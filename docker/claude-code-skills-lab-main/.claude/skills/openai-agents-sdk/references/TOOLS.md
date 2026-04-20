# Tools

Deep reference for all tool types in the OpenAI Agents SDK: function tools, hosted tools, agents as tools, and more.

---

## Five Tool Categories

| Category | Description | Execution |
|----------|-------------|-----------|
| **Hosted OpenAI tools** | WebSearchTool, FileSearchTool, CodeInterpreterTool, etc. | OpenAI servers |
| **Local/runtime tools** | ComputerTool, ApplyPatchTool, ShellTool | Local machine |
| **Function calling** | Python functions via `@function_tool` | Your code |
| **Agents as tools** | `agent.as_tool()` | Nested agent run |
| **Experimental** | Codex tool | Sandbox |

---

## @function_tool Decorator

### Basic Usage

```python
from agents import function_tool

@function_tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"The weather in {city} is sunny."
```

### Full Options

```python
from typing import Annotated
from agents import function_tool, RunContextWrapper

@function_tool(
    name_override="custom_name",          # Override tool name
    defer_loading=True,                    # Deferred loading with ToolSearchTool
    timeout=2.0,                           # Timeout in seconds (async only)
    timeout_behavior="error_as_result",    # or "raise_exception"
    timeout_error_function=None,           # Custom timeout message
    failure_error_function=None,           # Custom failure message
    use_docstring_info=True,               # Parse docstring for description
    docstring_style="google",              # "google", "sphinx", "numpy"
    needs_approval=True,                   # Require human approval
)
async def my_tool(
    ctx: RunContextWrapper[MyContext],      # Optional context access
    param: Annotated[str, "Parameter description"],
    count: Annotated[int, "Number of items"] = 5,
) -> str:
    """Tool description from docstring.

    Args:
        param: The search parameter
        count: How many items to return
    """
    return f"Result for {param}, count={count}"
```

### Parameter Annotations

Use `Annotated` for parameter descriptions and Pydantic `Field` for constraints:

```python
from typing import Annotated
from pydantic import Field

@function_tool
def score_review(
    score: Annotated[int, Field(..., ge=0, le=100, description="Review score")],
    comment: Annotated[str, "Review comment"],
) -> str:
    return f"Score: {score}, Comment: {comment}"
```

### Context Access

Function tools can optionally receive `RunContextWrapper` or `ToolContext` as first parameter:

```python
from agents import function_tool, RunContextWrapper, ToolContext

# RunContextWrapper - access shared state
@function_tool
async def fetch_user(ctx: RunContextWrapper[UserInfo]) -> str:
    return f"User age: {ctx.context.age}"

# ToolContext - access tool metadata too
@function_tool
def get_info(ctx: ToolContext[MyContext], query: str) -> str:
    print(f"Tool name: {ctx.tool_name}")
    print(f"Tool call ID: {ctx.tool_call_id}")
    return f"Info for {query}"
```

### Return Types

Supported return types beyond `str`:

```python
from agents import ToolOutputText, ToolOutputImage, ToolOutputFileContent

@function_tool
def generate_report() -> list:
    return [
        ToolOutputText(text="Report summary"),
        ToolOutputImage(image_url="https://example.com/chart.png"),
    ]
```

### Timeout Behavior

Only for async functions:

| Behavior | Effect |
|----------|--------|
| `"error_as_result"` (default) | Timeout message sent back to model as tool result |
| `"raise_exception"` | Raises `ToolTimeoutError` |

### Custom FunctionTool

For dynamic tool creation without decorators:

```python
from agents import FunctionTool

async def handler(ctx, args_json: str) -> str:
    import json
    args = json.loads(args_json)
    return f"Result: {args['query']}"

tool = FunctionTool(
    name="dynamic_search",
    description="Search dynamically",
    params_json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"],
    },
    on_invoke_tool=handler,
)
```

---

## Hosted OpenAI Tools

### WebSearchTool

```python
from agents import WebSearchTool

agent = Agent(
    name="Researcher",
    tools=[WebSearchTool()],
)
```

### FileSearchTool

```python
from agents import FileSearchTool

agent = Agent(
    name="Document Agent",
    tools=[
        FileSearchTool(
            vector_store_ids=["vs_abc123"],
            max_num_results=5,
            include_search_results=True,
        ),
    ],
)
```

