---
name: openai-agents-sdk
description: Comprehensive OpenAI Agents SDK skill for building AI agents from hello world to professional production systems. Use when building AI agents with OpenAI Agents SDK, creating multi-agent systems, implementing function tools, configuring handoffs, adding guardrails, managing sessions, integrating MCP servers, streaming responses, tracing agent runs, building voice/realtime agents, or deploying production agent workflows. Covers Agent, Runner, tools, handoffs, guardrails, context, tracing, sessions, MCP, human-in-the-loop, and multi-agent orchestration patterns.
---

# OpenAI Agents SDK Skill

This skill provides comprehensive support for building AI agents with the OpenAI Agents SDK (Python), from simple hello world examples to professional production-ready multi-agent systems. Before providing specific recommendations, this skill gathers context about your requirements and constraints.

## When to Use This Skill

Use this skill when you need to:
- Build AI agents with the OpenAI Agents SDK (`openai-agents` Python package)
- Create function tools, hosted tools, or use agents as tools
- Implement multi-agent orchestration with handoffs or agents-as-tools
- Add input/output guardrails for safety and validation
- Manage conversation state with sessions (SQLite, Redis, SQLAlchemy, Dapr)
- Integrate MCP servers (hosted, streamable HTTP, SSE, stdio)
- Stream agent responses in real-time
- Implement human-in-the-loop approval flows
- Configure tracing and observability for agent runs
- Build voice/realtime agents with WebSocket or SIP transport
- Deploy production agent systems with error handling, retries, and monitoring

## Pre-Implementation Context Gathering

Before providing specific recommendations, this skill gathers important context:

### Team Experience Assessment
- What is your team's current experience with the OpenAI Agents SDK? (beginner, intermediate, advanced)
- Have you worked with LLM-based agent systems before?
- Are you familiar with async Python (asyncio)?

### Use Case Requirements
- What type of agent are you building? (single agent, multi-agent, voice/realtime)
- Do you need tool calling? What tools will agents use?
- Do you need conversation persistence (sessions)?
- Do you need human-in-the-loop approval for sensitive actions?

### Infrastructure Constraints
- What is your deployment target? (local, cloud, serverless)
- Do you need to use non-OpenAI model providers? (Azure, LiteLLM, custom)
- Do you have existing MCP servers to integrate?
- What are your latency and throughput requirements?

### Safety & Compliance
- Do you need input/output guardrails?
- Are there content safety or PII requirements?
- Do you need audit trails via tracing?

## Prerequisites

- Python 3.9+
- `pip install openai-agents`
- `export OPENAI_API_KEY=sk-...`
- Optional extras: `pip install openai-agents[viz]` (visualization), `pip install openai-agents[redis]` (Redis sessions), `pip install openai-agents[litellm]` (LiteLLM provider)

## Quick Start: Hello World

### Step 1: Minimal Agent

```python
import asyncio
from agents import Agent, Runner

agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
)

async def main():
    result = await Runner.run(agent, "What is the capital of France?")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 2: Add a Tool

```python
import asyncio
from agents import Agent, Runner, function_tool

@function_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is sunny, 22°C."

agent = Agent(
    name="Weather Assistant",
    instructions="Help users with weather questions. Use the get_weather tool.",
    tools=[get_weather],
)

async def main():
    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 3: Multi-Agent with Handoffs

```python
import asyncio
from agents import Agent, Runner

history_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions="You answer history questions clearly and concisely.",
)

math_agent = Agent(
    name="Math Tutor",
    handoff_description="Specialist agent for math questions",
    instructions="You explain math step by step with worked examples.",
)

triage_agent = Agent(
    name="Triage Agent",
    instructions="Route each question to the right specialist.",
    handoffs=[history_agent, math_agent],
)

async def main():
    result = await Runner.run(
        triage_agent,
        "Who was the first president of the United States?",
    )
    print(result.final_output)
    print(f"Answered by: {result.last_agent.name}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Step 4: Sync Execution (No asyncio)

```python
from agents import Agent, Runner

