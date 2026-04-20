# Production Deployment

Deep reference for deploying ChatKit backends in production.

---

## Production Checklist

### Required

- [ ] Implement a real Store (PostgreSQL, etc.) -- never in-memory in production
- [ ] Store thread items as JSONB for schema evolution
- [ ] Authenticate every request
- [ ] Authorize thread/attachment access by user/tenant
- [ ] Set `OPENAI_API_KEY` via environment variable
- [ ] Register domain key in OpenAI platform settings
- [ ] Handle guardrail errors (`InputGuardrailTripwireTriggered`, `OutputGuardrailTripwireTriggered`)
- [ ] Configure CORS for frontend origin

### Recommended

- [ ] Use `previous_response_id` for efficient multi-turn conversations
- [ ] Implement `AttachmentStore` for file upload support
- [ ] Stream progress updates from long-running tools
- [ ] Auto-generate thread titles concurrently
- [ ] Set up client-side telemetry (`onLog`, `onError`)
- [ ] Implement data retention policies
- [ ] Use connection pooling for database
- [ ] Add rate limiting
- [ ] Set up health check endpoint

---

## Deployment Platforms

| Platform | Best For |
|----------|----------|
| **Vercel** | Quick deploys, preview environments, automatic HTTPS |
| **Fly.io / Render / Railway** | Managed containers, predictable SSE streaming |
| **AWS / GCP / Azure** | Full control, existing infrastructure |

**Key requirement**: The platform must support long-lived SSE connections for streaming.

---

## Error Handling

```python
from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from chatkit.types import ErrorEvent
from chatkit.errors import StreamError, CustomStreamError

class MyChatKitServer(ChatKitServer[RequestContext]):
    async def respond(self, thread, input_user_message, context):
        try:
            items_page = await self.store.load_thread_items(
                thread.id, after=None, limit=20, order="asc", context=context,
            )
            input_items = await simple_to_agent_input(items_page.data)
            agent_context = AgentContext(
                thread=thread, store=self.store, request_context=context,
            )
            result = Runner.run_streamed(assistant, input_items, context=agent_context)
            async for event in stream_agent_response(agent_context, result):
                yield event
        except InputGuardrailTripwireTriggered:
            yield ErrorEvent(message="Message blocked for safety.")
        except OutputGuardrailTripwireTriggered:
            yield ErrorEvent(message="Response blocked.", allow_retry=False)
        except Exception as e:
            logger.error(f"Respond error: {e}")
            yield ErrorEvent(message="Something went wrong. Please try again.")
```

---

## Thread Lifecycle Management

### Auto-Generate Titles

```python
import asyncio

async def respond(self, thread, input_user_message, context):
    # Start title generation concurrently
    title_task = asyncio.create_task(
        self._maybe_update_thread_title(thread, context)
    )

    # Stream agent response
    async for event in stream_agent_response(agent_context, result):
        yield event

    # Wait for title to complete
    await title_task

async def _maybe_update_thread_title(self, thread, context):
    if thread.title:
        return  # Already has a title
    # Use a lightweight model to generate title
    title_result = Runner.run_sync(
        title_agent, f"Generate a short title for: {thread.metadata.get('first_message', '')}",
    )
    thread.title = title_result.final_output[:100]
    await self.store.save_thread(thread, context=context)
```

### Thread Status Management

```python
from chatkit.types import ActiveStatus, LockedStatus, ClosedStatus

# Lock thread (e.g., during escalation)
thread.status = LockedStatus(reason="Escalated to human support.")
await self.store.save_thread(thread, context=context)

# Close thread
thread.status = ClosedStatus(reason="Issue resolved.")
await self.store.save_thread(thread, context=context)

# Block operations on locked/closed threads
async def respond(self, thread, input_user_message, context):
    if thread.status.type in {"locked", "closed"}:
        yield ErrorEvent(message=f"Thread is {thread.status.type}.")
        return
```

---

## Monitoring

### Client-Side Telemetry

```javascript
const chatkit = useChatKit({
  onLog: ({ name, data }) => {
    sendToAnalytics({
      name,
      data: scrubSensitiveFields(data),
      userId: currentUser.id,
    });
  },
  onError: ({ error }) => {
    sendToErrorTracker({
      name: "chatkit.error",
      error: scrubSensitiveFields(error),
      userId: currentUser.id,
    });
  },
});
```

### Server-Side Logging

```python
import logging

logger = logging.getLogger("chatkit")

@app.post("/chatkit")
async def chatkit(request: Request, ctx = Depends(get_current_user)):
    logger.info(f"ChatKit request from user {ctx.user_id}")
    result = await server.process(await request.body(), ctx)
    ...
```

---

## Feedback Collection

```javascript
// Client
messages: { threadItemActions: { feedback: true } }
```

```python
# Server
async def add_feedback(self, thread_id, item_ids, feedback, context):
    logger.info(f"Feedback: {feedback} on items {item_ids} in thread {thread_id}")
    # Persist to analytics database, QA system, etc.
    await self.analytics.record_feedback(
        thread_id=thread_id,
        item_ids=item_ids,
        feedback=feedback,
        user_id=context.user_id,
    )
```

---

## Dictation (Speech-to-Text)

```javascript
// Client
composer: { dictation: { enabled: true } }
```

```python
# Server
import io
from openai import OpenAI
from chatkit.types import AudioInput, TranscriptionResult

client = OpenAI()

async def transcribe(self, audio_input: AudioInput, context) -> TranscriptionResult:
    ext = {
        "audio/webm": "webm",
        "audio/mp4": "m4a",
        "audio/ogg": "ogg",
    }.get(audio_input.media_type, "webm")
    audio_file = io.BytesIO(audio_input.data)
    audio_file.name = f"audio.{ext}"
    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe", file=audio_file,
    )
    return TranscriptionResult(text=transcription.text)
```

---

## Localization

```python
import gettext
from pathlib import Path

LOCALE_DIR = Path(__file__).parent / "locales"
_translations: dict[str, gettext.NullTranslations] = {}

def get_translations(locale: str) -> gettext.NullTranslations:
    if locale not in _translations:
        _translations[locale] = gettext.translation(
            "messages", localedir=LOCALE_DIR, languages=[locale], fallback=True,
        )
    return _translations[locale]
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `openai-chatkit` | ChatKit Python SDK |
| `openai-agents>=0.3.2` | Agents SDK for tool execution |
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` | Type validation |
| `jinja2>=3.1,<4` | Widget template rendering |
| `psycopg` / `asyncpg` | PostgreSQL (production store) |

---

## Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| In-memory store in production | Use PostgreSQL or other persistent store |
| No auth on `/chatkit` endpoint | Always authenticate requests |
| User-derived system prompts | Keep system messages static |
| Ignoring `inference_options` | Check and fall back to defaults |
| Skipping guardrail error handling | Catch and yield `ErrorEvent` |
| No domain key in production | Register at OpenAI platform |
| Mixing Agents SDK sessions with ChatKit | ChatKit manages its own state |
| Using deprecated `build_basic()` | Use `build()` instead |