Parameters: `max_num_results`, `vector_store_ids`, `filters`, `ranking_options`, `include_search_results`.

### CodeInterpreterTool

```python
from agents import CodeInterpreterTool

agent = Agent(
    name="Code Agent",
    tools=[CodeInterpreterTool()],
)
```

### ImageGenerationTool

```python
from agents import ImageGenerationTool

agent = Agent(
    name="Image Agent",
    tools=[ImageGenerationTool()],
)
```

---

## ToolSearchTool (Deferred Loading)

For agents with many tools, defer loading to reduce prompt size:

```python
from agents import Agent, ToolSearchTool, function_tool
from agents.tool_context import tool_namespace

@function_tool(defer_loading=True)
def get_customer_profile(customer_id: str) -> str:
    return f"Profile for {customer_id}"

@function_tool(defer_loading=True)
def get_order_history(customer_id: str) -> str:
    return f"Orders for {customer_id}"

# Group related tools with namespaces
crm_tools = tool_namespace(
    name="crm",
    description="Customer relationship management tools",
    tools=[get_customer_profile, get_order_history],
)

agent = Agent(
    name="Support",
    model="gpt-5.4",
    tools=[*crm_tools, ToolSearchTool()],
)
```

**Best practices:**
- Add exactly one `ToolSearchTool()` when using deferred-loading tools
- Group tools with `tool_namespace()` for better organization
- Namespaces should contain fewer than 10 functions
- Named `tool_choice` cannot target deferred-only tools

---

## Agent.as_tool()

Convert an agent into a tool callable by another agent:

```python
researcher = Agent(name="Researcher", instructions="Research topics thoroughly.")

tool = researcher.as_tool(
    tool_name="research",
    tool_description="Research a topic in depth",
    max_turns=5,
    run_config=RunConfig(...),
    hooks=RunHooks(...),
    needs_approval=True,                 # Boolean or callable
    parameters=ResearchInput,            # Pydantic model for structured input
    include_input_schema=True,
    custom_output_extractor=extract_fn,  # Async callable
    is_enabled=True,                     # Boolean, callable, or async callable
    on_stream=handle_stream,             # Streaming callback
)

orchestrator = Agent(
    name="Orchestrator",
    instructions="Use research tool for gathering information.",
    tools=[tool],
)
```

### Streaming Nested Agent Runs

```python
async def handle_stream(event: AgentToolStreamEvent) -> None:
    print(f"[{event['agent'].name}] {event['event'].type}")

tool = agent.as_tool(
    tool_name="worker",
    tool_description="Worker agent",
    on_stream=handle_stream,
)
```

---

## ShellTool

Execute shell commands in a containerized environment:

```python
from agents import ShellTool

agent = Agent(
    name="Shell Agent",
    tools=[
        ShellTool(environment={
            "type": "container_auto",
            "network_policy": {"type": "disabled"},
        }),
    ],
)
```

---

## ComputerTool

Desktop automation with screenshot, click, type, scroll:

```python
from agents import ComputerTool

# Implement the AsyncComputer interface
class MyComputer(AsyncComputer):
    async def screenshot(self): ...
    async def click(self, x, y, button="left"): ...
    async def type(self, text): ...
    async def scroll(self, x, y, delta_x, delta_y): ...
    async def keypress(self, keys): ...
    async def wait(self, ms): ...
    async def move(self, x, y): ...
    async def drag(self, path): ...
    async def double_click(self, x, y): ...

agent = Agent(
    name="Desktop Agent",
    tools=[ComputerTool(computer=MyComputer())],
)
```

---

## Tool Error Formatting

Customize error messages sent to the model on tool failures:

```python
from agents import RunConfig, ToolErrorFormatterArgs

def format_rejection(args: ToolErrorFormatterArgs[None]) -> str | None:
    if args.kind == "approval_rejected":
        return f"Tool '{args.tool_name}' was rejected. Propose an alternative."
    return None  # Use default message

config = RunConfig(tool_error_formatter=format_rejection)
```

`ToolErrorFormatterArgs` fields: `kind`, `tool_type`, `tool_name`, `call_id`, `default_message`, `run_context`.