agent = Agent(name="Assistant", instructions="Reply concisely.")
result = Runner.run_sync(agent, "Hello!")
print(result.final_output)
```

## SDK Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                    Runner.run()                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              Agent Loop                          │ │
│  │  1. Call LLM with agent instructions + input     │ │
│  │  2. Process output:                              │ │
│  │     ├─ Final output → return result              │ │
│  │     ├─ Tool calls → execute tools, loop again    │ │
│  │     └─ Handoff → switch agent, loop again        │ │
│  │  3. MaxTurnsExceeded if limit breached           │ │
│  └─────────────────────────────────────────────────┘ │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │  Agent    │  │  Tools   │  │  Guardrails       │  │
│  │  - name   │  │  - func  │  │  - input guards   │  │
│  │  - instr  │  │  - hosted│  │  - output guards  │  │
│  │  - tools  │  │  - agent │  │  - tool guards    │  │
│  │  - model  │  │  - MCP   │  │                   │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
│                                                       │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Handoffs │  │ Sessions │  │  Tracing           │  │
│  │          │  │ (state)  │  │  (observability)   │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Core Primitives

| Primitive | Purpose | Key Class |
|-----------|---------|-----------|
| **Agent** | LLM with instructions and tools | `Agent(name, instructions, tools, handoffs)` |
| **Runner** | Executes agent loop | `Runner.run()`, `Runner.run_sync()`, `Runner.run_streamed()` |
| **Tools** | Extend agent capabilities | `@function_tool`, `WebSearchTool`, `Agent.as_tool()` |
| **Handoffs** | Delegate between agents | `handoff(agent, ...)`, agent `handoffs=[...]` |
| **Guardrails** | Validate input/output | `@input_guardrail`, `@output_guardrail` |
| **Context** | Share state across tools/agents | `RunContextWrapper[T]` |
| **Tracing** | Observability and debugging | `trace()`, spans, exporters |
| **Sessions** | Persistent conversation state | `SQLiteSession`, `RedisSession`, etc. |
| **MCP** | External tool servers | `MCPServerStdio`, `MCPServerStreamableHttp` |

## Agent Configuration

### Agent Parameters

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Required identifier |
| `instructions` | `str \| Callable` | Static or dynamic system prompt |
| `tools` | `list` | Function tools, hosted tools |
| `handoffs` | `list[Agent \| Handoff]` | Agents to hand off to |
| `model` | `str` | Model override (e.g., `"gpt-4.1"`) |
| `model_settings` | `ModelSettings` | Temperature, top_p, tool_choice |
| `output_type` | `type` | Pydantic model for structured output |
| `input_guardrails` | `list` | Input validation guardrails |
| `output_guardrails` | `list` | Output validation guardrails |
| `hooks` | `AgentHooks` | Lifecycle callbacks |
| `mcp_servers` | `list` | MCP server integrations |
| `tool_use_behavior` | | Controls post-tool-call behavior |
| `handoff_description` | `str` | Description when used as handoff target |

### Dynamic Instructions

```python
def dynamic_instructions(context: RunContextWrapper, agent: Agent) -> str:
    return f"You are helping user {context.context.user_name}. Be concise."

agent = Agent(name="Assistant", instructions=dynamic_instructions)
```

### Structured Output

```python
from pydantic import BaseModel
from agents import Agent, Runner

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

agent = Agent(
    name="Event Extractor",
    instructions="Extract event details from text.",
    output_type=CalendarEvent,
)

result = Runner.run_sync(agent, "Meeting with Alice and Bob on Friday at 3pm")
event = result.final_output  # CalendarEvent instance
```

### ModelSettings

```python
from agents import Agent, ModelSettings

agent = Agent(
    name="Reasoner",
    model="gpt-5.4",
    model_settings=ModelSettings(
        temperature=0.7,
        top_p=0.9,
        tool_choice="auto",
        parallel_tool_calls=True,
    ),
)
```

### tool_use_behavior

| Value | Behavior |
|-------|----------|
| `"run_llm_again"` (default) | LLM processes tool results and generates final output |
| `"stop_on_first_tool"` | First tool output becomes final response |
| `StopAtTools(stop_at_tool_names=[...])` | Stop only on specified tools |

## Running Agents

### Three Execution Modes

| Method | Type | Returns |
|--------|------|---------|
| `Runner.run(agent, input)` | Async | `RunResult` |
| `Runner.run_sync(agent, input)` | Sync | `RunResult` |
| `Runner.run_streamed(agent, input)` | Async streaming | `RunResultStreaming` |

### Multi-Turn Conversation

```python
# Manual state management
result = await Runner.run(agent, "What is Python?")
new_input = result.to_input_list() + [{"role": "user", "content": "Tell me more."}]
result = await Runner.run(agent, new_input)

# Automatic with sessions
from agents import SQLiteSession
session = SQLiteSession("conversation_123")
result = await Runner.run(agent, "What is Python?", session=session)
result = await Runner.run(agent, "Tell me more.", session=session)
```

### RunConfig

```python
from agents import RunConfig

