# Widgets

Deep reference for interactive UI components in the ChatKit Python SDK.

---

## Overview

Widgets are interactive UI components rendered inside the chat. They support actions, forms, streaming updates, and dynamic content. Build widgets at https://widgets.chatkit.studio/ and render them server-side with `WidgetTemplate`.

---

## WidgetTemplate

Load and render widget definitions:

```python
from chatkit.widgets import WidgetTemplate

# Load from .widget file
template = WidgetTemplate.from_file("my_widget.widget")

# Build with data
widget = template.build(data={"title": "Hello", "items": [1, 2, 3]})
```

**Note**: `from_file()` resolves paths relative to the caller's directory. `build_basic()` is **deprecated** -- use `build()` instead.

---

## Streaming Widgets from respond()

```python
from chatkit.server import stream_widget

async def respond(self, thread, input_user_message, context):
    widget = template.build(data={"user": "Alice", "message": "Welcome!"})
    async for event in stream_widget(
        thread, widget, copy_text="Welcome message",
        generate_id=lambda item_type: self.store.generate_item_id(
            item_type, thread, context
        ),
    ):
        yield event
```

## Streaming Widgets from Tools

```python
from agents import function_tool, RunContextWrapper
from chatkit.agents import AgentContext

@function_tool(description_override="Show a summary widget")
async def show_summary(ctx: RunContextWrapper[AgentContext], text: str):
    widget = template.build(data={"summary": text})
    await ctx.context.stream_widget(widget, copy_text=text)
```

---

## Progressive Widget Updates

Only `<Text>` and `<Markdown>` components with an `id` attribute support streamed text updates:

```python
async def widget_generator() -> AsyncGenerator[WidgetRoot, None]:
    message = ""
    async for event in agent_result.stream_events():
        if event.type == "raw_response_event" and \
           event.data.type == "response.output_text.delta":
            message += event.data.delta
            yield template.build(data={"message": message})
    yield template.build(data={"message": message})

await ctx.context.stream_widget(widget_generator())
```

---

## Widget Root Types

| Type | Use Case |
|------|----------|
| `Card` | Light border container; supports confirm/cancel actions; can act as form with `asForm=True` |
| `ListView` | Scroll-friendly list; children must be `<ListViewItem>` elements |
| `Basic` | Minimal container for entity previews only |

---

## Widget Actions

### Server-Side Action Handler

```python
from chatkit.types import Action, WidgetItem

class MyChatKitServer(ChatKitServer[RequestContext]):
    async def action(
        self,
        thread: ThreadMetadata,
        action: Action[str, Any],
        sender: WidgetItem | None,
        context: RequestContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        if action.type == "submit_form":
            name = action.payload.get("name")
            # Process the form data...
            yield ThreadItemDoneEvent(item=...)
        elif action.type == "delete_item":
            item_id = action.payload.get("item_id")
            # Handle deletion...
```

### Non-Streaming Action

```python
async def sync_action(self, thread, action, sender, context):
    return SyncCustomActionResponse(data={"status": "ok"})
```

### Form Values

Form field values arrive in `action.payload` with names from `editable={{ name: "field_name" }}`. Nested naming: `editable={{ name: "todo.title" }}` produces `action.payload["todo"]["title"]`.

**Warning**: Treat action payloads as untrusted input from the client.

### Loading Behavior

| Value | Behavior |
|-------|----------|
| `auto` | Adapts to context (default) |
| `self` | Loading on specific widget node |
| `container` | Loading on entire widget (fades out) |
| `none` | No loading state |

---

## Widget Diff (stream_widget internals)

```python
from chatkit.server import diff_widget

changes = diff_widget(before=old_widget, after=new_widget)
# Returns: list of WidgetStreamingTextValueDelta, WidgetRootUpdated, WidgetComponentUpdated
```

---

## Widget Component Library (60+)

**Layout**: Box, Row, Col, Spacer, Divider
**Text**: Title, Label, Caption, Markdown, Text
**Forms**: Input, Textarea, Checkbox, Select, RadioGroup, DatePicker
**Data Display**: Table, ListView, Card, ListViewItem
**Actions**: Button
**Media**: Image, Icon

Build widgets visually at https://widgets.chatkit.studio/
