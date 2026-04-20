# Tools

Deep reference for client tools, server tools, progress updates, and client effects in ChatKit.

---

## Client Tools (Server-Triggered, Client-Executed)

Client tools allow the server to trigger actions that execute on the frontend (e.g., reading canvas state, opening a dialog).

**Constraint**: Only one client tool call can run per turn.

### Server-Side Setup

```python
from agents import Agent, StopAtTools, function_tool, RunContextWrapper
from chatkit.agents import AgentContext, ClientToolCall

@function_tool(description_override="Read the user's current selection.")
async def get_selected_items(ctx: RunContextWrapper[AgentContext]) -> None:
    ctx.context.client_tool_call = ClientToolCall(
        name="get_selected_items",
        arguments={"project": "my_project"},
    )

assistant = Agent[AgentContext](
    model="gpt-4.1",
    name="Assistant",
    instructions="You are a helpful assistant.",
    tools=[get_selected_items],
    tool_use_behavior=StopAtTools(
        stop_at_tool_names=[get_selected_items.name]
    ),
)
```

### Client-Side Handler

```javascript
const chatkit = useChatKit({
  onClientTool: async ({ name, params }) => {
    if (name === "get_selected_items") {
      const items = myApp.getSelectedItems(params.project);
      return { items: items.map(i => ({ id: i.id, type: i.type })) };
    }
  },
});
```

The client tool result is sent back to the server via `ThreadsAddClientToolOutputReq`, which triggers another `respond()` call.

---

## Server Tools (with Progress Updates)

Stream progress updates to the client during long-running tool execution:

```python
from agents import function_tool, RunContextWrapper
from chatkit.agents import AgentContext
from chatkit.types import ProgressUpdateEvent

@function_tool()
async def ingest_files(ctx: RunContextWrapper[AgentContext], paths: list[str]):
    await ctx.context.stream(
        ProgressUpdateEvent(icon="upload", text="Uploading files...")
    )
    await upload(paths)

    await ctx.context.stream(
        ProgressUpdateEvent(icon="search", text="Indexing content...")
    )
    await index_files(paths)

    await ctx.context.stream(
        ProgressUpdateEvent(icon="check", text="Processing complete")
    )
    return f"Indexed {len(paths)} files"
```

Progress updates are **transient** -- they are displayed in the UI but not stored.

### From respond() directly

```python
async def respond(self, thread, input_user_message, context):
    yield ProgressUpdateEvent(icon="search", text="Searching tickets...")
    # ... do work, then yield agent events
```

---

## Client Effects (Fire-and-Forget)

Send one-way events to the client without expecting a response:

### Server-Side

```python
from chatkit.types import ClientEffectEvent

yield ClientEffectEvent(
    name="highlight_text",
    data={"index": 142, "length": 35},
)
```

### Client-Side Handler

```javascript
const chatkit = useChatKit({
  onEffect: async ({ name, data }) => {
    if (name === "highlight_text") {
      highlightArticleText(data);
    }
  },
});
```

---

## Composer Tool Selection

Allow users to pick tools from the composer UI:

### Client Config

```javascript
composer: {
  tools: [
    {
      id: "web_search",
      icon: "search",
      label: "Web Search",
      shortLabel: "Web",
      placeholderOverride: "Search the web...",
    },
    {
      id: "code_review",
      icon: "square-code",
      label: "Code Review",
      shortLabel: "Code",
    },
  ],
}
```

### Server-Side Access

```python
async def respond(self, thread, input_user_message, context):
    if input_user_message and input_user_message.inference_options:
        tool_choice = input_user_message.inference_options.tool_choice
        if tool_choice and tool_choice.id == "web_search":
            # Use web search agent
            ...
```

**Warning**: `inference_options` may be `None` if the user doesn't pick anything; always check and fall back to defaults.

---

## Model Selection

Allow users to pick models from the composer:

```javascript
composer: {
  models: [
    { id: "gpt-4.1", label: "GPT-4.1", description: "Most capable", default: true },
    { id: "gpt-4.1-mini", label: "GPT-4.1 Mini", description: "Fast and efficient" },
  ],
}
```

```python
# Server-side
model = "gpt-4.1"  # default
if input_user_message and input_user_message.inference_options:
    if input_user_message.inference_options.model:
        model = input_user_message.inference_options.model
```

---

## Image Generation

```python
from agents import Agent
from agents.tool import ImageGenerationTool

agent = Agent(
    name="designer",
    instructions="Generate images when asked.",
    tools=[ImageGenerationTool(tool_config={"type": "image_generation"})],
)

# With partial image streaming
agent = Agent(
    name="designer",
    instructions="Generate images.",
    tools=[ImageGenerationTool(
        tool_config={"type": "image_generation", "partial_images": 3}
    )],
)
```

Override `ResponseStreamConverter.base64_image_to_url` to convert base64 to URLs for persistent storage.