config = RunConfig(
    model="gpt-4.1",                    # Global model override
    tracing_disabled=False,              # Enable/disable tracing
    trace_include_sensitive_data=False,  # PII protection
    workflow_name="my_workflow",         # Trace workflow name
)

result = await Runner.run(agent, "Hello", run_config=config)
```

### Error Handling

```python
from agents import AgentsException, MaxTurnsExceeded

try:
    result = await Runner.run(agent, "Complex task", max_turns=5)
except MaxTurnsExceeded:
    print("Agent exceeded maximum turns")
except AgentsException as e:
    print(f"Agent error: {e}")
```

## Tools Quick Reference

### Function Tools

```python
from typing import Annotated
from agents import function_tool, RunContextWrapper

@function_tool
def search_database(query: Annotated[str, "Search query"]) -> str:
    """Search the database for records matching the query."""
    return f"Found 3 results for: {query}"

# With context access
@function_tool
async def get_user_data(ctx: RunContextWrapper[MyContext]) -> str:
    """Get current user data."""
    return f"User: {ctx.context.user_name}"

# With timeout
@function_tool(timeout=5.0, timeout_behavior="error_as_result")
async def slow_operation(param: str) -> str:
    """Operation that may timeout."""
    return "result"
```

### Hosted Tools

```python
from agents import Agent, WebSearchTool, FileSearchTool, CodeInterpreterTool

agent = Agent(
    name="Research Agent",
    tools=[
        WebSearchTool(),
        FileSearchTool(
            vector_store_ids=["vs_abc123"],
            max_num_results=5,
        ),
        CodeInterpreterTool(),
    ],
)
```

### Agents as Tools

```python
researcher = Agent(name="Researcher", instructions="Research topics thoroughly.")
writer = Agent(name="Writer", instructions="Write clear summaries.")

orchestrator = Agent(
    name="Orchestrator",
    instructions="Use researcher for facts, then writer for summaries.",
    tools=[
        researcher.as_tool(
            tool_name="research",
            tool_description="Research a topic in depth",
        ),
        writer.as_tool(
            tool_name="write_summary",
            tool_description="Write a clear summary",
        ),
    ],
)
```

## Handoffs Quick Reference

```python
from agents import Agent, handoff

# Simple: add agents to handoffs list
triage = Agent(
    name="Triage",
    handoffs=[billing_agent, support_agent],
)

# Advanced: with custom configuration
from agents import handoff

h = handoff(
    agent=billing_agent,
    tool_name_override="route_to_billing",
    tool_description_override="Transfer to billing for payment issues",
    on_handoff=lambda ctx: print("Handing off to billing"),
)
triage = Agent(name="Triage", handoffs=[h])
```

**Key rules:**
- Handoffs stay within a single `Runner.run()` call
- Input guardrails apply only to the **first** agent
- Output guardrails apply only to the **final** agent
- Use `handoff_description` on target agents for better routing

## Guardrails Quick Reference

```python
from agents import Agent, input_guardrail, output_guardrail, GuardrailFunctionOutput

@input_guardrail
async def block_harmful_input(ctx, agent, input) -> GuardrailFunctionOutput:
    if "harmful" in str(input).lower():
        return GuardrailFunctionOutput(
            output_info="Blocked harmful content",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info="OK", tripwire_triggered=False)

@output_guardrail
async def check_output_quality(ctx, agent, output) -> GuardrailFunctionOutput:
    if len(str(output)) < 10:
        return GuardrailFunctionOutput(
            output_info="Output too short",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info="OK", tripwire_triggered=False)

agent = Agent(
    name="Safe Agent",
    input_guardrails=[block_harmful_input],
    output_guardrails=[check_output_quality],
)
```

## Sessions Quick Reference

```python
from agents import Agent, Runner, SQLiteSession

# In-memory session
session = SQLiteSession("user_123")

# File-backed session
session = SQLiteSession("user_123", "conversations.db")

