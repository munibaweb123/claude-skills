# Core Concepts

Deep reference for Agent, Runner, and RunResult - the foundational classes of the OpenAI Agents SDK.

---

## Agent Class

Generic type: `Agent[ContextType]`

### Constructor Parameters

| Parameter | Type | Default | Notes |
|-----------|------|---------|-------|
| `name` | `str` | Required | Agent identifier |
| `instructions` | `str \| Callable` | `""` | Static string or dynamic function |
| `prompt` | `dict \| Callable` | `None` | Optional prompt template |
| `handoff_description` | `str` | `""` | Description used when this agent is a handoff target |
| `handoffs` | `list[Agent \| Handoff]` | `[]` | Agents this agent can hand off to |
| `model` | `str` | `None` | Model name override |
| `model_settings` | `ModelSettings` | `None` | Temperature, top_p, tool_choice, etc. |
| `tools` | `list` | `[]` | Function tools, hosted tools, etc. |
| `mcp_servers` | `list` | `[]` | MCP server configurations |
| `mcp_config` | `dict` | `None` | MCP configuration |
| `input_guardrails` | `list` | `[]` | Input validation guardrails |
| `output_guardrails` | `list` | `[]` | Output validation guardrails |
| `output_type` | `type` | `str` | Pydantic model, dataclass, TypedDict, list, or str |
| `hooks` | `AgentHooks` | `None` | Agent-level lifecycle callbacks |
| `tool_use_behavior` | | `"run_llm_again"` | Controls what happens after tool use |
| `reset_tool_choice` | `bool` | `True` | Resets tool_choice to "auto" after a tool call |

### Dynamic Instructions

Instructions can be a callable that receives context and agent:

```python
def instructions(context: RunContextWrapper, agent: Agent) -> str:
    return f"You are helping user {context.context.user_name}"

# Async is also supported
async def async_instructions(context: RunContextWrapper, agent: Agent) -> str:
    user = await fetch_user(context.context.user_id)
    return f"You are helping {user.name}"

agent = Agent(name="Helper", instructions=instructions)
```

### Prompt Templates

```python
agent = Agent(
    name="Templated Agent",
    prompt={
        "id": "pmpt_123",
        "version": "1",
        "variables": {"param": "value"},
    },
)
```

### Output Types

Default is `str` (plain text). Setting `output_type` forces structured JSON output:

```python
from pydantic import BaseModel

class WeatherResult(BaseModel):
    city: str
    temperature: float
    conditions: str

agent = Agent(
    name="Weather",
    instructions="Extract weather info.",
    output_type=WeatherResult,
)

result = Runner.run_sync(agent, "It's 72F and sunny in NYC")
weather = result.final_output  # WeatherResult(city="NYC", temperature=72.0, conditions="sunny")
```

Supported types: Pydantic models, dataclasses, TypedDict, list, str.

### tool_use_behavior

Controls what happens after the agent calls a tool:

| Value | Behavior |
|-------|----------|
| `"run_llm_again"` (default) | LLM processes tool results and generates final output |
| `"stop_on_first_tool"` | First tool's output becomes the final response |
| `StopAtTools(stop_at_tool_names=[...])` | Stop only on specified tool names |
| `ToolsToFinalOutputFunction` | Custom handler function |

```python
from agents import Agent, StopAtTools

# Stop on specific tools
agent = Agent(
    name="Lookup",
    tools=[search_db, format_result],
    tool_use_behavior=StopAtTools(stop_at_tool_names=["format_result"]),
)
```

### ModelSettings

```python
from agents import ModelSettings
from openai.types.shared import Reasoning

settings = ModelSettings(
    temperature=0.7,
    top_p=0.9,
    tool_choice="auto",          # "auto", "required", "none", or tool name
    parallel_tool_calls=True,
    reasoning=Reasoning(effort="high"),
    verbosity="low",
    extra_args={"service_tier": "flex"},
)

agent = Agent(name="Reasoner", model="gpt-5.4", model_settings=settings)
```

Full ModelSettings properties: `temperature`, `top_p`, `tool_choice`, `parallel_tool_calls`, `truncation`, `store`, `prompt_cache_retention`, `response_include`, `top_logprobs`, `retry`, `extra_args`, `verbosity`, `reasoning`.

---

## Runner Class

The Runner executes the agent loop: calling the LLM, processing outputs, handling tool calls and handoffs.

### Three Execution Modes

| Method | Type | Returns | Use Case |
|--------|------|---------|----------|
| `Runner.run(agent, input)` | Async | `RunResult` | Production async code |
| `Runner.run_sync(agent, input)` | Sync | `RunResult` | Scripts, simple usage |
| `Runner.run_streamed(agent, input)` | Async streaming | `RunResultStreaming` | Real-time UI updates |

### Agent Loop Lifecycle

```
1. Call LLM with current agent + input
2. Process output:
   ├─ Final output → loop ends, return RunResult
   ├─ Handoff → update active agent + input, re-enter loop
   └─ Tool calls → execute tools, append results, re-enter loop
3. If max_turns exceeded → raise MaxTurnsExceeded
```

### Input Types

```python
# String input (treated as user message)
result = await Runner.run(agent, "Hello")

# List input (OpenAI Responses API format)
result = await Runner.run(agent, [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
    {"role": "user", "content": "How are you?"},
])

# RunState input (for resuming interrupted runs)
state = result.to_state()
result = await Runner.run(agent, state)
```

### RunConfig Parameters

