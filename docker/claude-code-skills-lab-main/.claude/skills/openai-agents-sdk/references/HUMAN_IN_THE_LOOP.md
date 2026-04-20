# Human-in-the-Loop

Deep reference for human approval flows in the OpenAI Agents SDK.

---

## Overview

The HITL flow pauses agent execution awaiting human approval or rejection of sensitive tool calls. Approvals surface as interruptions in run results and can be serialized/resumed via `RunState`.

---

## Basic Approval

### Always Require Approval

```python
from agents import function_tool

@function_tool(needs_approval=True)
async def cancel_order(order_id: int) -> str:
    return f"Cancelled order {order_id}"
```

### Conditional Approval

```python
async def requires_review(ctx, params, call_id) -> bool:
    return "refund" in params.get("subject", "").lower()

@function_tool(needs_approval=requires_review)
async def send_email(subject: str, body: str) -> str:
    return f"Sent '{subject}'"
```

---

## Tools Supporting needs_approval

| Tool Type | How |
|-----------|-----|
| `@function_tool` | `needs_approval=True` or callable |
| `Agent.as_tool()` | `needs_approval=True` or callable |
| `ShellTool` | `needs_approval` parameter |
| `ApplyPatchTool` | `needs_approval` parameter |
| Local MCP servers | `require_approval` on server class |
| `HostedMCPTool` | `tool_config={"require_approval": "always"}` |

---

## Approval Flow

```
1. Model emits tool call → runner evaluates approval rule
2. If approval exists in RunContextWrapper → proceed
3. Otherwise → pause execution
4. RunResult.interruptions contains ToolApprovalItem entries
5. Convert to RunState via result.to_state()
6. Call state.approve() or state.reject()
7. Resume with Runner.run(agent, state)
8. Repeat if new approvals needed
```

---

## Complete Pause-Approve-Resume Example

```python
import asyncio
import json
from pathlib import Path
from agents import Agent, Runner, RunState, function_tool

async def needs_oakland_approval(ctx, params, call_id) -> bool:
    return "Oakland" in params.get("city", "")

@function_tool(needs_approval=needs_oakland_approval)
async def get_temperature(city: str) -> str:
    return f"The temperature in {city} is 20°C"

agent = Agent(
    name="Weather Assistant",
    instructions="Answer weather questions with the provided tools.",
    tools=[get_temperature],
)

STATE_PATH = Path(".cache/hitl_state.json")

def prompt_approval(tool_name: str, arguments: str | None) -> bool:
    answer = input(f"Approve {tool_name} with {arguments}? [y/N]: ").strip().lower()
    return answer in {"y", "yes"}

async def main():
    result = await Runner.run(agent, "What is the temperature in Oakland?")

    while result.interruptions:
        # Serialize state (can persist to disk/database)
        state = result.to_state()
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(state.to_string())

        # Load state (possibly in different process)
        stored = json.loads(STATE_PATH.read_text())
        state = await RunState.from_json(agent, stored)

        # Resolve each interruption
        for interruption in result.interruptions:
            approved = await asyncio.get_running_loop().run_in_executor(
                None, prompt_approval,
                interruption.name or "unknown_tool",
                interruption.arguments,
            )
            if approved:
                state.approve(interruption, always_approve=False)
            else:
                state.reject(interruption)

        # Resume execution
        result = await Runner.run(agent, state)

    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## RunState Serialization

```python
# Serialize
state = result.to_state()
json_dict = state.to_json()       # dict
json_string = state.to_string()   # JSON string

# Deserialize
state = await RunState.from_json(agent, json_dict)
state = await RunState.from_string(agent, json_string)
```

### Serialization Options

| Option | Purpose |
|--------|---------|
| `context_serializer` | Custom serialization for non-mapping context |
| `context_deserializer` | Rebuild non-mapping context on load |
| `strict_context=True` | Fail unless context is mapping or serializer provided |
| `context_override` | Replace context when loading state |
| `include_tracing_api_key=True` | Include tracing credentials |

---

## Approval/Rejection

### Basic

```python
for interruption in result.interruptions:
    state.approve(interruption)
    # or
    state.reject(interruption)
```

### Sticky Decisions

Persist decisions across serialization cycles:

```python
state.approve(interruption, always_approve=True)   # Auto-approve in future
state.reject(interruption, always_reject=True)      # Auto-reject in future
```

### Custom Rejection Messages

```python
# Per-rejection
state.reject(
    interruption,
    rejection_message="Action was canceled because reviewer denied approval.",
)

# Global via RunConfig
from agents import RunConfig, ToolErrorFormatterArgs

def format_rejection(args: ToolErrorFormatterArgs) -> str | None:
    if args.kind == "approval_rejected":
        return f"Tool '{args.tool_name}' was rejected. Propose alternative."
    return None

config = RunConfig(tool_error_formatter=format_rejection)
```

---

## Partial Resolution

Not all interruptions must be resolved in one pass:

```python
# Approve some, leave others
state = result.to_state()
state.approve(result.interruptions[0])
# interruptions[1] remains unresolved

result = await Runner.run(agent, state)
# result.interruptions still contains unresolved items
```

---

## Nested Agent Interruptions

Interruptions from nested `Agent.as_tool()` runs surface on the outer run:

```python
worker = Agent(name="Worker", tools=[dangerous_tool])
orchestrator = Agent(
    name="Orchestrator",
    tools=[worker.as_tool(tool_name="worker", needs_approval=True)],
)

result = await Runner.run(orchestrator, "Do the dangerous thing")
# result.interruptions contains the nested tool's approval request
# Resume the original top-level agent
```

---

## Streaming with HITL

```python
result = Runner.run_streamed(agent, "Delete temp files")
async for event in result.stream_events():
    pass  # Consume stream

if result.interruptions:
    state = result.to_state()
    for interruption in result.interruptions:
        state.approve(interruption)
    result = Runner.run_streamed(agent, state)
    async for event in result.stream_events():
        pass
```

---

## Automatic Approval via Callbacks

For `ShellTool` and `ApplyPatchTool`:

```python
from agents import ShellTool

def auto_approve(tool_name, args):
    # Custom approval logic
    return True

agent = Agent(
    name="Shell Agent",
    tools=[ShellTool(on_approval=auto_approve)],
)
```

---

## Warnings

- Keep secrets out of context objects if serializing `RunState`
- For long-running approvals, store a version marker alongside serialized state
- Interruption details include `agent.name`, `tool_name`, and `arguments`
