# Core Concepts

Deep reference for ChatKitServer, request routing, and the respond pipeline.

---

## ChatKitServer[TContext]

The main server class. Subclass it and implement `respond()`.

### Constructor

```python
ChatKitServer.__init__(
    store: Store[TContext],
    attachment_store: AttachmentStore[TContext] | None = None,
)
```

### Abstract Methods

| Method | Signature | Returns |
|--------|-----------|---------|
| `respond` | `async (thread: ThreadMetadata, input_user_message: UserMessageItem \| None, context: TContext)` | `AsyncIterator[ThreadStreamEvent]` |

### Concrete / Overridable Methods

| Method | Returns | Notes |
|--------|---------|-------|
| `process(request, context)` | `StreamingResult \| NonStreamingResult` | Main entry point; parses and routes all requests |
| `action(thread, action, sender, context)` | `AsyncIterator[ThreadStreamEvent]` | Handle widget/custom streaming actions |
| `sync_action(thread, action, sender, context)` | `SyncCustomActionResponse` | Non-streaming action variant |
| `add_feedback(thread_id, item_ids, feedback, context)` | `None` | Persist thumbs up/down |
| `transcribe(audio_input, context)` | `TranscriptionResult` | Speech-to-text; raises `NotImplementedError` by default |
| `get_stream_options(thread, context)` | `StreamOptions` | Default: `StreamOptions(allow_cancel=True)` |
| `handle_stream_cancelled(thread, pending_items, context)` | `None` | Persists non-empty assistant messages on cancel |

---

## Request Routing

`server.process()` parses the raw request body and routes to the appropriate handler:

### Streaming Requests (5 types)

| Request | Triggers |
|---------|----------|
| `ThreadsCreateReq` | `respond()` (new thread) |
| `ThreadsAddUserMessageReq` | `respond()` (existing thread) |
| `ThreadsAddClientToolOutputReq` | `respond()` (client tool result) |
| `ThreadsRetryAfterItemReq` | `respond()` (retry from point) |
| `ThreadsCustomActionReq` | `action()` (widget action) |

### Non-Streaming Requests (8+ types)

CRUD operations for threads, items, attachments, feedback:
`ThreadsGetByIdReq`, `ThreadsListReq`, `ItemsListReq`, `ItemsFeedbackReq`, `AttachmentsCreateReq`, `AttachmentsDeleteReq`, `ThreadsUpdateReq`, `ThreadsDeleteReq`, `InputTranscribeReq`, `ThreadsSyncCustomActionReq`

### Helper

```python
from chatkit.types import is_streaming_req
if is_streaming_req(request):
    # Returns StreamingResult
else:
    # Returns NonStreamingResult
```

---

## FastAPI Integration Pattern

```python
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from chatkit.server import ChatKitServer, StreamingResult

app = FastAPI()
server = MyChatKitServer(store)

@app.post("/chatkit")
async def chatkit(request: Request):
    result = await server.process(await request.body(), context={})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

### With Authentication Context

```python
from dataclasses import dataclass

@dataclass
class RequestContext:
    user_id: str
    org_id: str
    locale: str

@app.post("/chatkit")
async def chatkit(request: Request):
    user_id = request.headers.get("x-user-id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    context = RequestContext(user_id=user_id, org_id="org_1", locale="en")
    result = await server.process(await request.body(), context)
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

---

## Respond Pipeline (Complete)

```python
class MyChatKitServer(ChatKitServer[RequestContext]):
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        # 1. Load history
        items_page = await self.store.load_thread_items(
            thread.id, after=None, limit=20, order="asc", context=context,
        )

        # 2. Convert to agent input
        input_items = await simple_to_agent_input(items_page.data)

        # 3. Create agent context
        agent_context = AgentContext(
            thread=thread, store=self.store, request_context=context,
        )

        # 4. Run agent
        result = Runner.run_streamed(assistant, input_items, context=agent_context)

        # 5. Stream with error handling
        try:
            async for event in stream_agent_response(agent_context, result):
                yield event
        except InputGuardrailTripwireTriggered:
            yield ErrorEvent(message="Message blocked for safety.")
        except OutputGuardrailTripwireTriggered:
            yield ErrorEvent(message="Response blocked.", allow_retry=False)
```

### Response Chaining with previous_response_id

```python
async def respond(self, thread, input_user_message, context):
    items_page = await self.store.load_thread_items(
        thread.id, after=None, limit=20, order="asc", context=context,
    )
    input_items = await simple_to_agent_input(items_page.data)

    last_response_id = thread.metadata.get("last_response_id")
    agent_context = AgentContext(
        thread=thread, store=self.store, request_context=context,
    )

    result = Runner.run_streamed(
        assistant, input_items, context=agent_context,
        previous_response_id=last_response_id,
        auto_previous_response_id=True,
    )

    async for event in stream_agent_response(agent_context, result):
        yield event

    if result.last_response_id:
        thread.metadata["last_response_id"] = result.last_response_id
        await self.store.save_thread(thread, context=context)
```

---

## Stream Cancellation

The SDK handles stream cancellation automatically:

```python
# Override for custom behavior
async def handle_stream_cancelled(
    self,
    thread: ThreadMetadata,
    pending_items: list[ThreadItem],
    context: TContext,
) -> None:
    # Default: persists non-empty assistant messages
    # Adds SDKHiddenContextItem noting cancellation
    await super().handle_stream_cancelled(thread, pending_items, context)
```

```python
def get_stream_options(self, thread, context):
    return StreamOptions(allow_cancel=True)  # Default
```