```python
from agents import RunConfig

config = RunConfig(
    # Model & Session
    model="gpt-4.1",                         # Global LLM override
    model_provider=None,                      # Custom model provider
    model_settings=ModelSettings(...),        # Override agent settings
    session_settings=SessionSettings(limit=50),
    session_input_callback=keep_recent,       # Custom history merging

    # Guardrails & Handoffs
    input_guardrails=[...],                   # Global input guardrails
    output_guardrails=[...],                  # Global output guardrails
    handoff_input_filter=filter_fn,           # Edit inputs on handoff
    nest_handoff_history=True,                # Collapse transcript (beta)

    # Tracing
    tracing_disabled=False,
    trace_include_sensitive_data=False,
    workflow_name="my_workflow",
    trace_id="trace_abc123",
    group_id="group_xyz",

    # Tool behavior
    tool_error_formatter=format_rejection,
    call_model_input_filter=drop_old_messages,
)
```

### Conversation State Management

| Strategy | Location | Use Case |
|----------|----------|----------|
| `result.to_input_list()` | App memory | Small loops, manual control |
| `session` parameter | Storage + SDK | Persistent state, resumable |
| `conversation_id` | OpenAI API | Named server conversation |
| `previous_response_id` | OpenAI API | Lightweight continuation |

**IMPORTANT:** Cannot mix client-managed (session) with server-managed (conversation_id / previous_response_id) in the same run.

```python
# Manual with to_input_list()
result = await Runner.run(agent, "first question")
new_input = result.to_input_list() + [{"role": "user", "content": "follow-up"}]
result = await Runner.run(agent, new_input)

# Automatic with Sessions
from agents import SQLiteSession
session = SQLiteSession("conversation_123")
result = await Runner.run(agent, "question", session=session)
result = await Runner.run(agent, "follow-up", session=session)

# Server-managed: previous_response_id
result = await Runner.run(agent, user_input,
    previous_response_id=previous_response_id,
    auto_previous_response_id=True)
```

### call_model_input_filter

Filter or trim input before each LLM call:

```python
from agents import RunConfig, CallModelData, ModelInputData

def drop_old_messages(data: CallModelData[None]) -> ModelInputData:
    trimmed = data.model_data.input[-5:]  # Keep last 5 messages
    return ModelInputData(input=trimmed, instructions=data.model_data.instructions)

result = Runner.run_sync(agent, "prompt",
    run_config=RunConfig(call_model_input_filter=drop_old_messages))
```

### Error Handling

```python
from agents import RunConfig, RunErrorHandlerInput, RunErrorHandlerResult

def on_max_turns(_data: RunErrorHandlerInput[None]) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output="Couldn't finish within turn limit",
        include_in_history=False,
    )

result = Runner.run_sync(agent, "prompt", max_turns=3,
    error_handlers={"max_turns": on_max_turns})
```

---

## RunResult

Both `RunResult` and `RunResultStreaming` inherit from `RunResultBase`.

### Properties

| Property | Description |
|----------|-------------|
| `final_output` | Final answer (str, typed object, or None) |
| `input` | Base input for run segment |
| `new_items` | Rich RunItem wrappers with metadata |
| `raw_responses` | Raw ModelResponse objects from each model call |
| `last_agent` | Agent that would handle next user turn |
| `last_response_id` | Latest model response ID |
| `interruptions` | Pending approvals (HITL) |
| `input_guardrail_results` | Input guardrail results |
| `output_guardrail_results` | Output guardrail results |
| `context_wrapper` | App context with usage tracking |

### Methods

```python
# Get input list for continuation
input_list = result.to_input_list()  # mode="preserve_all" (default)
input_list = result.to_input_list(mode="normalized")

# Capture resumable state (for HITL pause/resume)
state = result.to_state()
```

### Item Types in new_items

- `MessageOutputItem` - Text output from the agent
- `ReasoningItem` - Model reasoning (chain-of-thought)
- `ToolCallItem` - Tool call initiated by model
- `ToolCallOutputItem` - Tool execution result
- `ToolApprovalItem` - Pending approval request
- `HandoffCallItem` - Handoff initiated
- `HandoffOutputItem` - Handoff completed
- `ToolSearchCallItem` - Tool search initiated
- `ToolSearchOutputItem` - Tool search results

---

## Exception Classes

| Exception | When Raised |
|-----------|-------------|
| `AgentsException` | Base exception class |
| `MaxTurnsExceeded` | Agent exceeded max_turns limit |
| `ModelBehaviorError` | Malformed JSON, unexpected tool failures |
| `ToolTimeoutError` | Function timeout with `timeout_behavior="raise_exception"` |
| `UserError` | SDK misuse, invalid configuration |
| `InputGuardrailTripwireTriggered` | Input guardrail triggered tripwire |
| `OutputGuardrailTripwireTriggered` | Output guardrail triggered tripwire |

---

## Lifecycle Hooks

### RunHooks (observe entire Runner.run())

```python
class MyRunHooks(RunHooks):
    async def on_agent_start(self, context, agent): ...
    async def on_agent_end(self, context, agent, output): ...
    async def on_llm_start(self, context, agent): ...
    async def on_llm_end(self, context, agent, response): ...
    async def on_tool_start(self, context): ...
    async def on_tool_end(self, context): ...
    async def on_handoff(self, context): ...
```

### AgentHooks (agent-specific)

Set via `agent.hooks = MyAgentHooks()` for callbacks scoped to a single agent.
