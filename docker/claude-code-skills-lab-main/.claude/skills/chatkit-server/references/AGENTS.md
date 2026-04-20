# Agents Integration

Deep reference for bridging ChatKit with the OpenAI Agents SDK.

---

## AgentContext[TContext]

The context object that flows through agent execution, bridging ChatKit state with the Agents SDK.

### Fields

| Field | Type | Purpose |
|-------|------|---------|
| `thread` | `ThreadMetadata` | Current thread |
| `store` | `Store[TContext]` | Data persistence |
| `request_context` | `TContext` | Your app context (user_id, etc.) |
| `previous_response_id` | `str \| None` | For response chaining |
| `client_tool_call` | `ClientToolCall \| None` | Client tool trigger |
| `workflow_item` | `WorkflowItem \| None` | Active workflow |
| `generated_image_item` | `GeneratedImageItem \| None` | Generated image |

### Methods

| Method | Purpose |
|--------|---------|
| `generate_id(type, thread)` | Generate unique IDs for items |
| `stream_widget(widget, copy_text)` | Stream a widget to the client |
| `stream(event)` | Stream any ThreadStreamEvent |
| `start_workflow(workflow)` | Begin a workflow display |
| `end_workflow(summary, expanded)` | Complete a workflow |
| `update_workflow_task(task, task_index)` | Update a workflow task |
| `add_workflow_task(task)` | Add a task to active workflow |

### Usage

```python
from chatkit.agents import AgentContext

agent_context = AgentContext(
    thread=thread,
    store=self.store,
    request_context=context,
)
```

---

## stream_agent_response()

Converts Agents SDK streaming output to ChatKit events:

```python
from chatkit.agents import stream_agent_response

async stream_agent_response(
    context: AgentContext,
    result: RunResultStreaming,
    *,
    converter: ResponseStreamConverter = _DEFAULT,
) -> AsyncIterator[ThreadStreamEvent]
```

### Basic Usage

```python
from agents import Agent, Runner
from chatkit.agents import AgentContext, simple_to_agent_input, stream_agent_response

assistant = Agent(name="assistant", instructions="Be helpful.", model="gpt-4.1-mini")

async def respond(self, thread, input_user_message, context):
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

---

## simple_to_agent_input()

Converts ChatKit thread items to Agents SDK input format:

```python
from chatkit.agents import simple_to_agent_input

input_items = await simple_to_agent_input(thread_items)
# Returns list compatible with Runner.run_streamed() input
```

**Warning**: Only includes model-visible history. Widgets/workflows emitted directly to the client won't be included unless you add them to `input_items` manually.

---

## ThreadItemConverter

For custom conversion (attachments, tags, hidden context), subclass `ThreadItemConverter`:

```python
from chatkit.agents import ThreadItemConverter

class MyConverter(ThreadItemConverter):
    async def attachment_to_message_content(self, attachment):
        content = await read_bytes(attachment.id)
        if isinstance(attachment, ImageAttachment):
            return ResponseInputImageParam(
                type="input_image", detail="auto",
                image_url=as_data_url(attachment.mime_type, content),
            )
        return ResponseInputTextParam(
            type="input_text",
            text=f"[Attached file: {attachment.name}]",
        )

    async def tag_to_message_content(self, tag):
        summary = await fetch_article_summary(tag.id)
        return ResponseInputTextParam(
            type="input_text",
            text=f"<ARTICLE>\nID: {tag.id}\nTitle: {tag.text}\nSummary: {summary}\n</ARTICLE>",
        )

    async def widget_to_input(self, item):
        return None  # Skip widgets in agent input

    async def hidden_context_to_input(self, item):
        return ResponseInputTextParam(
            type="input_text",
            text=f"[Context: {item.content}]",
        )
```

### Overridable Methods

| Method | Converts |
|--------|----------|
| `attachment_to_message_content` | File/image attachments |
| `tag_to_message_content` | @-mention entity tags |
| `generated_image_to_input` | Generated images |
| `hidden_context_to_input` | Integration-defined hidden context |
| `sdk_hidden_context_to_input` | SDK-internal hidden context |
| `task_to_input` | Task items |
| `workflow_to_input` | Workflow items |
| `widget_to_input` | Widget items |

---

## ResponseStreamConverter

Customize how Agents SDK stream events become ChatKit events:

```python
from chatkit.agents import ResponseStreamConverter

class MyResponseConverter(ResponseStreamConverter):
    async def base64_image_to_url(self, image_id, base64_image, partial_index):
        # Upload to blob storage and return URL
        url = await upload_to_s3(base64_image)
        return url

    async def url_citation_to_annotation(self, url_citation):
        return Annotation(
            source=URLSource(url=url_citation.url, title=url_citation.title),
            index=url_citation.index,
        )
```

### Overridable Methods

| Method | Purpose |
|--------|---------|
| `base64_image_to_url` | Convert base64 images to URLs |
| `partial_image_index_to_progress` | Map partial image index to progress float |
| `file_citation_to_annotation` | Convert file citations to annotations |
| `container_file_citation_to_annotation` | Convert container file citations |
| `url_citation_to_annotation` | Convert URL citations to annotations |

---

## ClientToolCall

For triggering client-side tool execution:

```python
from chatkit.agents import ClientToolCall

class ClientToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]
```

See `references/TOOLS.md` for complete client tool patterns.

---

## Workflow Streaming

Display multi-step progress to the user:

```python
from chatkit.types import Workflow, CustomTask

@function_tool()
async def analyze_data(ctx: RunContextWrapper[AgentContext], query: str):
    # Start workflow
    await ctx.context.start_workflow(Workflow(
        type="custom",
        tasks=[
            CustomTask(title="Loading data", status_indicator="loading"),
            CustomTask(title="Analyzing", status_indicator="none"),
        ],
    ))

    # Update tasks as work progresses
    data = await load_data(query)
    await ctx.context.update_workflow_task(
        CustomTask(title="Loading data", status_indicator="complete"), task_index=0
    )
    await ctx.context.update_workflow_task(
        CustomTask(title="Analyzing", status_indicator="loading"), task_index=1
    )

    result = await analyze(data)
    await ctx.context.end_workflow(summary=WorkflowSummary(text="Analysis complete"))
    return result
```
