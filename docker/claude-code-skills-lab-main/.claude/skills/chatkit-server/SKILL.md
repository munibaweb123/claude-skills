---
name: chatkit-server
description: Comprehensive OpenAI ChatKit Server skill for building conversational AI backends from hello world to professional production systems. Use when building chat backends with OpenAI ChatKit Python SDK, implementing ChatKitServer, creating Store implementations, streaming agent responses, building widgets, handling client tools, managing threads, integrating with OpenAI Agents SDK, or deploying production conversational AI applications. Covers ChatKitServer, Store, AgentContext, widgets, tools, streaming, attachments, authentication, and production deployment patterns.
---

# ChatKit Server Skill

This skill provides comprehensive support for building conversational AI backends with the OpenAI ChatKit Python SDK (`openai-chatkit`), from simple hello world examples to professional production-ready systems. Before providing specific recommendations, this skill gathers context about your requirements and constraints.

## When to Use This Skill

Use this skill when you need to:
- Build a conversational AI backend with OpenAI ChatKit (`openai-chatkit`)
- Implement `ChatKitServer` with custom `respond()` logic
- Create a `Store` for thread and item persistence (in-memory, PostgreSQL, etc.)
- Stream agent responses using `stream_agent_response()` with OpenAI Agents SDK
- Build interactive widgets with actions and streaming updates
- Implement client tools (server-triggered, client-executed)
- Handle file attachments, dictation, and @-mentions
- Manage thread lifecycle (create, lock, close, delete)
- Deploy production ChatKit backends with authentication and monitoring

## Pre-Implementation Context Gathering

Before providing specific recommendations, this skill gathers important context:

### Team Experience Assessment
- What is your team's experience with ChatKit? (beginner, intermediate, advanced)
- Are you familiar with the OpenAI Agents SDK?
- Do you have experience with FastAPI or async Python?

### Use Case Requirements
- What type of chat experience are you building? (support bot, assistant, internal tool)
- Do you need widgets for interactive UI components?
- Do you need file attachments or dictation support?
- Do you need client tools (frontend-executed actions)?

### Architecture Choice
- **OpenAI-hosted**: Quick start, OpenAI manages the backend via Agent Builder
- **Self-hosted**: Full control over auth, data, orchestration with `ChatKitServer`
- Which mode fits your needs?

### Infrastructure Constraints
- What database will you use for persistence? (PostgreSQL, SQLite, etc.)
- What web framework? (FastAPI recommended)
- What are your authentication requirements?

## Prerequisites

- Python 3.10+
- `pip install openai-chatkit`
- `export OPENAI_API_KEY=sk-...`
- Frontend: `npm install @openai/chatkit-react` (React) or CDN script tag
- Dependencies: `fastapi`, `uvicorn`, `openai-agents>=0.3.2`, `pydantic`, `jinja2`

## Quick Start: Hello World

### Step 1: Minimal Server (Echo)

```python
from collections import defaultdict
from datetime import datetime
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

from chatkit.server import ChatKitServer, StreamingResult
from chatkit.store import Store, NotFoundError
from chatkit.types import (
    AssistantMessageContent, AssistantMessageItem,
    ThreadItemDoneEvent, ThreadMetadata, ThreadStreamEvent,
    ThreadItem, UserMessageItem, Page, Attachment,
)

# --- In-Memory Store ---
class MyChatKitStore(Store[dict]):
    def __init__(self):
        self.threads: dict[str, ThreadMetadata] = {}
        self.items: dict[str, list[ThreadItem]] = defaultdict(list)

    async def load_thread(self, thread_id, context):
        if thread_id not in self.threads:
            raise NotFoundError(f"Thread {thread_id} not found")
        return self.threads[thread_id]

    async def save_thread(self, thread, context):
        self.threads[thread.id] = thread

    async def load_threads(self, limit, after, order, context):
        return Page(data=list(self.threads.values()), has_more=False, after="")

    async def load_thread_items(self, thread_id, after, limit, order, context):
        return Page(data=self.items.get(thread_id, []), has_more=False, after="")

    async def add_thread_item(self, thread_id, item, context):
        self.items[thread_id].append(item)

    async def save_item(self, thread_id, item, context):
        items = self.items[thread_id]
        for idx, existing in enumerate(items):
            if existing.id == item.id:
                items[idx] = item
                return
        items.append(item)

    async def load_item(self, thread_id, item_id, context):
        for item in self.items.get(thread_id, []):
            if item.id == item_id:
                return item
        raise NotFoundError(f"Item {item_id} not found")

    async def delete_thread(self, thread_id, context):
        self.threads.pop(thread_id, None)
        self.items.pop(thread_id, None)

    async def delete_thread_item(self, thread_id, item_id, context):
        self.items[thread_id] = [
            i for i in self.items.get(thread_id, []) if i.id != item_id
        ]

    async def save_attachment(self, attachment, context): pass
    async def load_attachment(self, attachment_id, context): raise NotFoundError("")
    async def delete_attachment(self, attachment_id, context): pass

# --- Server ---
class MyChatKitServer(ChatKitServer[dict]):
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
        yield ThreadItemDoneEvent(
            item=AssistantMessageItem(
                thread_id=thread.id,
                id=self.store.generate_item_id("message", thread, context),
                created_at=datetime.now(),
                content=[AssistantMessageContent(text="Hello, world!")],
            ),
        )

# --- FastAPI ---
app = FastAPI()
store = MyChatKitStore()
server = MyChatKitServer(store)

@app.post("/chatkit")
async def chatkit(request: Request):
    result = await server.process(await request.body(), context={})
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

### Step 2: Agent-Powered Server

```python
from agents import Agent, Runner
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response
from chatkit.server import ChatKitServer
from chatkit.types import ThreadMetadata, UserMessageItem, ThreadStreamEvent

