# Streaming

Deep reference for Server-Sent Events (SSE) streaming in ChatKit.

---

## Overview

ChatKit uses SSE (Server-Sent Events) for streaming responses from server to client. The server yields `ThreadStreamEvent` objects that are automatically serialized and sent to the client.

---

## Streaming from respond()

```python
from chatkit.types import (
    ThreadItemDoneEvent, AssistantMessageItem, AssistantMessageContent,
    ProgressUpdateEvent, ErrorEvent,
)
from datetime import datetime

async def respond(self, thread, input_user_message, context):
    # Transient progress
    yield ProgressUpdateEvent(icon="search", text="Thinking...")

    # Final message (persisted automatically)
    yield ThreadItemDoneEvent(
        item=AssistantMessageItem(
            thread_id=thread.id,
            id=self.store.generate_item_id("message", thread, context),
            created_at=datetime.now(),
            content=[AssistantMessageContent(text="Here's your answer.")],
        ),
    )
```

---

## Streaming with Agents SDK

The most common pattern -- stream agent responses:

```python
from agents import Runner
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response

async def respond(self, thread, input_user_message, context):
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
```

---

## Event Persistence Rules

| Event | Stored |
|-------|--------|
| `ThreadItemDoneEvent` | Yes -- triggers `store.add_thread_item()` |
| `ThreadItemReplacedEvent` | Yes -- triggers `store.save_item()` |
| `ThreadCreatedEvent` | Yes -- triggers `store.save_thread()` |
| `ThreadUpdatedEvent` | Yes -- triggers `store.save_thread()` |
| `ThreadItemAddedEvent` | **No** -- intermediate only |
| `ThreadItemUpdatedEvent` | **No** -- partial update only |
| `ProgressUpdateEvent` | **No** -- transient UI |
| `ClientEffectEvent` | **No** -- fire-and-forget |
| `ErrorEvent` | **No** -- error display |

---

## FastAPI Endpoint Pattern

```python
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from chatkit.server import StreamingResult

@app.post("/chatkit")
async def chatkit(request: Request):
    result = await server.process(await request.body(), context=my_context)
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

---

## Stream Options

Control client-side streaming behavior:

```python
from chatkit.types import StreamOptions

def get_stream_options(self, thread, context):
    return StreamOptions(allow_cancel=True)  # Default
```

---

## Stream Cancellation

When the user cancels mid-stream:

```python
async def handle_stream_cancelled(self, thread, pending_items, context):
    # Default behavior:
    # - Persists non-empty assistant messages
    # - Adds SDKHiddenContextItem noting the cancellation
    await super().handle_stream_cancelled(thread, pending_items, context)
```

---

## Error Streaming

```python
from chatkit.types import ErrorEvent
from agents import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered

async def respond(self, thread, input_user_message, context):
    try:
        async for event in stream_agent_response(agent_context, result):
            yield event
    except InputGuardrailTripwireTriggered:
        yield ErrorEvent(message="Message blocked for safety.")
    except OutputGuardrailTripwireTriggered:
        yield ErrorEvent(message="Response blocked.", allow_retry=False)
    except Exception as e:
        yield ErrorEvent(message="An error occurred. Please try again.")
```
