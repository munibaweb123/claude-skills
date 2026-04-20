# Streaming

Deep reference for streaming agent responses in the OpenAI Agents SDK.

---

## Overview

`Runner.run_streamed()` provides real-time streaming of agent responses, including token-by-token text, tool calls, and handoff events.

---

## Basic Streaming

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="Be helpful.")

result = Runner.run_streamed(agent, "Write a short poem about coding.")

async for event in result.stream_events():
    if event.type == "raw_response_event":
        if hasattr(event.data, "delta") and hasattr(event.data.delta, "text"):
            print(event.data.delta.text, end="", flush=True)

print()  # Newline after streaming
print(f"Final: {result.final_output}")
```

---

## Event Types

### Raw Response Events

| Event | Description |
|-------|-------------|
| `RawResponsesStreamEvent` | Direct LLM events in OpenAI Responses API format |
| `ResponseTextDeltaEvent` | Token-by-token text generation |

### Higher-Level Events

| Event | Description |
|-------|-------------|
| `RunItemStreamEvent` | Signals item completion (message, tool call, etc.) |
| `AgentUpdatedStreamEvent` | Notifies of agent changes/handoffs |

### RunItem Event Names

| Name | When |
|------|------|
| `message_output_created` | Agent produced text output |
| `tool_called` | Agent called a tool |
| `tool_output` | Tool returned result |
| `handoff_requested` | Agent requested handoff |
| `handoff_occured` | Handoff completed (note: intentionally misspelled in SDK) |
| `tool_search_called` | ToolSearchTool invoked |
| `tool_search_output_created` | Tool search returned results |
| `reasoning_item_created` | Reasoning/CoT item produced |
| `mcp_approval_requested` | MCP tool approval needed |

---

## Streaming with Event Processing

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="Be helpful.", tools=[my_tool])

result = Runner.run_streamed(agent, "Search for Python tutorials")

async for event in result.stream_events():
    if event.type == "raw_response_event":
        # Token-level streaming
        data = event.data
        if hasattr(data, "delta") and hasattr(data.delta, "text"):
            print(data.delta.text, end="", flush=True)

    elif event.type == "run_item_stream_event":
        # High-level semantic events
        if event.name == "tool_called":
            print(f"\n[Tool called: {event.item.tool_name}]")
        elif event.name == "tool_output":
            print(f"[Tool output received]")
        elif event.name == "handoff_occured":
            print(f"[Handoff to: {event.item.target_agent}]")

    elif event.type == "agent_updated_stream_event":
        print(f"\n[Active agent: {event.new_agent.name}]")
```

---

## RunResultStreaming Properties

| Property | Description |
|----------|-------------|
| `stream_events()` | Async iterator for semantic events |
| `current_agent` | Active agent mid-run |
| `is_complete` | Whether stream has finished |
| `final_output` | Available after stream completes |
| `last_agent` | Agent that handled final response |
| `new_items` | All items produced during the run |
| `interruptions` | Pending HITL approvals |

---

## Cancellation

### Immediate Cancellation

```python
result = Runner.run_streamed(agent, "Long task")

async for event in result.stream_events():
    if should_cancel():
        result.cancel()  # Immediate stop
        break
```

### Graceful Cancellation

```python
result = Runner.run_streamed(agent, "Long task")

async for event in result.stream_events():
    if should_stop_after_this_turn():
        result.cancel(mode="after_turn")  # Complete current turn, then stop
```

---

## WebSocket Transport

Persistent WebSocket connections for lower latency:

### Global WebSocket

```python
from agents import set_default_openai_responses_transport, Runner

set_default_openai_responses_transport("websocket")
result = Runner.run_streamed(agent, "Hello")
async for event in result.stream_events():
    pass
```

### Multi-Turn WebSocket Reuse (Recommended)

```python
from agents import responses_websocket_session

async with responses_websocket_session() as ws:
    # First turn
    first = ws.run_streamed(agent, "Hello")
    async for event in first.stream_events():
        pass

    # Second turn reuses connection
    second = ws.run_streamed(
        agent, "Goodbye",
        previous_response_id=first.last_response_id,
    )
    async for event in second.stream_events():
        pass
```

**Warning:** Finish consuming streamed results before exiting context; in-flight requests will force-close the connection.

---

## Streaming with Sessions

```python
from agents import Agent, Runner, SQLiteSession

agent = Agent(name="Assistant", instructions="Be helpful.")
session = SQLiteSession("user_123")

# First turn
result = Runner.run_streamed(agent, "What is Python?", session=session)
async for event in result.stream_events():
    if event.type == "raw_response_event":
        if hasattr(event.data, "delta") and hasattr(event.data.delta, "text"):
            print(event.data.delta.text, end="", flush=True)

# Second turn with history
result = Runner.run_streamed(agent, "Tell me more.", session=session)
async for event in result.stream_events():
    if event.type == "raw_response_event":
        if hasattr(event.data, "delta") and hasattr(event.data.delta, "text"):
            print(event.data.delta.text, end="", flush=True)
```

---

## Streaming with HITL

```python
result = Runner.run_streamed(agent, "Delete all temp files")

async for event in result.stream_events():
    pass  # Consume stream

if result.interruptions:
    state = result.to_state()
    for interruption in result.interruptions:
        state.approve(interruption)
    # Resume with streaming
    result = Runner.run_streamed(agent, state)
    async for event in result.stream_events():
        pass
```

---

## Important Notes

- A streaming run is **not complete** until the iterator ends
- Post-processing (session persistence, approval bookkeeping, history compaction) can finish after the last visible token
- Always consume the full stream before using `result.final_output`
- For low-latency streaming with sessions, disable auto-compaction and call `session.run_compaction()` manually