assistant = Agent(
    name="assistant",
    instructions="You are a helpful assistant.",
    model="gpt-4.1-mini",
)

class MyChatKitServer(ChatKitServer[dict]):
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: dict,
    ) -> AsyncIterator[ThreadStreamEvent]:
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

### Step 3: React Frontend

```javascript
import { ChatKit, useChatKit } from "@openai/chatkit-react";

export function App() {
  const chatkit = useChatKit({
    api: {
      url: "http://localhost:8000/chatkit",
      domainKey: "local-dev",
    },
  });
  return <ChatKit control={chatkit.control} />;
}
```

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (@openai/chatkit-react)                        │
│  ┌─────────┐  ┌───────────┐  ┌────────────────────────┐ │
│  │ ChatKit │  │ useChatKit│  │ Client Tools / Effects │ │
│  │ Widget  │  │ Hook      │  │ onClientTool, onEffect │ │
│  └────┬────┘  └─────┬─────┘  └────────────┬───────────┘ │
│       └─────────────┼──────────────────────┘             │
│                     │ POST /chatkit (SSE)                │
└─────────────────────┼────────────────────────────────────┘
                      │
┌─────────────────────┼────────────────────────────────────┐
│  Backend (openai-chatkit Python)                         │
│                     │                                    │
│  ┌──────────────────▼──────────────────────────────────┐ │
│  │  ChatKitServer.process(request, context)             │ │
│  │    ├─ Streaming → respond() / action()               │ │
│  │    └─ Non-streaming → CRUD threads/items/attachments │ │
│  └──────────────────┬──────────────────────────────────┘ │
│                     │                                    │
│  ┌──────────┐  ┌────▼─────┐  ┌──────────────────┐       │
│  │  Store   │  │  Agent   │  │  Widgets          │       │
│  │ (DB)     │  │  Context │  │  (WidgetTemplate) │       │
│  └──────────┘  └────┬─────┘  └──────────────────┘       │
│                     │                                    │
│         ┌───────────▼───────────────┐                    │
│         │  OpenAI Agents SDK        │                    │
│         │  Runner.run_streamed()    │                    │
│         │  stream_agent_response()  │                    │
│         └───────────────────────────┘                    │
└──────────────────────────────────────────────────────────┘
```

### Core Components

| Component | Module | Purpose |
|-----------|--------|---------|
| `ChatKitServer` | `chatkit.server` | Request routing, streaming, lifecycle |
| `Store` | `chatkit.store` | Thread/item persistence (abstract) |
| `AgentContext` | `chatkit.agents` | Bridge between ChatKit and Agents SDK |
| `stream_agent_response` | `chatkit.agents` | Converts Agents SDK events to ChatKit events |
| `simple_to_agent_input` | `chatkit.agents` | Converts thread items to agent input |
| `WidgetTemplate` | `chatkit.widgets` | Interactive UI components |
| Thread types | `chatkit.types` | ThreadMetadata, ThreadItem, events |

## Respond Pipeline

The core flow for handling user messages:

```
1. Load conversation history from Store
2. Convert thread items to agent input (simple_to_agent_input)
3. Create AgentContext (thread + store + request context)
4. Run agent with Runner.run_streamed()
5. Stream events via stream_agent_response()
6. Events auto-persist via ThreadItemDoneEvent
```

```python
async def respond(self, thread, input_user_message, context):
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
    # 4-5. Run and stream
    result = Runner.run_streamed(assistant, input_items, context=agent_context)
    async for event in stream_agent_response(agent_context, result):
        yield event