# Multi-turn conversation with automatic history
agent = Agent(name="Assistant", instructions="Reply concisely.")
result = await Runner.run(agent, "What is Python?", session=session)
result = await Runner.run(agent, "What state is it in?", session=session)
# Agent automatically remembers previous turns
```

**Available session backends:** SQLiteSession, AsyncSQLiteSession, RedisSession, SQLAlchemySession, DaprSession, OpenAIConversationsSession, OpenAIResponsesCompactionSession, AdvancedSQLiteSession, EncryptedSession

## Production Best Practices

### Required
- Set `max_turns` to prevent infinite loops
- Use guardrails for user-facing agents
- Enable tracing for debugging and monitoring
- Handle `MaxTurnsExceeded` and `AgentsException` exceptions
- Use structured outputs (`output_type`) for downstream processing
- Set `trace_include_sensitive_data=False` in production

### Recommended
- Use sessions for multi-turn conversations (not manual `to_input_list()`)
- Implement human-in-the-loop for destructive operations
- Use `RunConfig` for consistent configuration across runs
- Cache MCP tool lists with `cache_tools_list=True`
- Use `flush_traces()` in long-running workers (Celery, etc.)
- Configure retry settings for resilience

### Anti-Patterns
- **Don't** mix client-managed sessions with server-managed (`conversation_id`/`previous_response_id`)
- **Don't** put secrets in context objects if using state serialization
- **Don't** skip `flush_traces()` in worker processes
- **Don't** use `tool_choice="required"` without `reset_tool_choice=True` (default) to avoid infinite loops

## Common Troubleshooting

### Agent Loops Infinitely on Tools
- Check `reset_tool_choice` is `True` (default) - resets `tool_choice` to `"auto"` after tool call
- Set `max_turns` to cap iterations

### Tracing 401 Errors
- Disable tracing: `set_tracing_disabled(True)`
- Or set separate tracing key: `set_tracing_export_api_key("sk-...")`

### MCP Tool Not Appearing
- Ensure server is connected (`async with` context manager)
- Check `cache_tools_list` - call `invalidate_tools_cache()` if tools changed
- Verify tool filtering isn't excluding your tool

### Structured Output Failures
- Ensure output_type is a valid Pydantic model, dataclass, or TypedDict
- Some non-OpenAI providers lack `json_schema` support

### Responses API 404 Errors
- Switch to Chat Completions: `set_default_openai_api("chat_completions")`
- Some providers only support Chat Completions API

## Decision Tree

```
What do you need?
│
├─ First agent? → See "Quick Start: Hello World"
├─ Add capabilities to agent?
│   ├─ Python functions → @function_tool
│   ├─ Web search, file search, code exec → Hosted Tools
│   ├─ External tool server → MCP Integration
│   └─ Another agent's help → Agent.as_tool()
├─ Multiple specialized agents?
│   ├─ Agent responds directly → Handoffs
│   └─ Orchestrator controls flow → Agents as Tools
├─ Validate input/output? → Guardrails
├─ Persist conversation? → Sessions
├─ Approve sensitive actions? → Human-in-the-Loop
├─ Real-time streaming? → Runner.run_streamed()
├─ Voice/audio interaction? → RealtimeAgent
└─ Debug/monitor? → Tracing
```

## Reference Documentation

| Reference | Description |
|-----------|-------------|
| [CORE_CONCEPTS.md](references/CORE_CONCEPTS.md) | Agent, Runner, RunResult, agent loop lifecycle |
| [TOOLS.md](references/TOOLS.md) | Function tools, hosted tools, agents as tools, ToolSearchTool |
| [HANDOFFS.md](references/HANDOFFS.md) | Agent handoffs, input filters, history management |
| [GUARDRAILS.md](references/GUARDRAILS.md) | Input, output, and tool guardrails with tripwires |
| [CONTEXT.md](references/CONTEXT.md) | RunContextWrapper, ToolContext, shared state |
| [TRACING.md](references/TRACING.md) | Traces, spans, exporters, integrations |
| [STREAMING.md](references/STREAMING.md) | Stream events, WebSocket transport, cancellation |
| [SESSIONS.md](references/SESSIONS.md) | All session backends, custom sessions, compaction |
| [MCP.md](references/MCP.md) | MCP server integration (hosted, HTTP, SSE, stdio) |
| [HUMAN_IN_THE_LOOP.md](references/HUMAN_IN_THE_LOOP.md) | Approval flows, RunState, pause/resume |
| [MULTI_AGENT.md](references/MULTI_AGENT.md) | LLM-based and code-based orchestration patterns |
| [MODELS.md](references/MODELS.md) | Model configuration, providers, retries, WebSocket |
| [REALTIME.md](references/REALTIME.md) | Voice agents, RealtimeAgent, SIP telephony |
| [CONFIGURATION.md](references/CONFIGURATION.md) | Global config, environment variables, logging |
| [PRODUCTION.md](references/PRODUCTION.md) | Production deployment, error handling, scaling |
