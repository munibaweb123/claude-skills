# Context Management

Deep reference for RunContextWrapper, ToolContext, and shared state in the OpenAI Agents SDK.

---

## Overview

Context allows you to share application state, dependencies, and data across agents, tools, and lifecycle hooks within a single `Runner.run()` call.

**Critical Rule:** All agents, tools, and lifecycle hooks within a single run MUST use the identical context type.

---

## RunContextWrapper[T]

The wrapper that carries your application context through the agent loop:

| Property | Description |
|----------|-------------|
| `context` | Your app-defined mutable state/dependencies (type T) |
| `usage` | Aggregated request and token usage metrics |
| `tool_input` | Structured input when executing within `Agent.as_tool()` |
| `approve_tool()` | Programmatic tool approval (HITL) |
| `reject_tool()` | Programmatic tool rejection (HITL) |

### Defining Context

```python
from dataclasses import dataclass

@dataclass
class AppContext:
    user_id: str
    user_name: str
    db_connection: Any
    is_premium: bool = False
```

### Passing Context to Runner

```python
from agents import Agent, Runner

agent = Agent[AppContext](
    name="Assistant",
    instructions="Help the user.",
)

ctx = AppContext(
    user_id="user_123",
    user_name="Alice",
    db_connection=db,
    is_premium=True,
)

result = await Runner.run(agent, "Hello", context=ctx)
```

---

## ToolContext[T]

Extends `RunContextWrapper` with additional tool-specific metadata:

| Field | Description |
|-------|-------------|
| `tool_name` | Name of the tool being executed |
| `tool_call_id` | Unique ID of this tool call |
| `tool_arguments` | Raw arguments string |
| `tool_namespace` | Namespace if using `tool_namespace()` |
| `qualified_tool_name` | Full qualified name (namespace.tool_name) |

### Using ToolContext in Function Tools

```python
from agents import function_tool, ToolContext

@function_tool
def get_user_data(ctx: ToolContext[AppContext], query: str) -> str:
    """Fetch user data using app context."""
    user = ctx.context  # Access AppContext
    print(f"Tool: {ctx.tool_name}, Call ID: {ctx.tool_call_id}")
    return f"Data for {user.user_name}: {query}"
```

---

## Context in Dynamic Instructions

```python
from agents import Agent, RunContextWrapper

def dynamic_instructions(ctx: RunContextWrapper[AppContext], agent: Agent) -> str:
    user = ctx.context
    tier = "premium" if user.is_premium else "standard"
    return f"You are helping {user.user_name} ({tier} tier). Be helpful."

agent = Agent[AppContext](
    name="Assistant",
    instructions=dynamic_instructions,
)
```

---

## Context in Lifecycle Hooks

```python
from agents import RunHooks

class MyHooks(RunHooks[AppContext]):
    async def on_agent_start(self, context: RunContextWrapper[AppContext], agent):
        print(f"Agent {agent.name} started for user {context.context.user_name}")

    async def on_tool_end(self, context: RunContextWrapper[AppContext]):
        print(f"Tool completed. Usage so far: {context.usage}")
```

---

## Data Visibility to LLM

**Context is NOT transmitted to the LLM directly.** Four mechanisms expose context data to the LLM:

| Mechanism | How |
|-----------|-----|
| **Dynamic instructions** | Function receives context, returns string injected as system prompt |
| **Runner input** | The `input` parameter to `Runner.run()` |
| **Function tools** | Tools access context and return data to the LLM |
| **Retrieval/search tools** | External data retrieved via hosted tools |

```python
# Good: expose context data through instructions
def instructions(ctx: RunContextWrapper[AppContext], agent: Agent) -> str:
    return f"User: {ctx.context.user_name}, Premium: {ctx.context.is_premium}"

# Good: expose context data through tools
@function_tool
def get_account_info(ctx: RunContextWrapper[AppContext]) -> str:
    return f"Account: {ctx.context.user_id}, Premium: {ctx.context.is_premium}"
```

---

## Usage Tracking

```python
result = await Runner.run(agent, "Hello", context=ctx)

# Access aggregated usage
usage = result.context_wrapper.usage
print(f"Total tokens: {usage.total_tokens}")
print(f"Prompt tokens: {usage.prompt_tokens}")
print(f"Completion tokens: {usage.completion_tokens}")
print(f"Requests: {usage.requests}")
```

---

## Context Serialization Warning

When using `RunState` serialization (for HITL pause/resume), runtime metadata (usage, approval states) is saved. **Keep secrets out of context objects** for persistence scenarios.

```python
# Bad: secrets in context that gets serialized
@dataclass
class BadContext:
    api_key: str  # Will be serialized with RunState!

# Good: keep secrets separate
@dataclass
class GoodContext:
    user_id: str
    # Access secrets from environment, not context
```

---

## Complete Example

```python
import asyncio
from dataclasses import dataclass
from agents import Agent, Runner, function_tool, RunContextWrapper

@dataclass
class CustomerContext:
    customer_id: str
    customer_name: str
    account_tier: str

@function_tool
async def get_order_history(ctx: RunContextWrapper[CustomerContext]) -> str:
    """Get the customer's recent orders."""
    return f"Orders for {ctx.context.customer_name}: Order #1001, #1002"

@function_tool
async def check_loyalty_points(ctx: RunContextWrapper[CustomerContext]) -> str:
    """Check customer loyalty points."""
    points = 1500 if ctx.context.account_tier == "gold" else 500
    return f"{ctx.context.customer_name} has {points} loyalty points"

def instructions(ctx: RunContextWrapper[CustomerContext], agent: Agent) -> str:
    return (
        f"You are a customer support agent helping {ctx.context.customer_name}. "
        f"Their account tier is {ctx.context.account_tier}. Be friendly and helpful."
    )

agent = Agent[CustomerContext](
    name="Support Agent",
    instructions=instructions,
    tools=[get_order_history, check_loyalty_points],
)

async def main():
    ctx = CustomerContext(
        customer_id="cust_456",
        customer_name="Bob",
        account_tier="gold",
    )
    result = await Runner.run(agent, "What are my recent orders?", context=ctx)
    print(result.final_output)

if __name__ == "__main__":
    asyncio.run(main())
```