```

## Production Best Practices

### Required
- Implement a real Store (PostgreSQL, etc.) -- never use in-memory store in production
- Store thread items as JSONB to accommodate schema evolution without migrations
- Authenticate every request (session cookies, bearer tokens, or JWTs)
- Authorize thread/attachment access by user/tenant
- Protect API keys via environment variables
- Handle guardrail errors (`InputGuardrailTripwireTriggered`, `OutputGuardrailTripwireTriggered`)
- Register domain key at OpenAI platform for production frontends

### Recommended
- Use `previous_response_id` for efficient multi-turn conversations
- Stream progress updates from tools via `ProgressUpdateEvent`
- Implement `FileStore` for upload handling
- Handle stream cancellation gracefully
- Auto-generate thread titles concurrently
- Set up client-side telemetry via `onLog` and `onError` callbacks
- Implement retention policies for thread data

### Anti-Patterns
- **Don't** derive system prompts from user input
- **Don't** skip input validation on widget action payloads (treat as untrusted)
- **Don't** mix Agents SDK sessions with ChatKit sessions (ChatKit has its own state)
- **Don't** use `build_basic()` on WidgetTemplate (deprecated, use `build()`)

## Common Troubleshooting

### ChatKit Widget Not Loading
- Verify `domainKey` is registered in OpenAI platform settings
- Check CORS configuration on your FastAPI server
- Ensure `/chatkit` endpoint returns correct `media_type` for streaming vs non-streaming

### Agent Not Responding
- Verify `OPENAI_API_KEY` is set
- Check `load_thread_items` returns conversation history in correct order
- Ensure `simple_to_agent_input` receives the items (not an empty list)

### Widget Actions Not Firing
- Implement `action()` method on your ChatKitServer subclass
- For client-side actions, use `handler="client"` in `ActionConfig`
- Check action type matches in your handler

### Streaming Cuts Off
- Ensure `allow_cancel=True` in `StreamOptions` (default)
- Check `handle_stream_cancelled` persists partial messages
- Verify FastAPI returns `StreamingResponse` with `text/event-stream`

## Decision Tree

```
What do you need?
│
├─ First ChatKit backend? → See "Quick Start: Hello World"
├─ Agent-powered responses?
│   ├─ Simple → simple_to_agent_input + stream_agent_response
│   └─ Custom input handling → ThreadItemConverter subclass
├─ Persist conversations?
│   ├─ Development → In-memory Store
│   └─ Production → PostgreSQL Store (JSONB pattern)
├─ Interactive UI elements? → Widgets (WidgetTemplate)
├─ Frontend-executed actions? → Client Tools (StopAtTools)
├─ File uploads? → AttachmentStore + composer config
├─ Voice input? → transcribe() override
├─ @-mentions? → Entity tags + tag_to_message_content
├─ Thread management? → ThreadStatus (Active/Locked/Closed)
└─ Production deployment? → Auth + Store + monitoring
```

## Reference Documentation

| Reference | Description |
|-----------|-------------|
| [CORE_CONCEPTS.md](references/CORE_CONCEPTS.md) | ChatKitServer, request routing, respond pipeline |
| [STORE.md](references/STORE.md) | Store interface, in-memory and PostgreSQL implementations |
| [AGENTS.md](references/AGENTS.md) | AgentContext, stream_agent_response, ThreadItemConverter |
| [WIDGETS.md](references/WIDGETS.md) | WidgetTemplate, streaming widgets, actions |
| [TOOLS.md](references/TOOLS.md) | Client tools, server tools, progress updates, effects |
| [TYPES.md](references/TYPES.md) | ThreadMetadata, ThreadItem, events, annotations |
| [FRONTEND.md](references/FRONTEND.md) | React integration, useChatKit, configuration |
| [AUTHENTICATION.md](references/AUTHENTICATION.md) | Auth patterns, domain keys, tenant isolation |
| [PRODUCTION.md](references/PRODUCTION.md) | Deployment, monitoring, error handling, scaling |
