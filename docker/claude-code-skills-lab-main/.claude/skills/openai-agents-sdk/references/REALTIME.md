# Realtime / Voice Agents

Deep reference for voice and realtime agent interactions in the OpenAI Agents SDK.

---

## Overview

Realtime agents enable voice-based interactions over WebSocket or SIP/telephony transport. This is a beta feature.

---

## Core Classes

| Class | Purpose |
|-------|---------|
| `RealtimeAgent` | Agent configured for realtime (voice) interactions |
| `RealtimeRunner` | Session factory wiring agent to transport |
| `RealtimeSession` | Live session managing I/O, events, history, tools |
| `OpenAIRealtimeWebSocketModel` | Default WebSocket transport |
| `OpenAIRealtimeSIPModel` | Telephony/SIP transport |

---

## RealtimeAgent

```python
from agents.realtime import RealtimeAgent

agent = RealtimeAgent(
    name="Voice Assistant",
    instructions="You are a friendly voice assistant. Keep responses brief.",
    tools=[get_weather, check_calendar],
    output_guardrails=[content_safety_guard],
    handoffs=[spanish_agent, french_agent],
)
```

**Limitations:**
- Does NOT support structured outputs (`output_type`)
- Does NOT support per-agent model choice
- Input guardrails are NOT supported (output only)

---

## Session Lifecycle

```python
from agents.realtime import RealtimeRunner

runner = RealtimeRunner(
    starting_agent=agent,
    config={...},
)

async with await runner.run(model_config={...}) as session:
    async for event in session:
        if event.type == "audio":
            # Send audio to speaker/output
            play_audio(event.data)
        elif event.type == "agent_start":
            print(f"Agent started: {event.agent.name}")
        elif event.type == "tool_approval_required":
            session.approve_tool_call(event.call_id)
```

---

## RealtimeSessionModelSettings

```python
config = {
    "model_settings": {
        "model_name": "gpt-realtime-1.5",
        "audio": {
            "input": {
                "format": "pcm16",
                "transcription": {
                    "model": "gpt-4o-mini-transcribe",
                },
                "turn_detection": {
                    "type": "semantic_vad",
                    "interrupt_response": True,
                },
            },
            "output": {
                "format": "pcm16",
                "voice": "ash",
            },
        },
    },
}
```

### Available Voices

`ash`, `ballad`, `coral`, `sage`, `verse` (and others as added by OpenAI).

### Turn Detection Types

| Type | Description |
|------|-------------|
| `semantic_vad` | Semantic voice activity detection (recommended) |

---

## RealtimeRunConfig

```python
config = {
    "async_tool_calls": True,                    # Concurrent tool execution
    "output_guardrails": [safety_guard],          # Output validation
    "guardrails_settings": {
        "debounce_text_length": 100,              # Debounce threshold
    },
    "tool_error_formatter": format_fn,
    "tracing_disabled": False,
}
```

---

## Input/Output Methods

### Sending Input

```python
# Text message
session.send_message("Hello, how are you?")

# Audio bytes
session.send_audio(audio_bytes, commit=True)

# Structured input
from agents.realtime import RealtimeUserInputMessage
session.send_message(RealtimeUserInputMessage(
    input_text="Hello",
    # or input_image=image_content,
))
```

---

## Session Events

| Event | Description |
|-------|-------------|
| `audio` | Audio chunk from agent |
| `audio_end` | Agent finished speaking |
| `audio_interrupted` | Agent speech interrupted |
| `agent_start` | Agent began processing |
| `agent_end` | Agent finished processing |
| `tool_start` | Tool execution started |
| `tool_end` | Tool execution completed |
| `tool_approval_required` | Tool needs human approval |
| `handoff` | Agent handoff occurred |
| `history_added` | History item added |
| `history_updated` | History item updated |
| `guardrail_tripped` | Output guardrail triggered |
| `input_audio_timeout_triggered` | Audio input timed out |
| `error` | Error occurred |
| `raw_model_event` | Raw model event passthrough |

---

## Tool Approvals in Realtime

```python
async for event in session:
    if event.type == "tool_approval_required":
        # Approve
        session.approve_tool_call(event.call_id)
        # or Reject
        session.reject_tool_call(event.call_id, reason="Not authorized")
```

---

## Handoffs in Realtime

```python
from agents.realtime import realtime_handoff

h = realtime_handoff(
    agent=spanish_agent,
    tool_description="Transfer to Spanish-speaking agent",
)

main_agent = RealtimeAgent(
    name="Router",
    instructions="Route to language-specific agent.",
    handoffs=[h],
)
```

**Note:** Realtime handoffs do NOT support the regular handoff `input_filter`.

---

## SIP/Telephony Transport

For phone call integration:

```python
from agents.realtime import OpenAIRealtimeSIPModel

# Attach to incoming call via call_id from Realtime Calls API webhook
model = OpenAIRealtimeSIPModel(call_id="call_abc123")

# Build initial session payload for call acceptance
payload = OpenAIRealtimeSIPModel.build_initial_session_payload(
    agent=agent,
    model_config=config,
)
```

---

## Azure OpenAI Support

Pass the GA Realtime endpoint URL with explicit headers:

```python
model_config = {
    "url": "wss://your-resource.openai.azure.com/openai/realtime",
    "headers": {
        "api-key": "your-azure-api-key",
    },
}
```

---

## Key Limitations

- No structured outputs (`output_type` not supported)
- Voice configuration cannot change after audio production begins
- Input guardrails not supported (output guardrails only)
- No browser WebRTC transport (server-side WebSocket only)
- Python 3.10+ required for realtime features
- Beta feature with potential breaking changes
