# Types

Deep reference for all ChatKit type definitions in `chatkit.types`.

---

## Thread Types

### ThreadMetadata

```python
ThreadMetadata(
    id: str,
    title: str,
    created_at: datetime,
    status: ThreadStatus,           # ActiveStatus | LockedStatus | ClosedStatus
    allowed_image_domains: list[str],
    metadata: dict,                 # Custom metadata (e.g., last_response_id)
)
```

### ThreadStatus (discriminated union)

```python
from chatkit.types import ActiveStatus, LockedStatus, ClosedStatus

thread.status = ActiveStatus()                          # Default
thread.status = LockedStatus(reason="Escalated.")       # Temporary pause
thread.status = ClosedStatus(reason="Resolved.")        # Permanent closure
```

---

## Thread Item Types (discriminated union `ThreadItem`)

| Type | Key Fields |
|------|-----------|
| `UserMessageItem` | `content`, `attachments`, `quoted_text`, `inference_options` |
| `AssistantMessageItem` | `content: list[AssistantMessageContent]`, `thread_id`, `id`, `created_at` |
| `ClientToolCallItem` | `call_id`, `name`, `arguments`, `output`, `status` |
| `WidgetItem` | `widget: WidgetRoot`, `copy_text` |
| `GeneratedImageItem` | `image` object |
| `TaskItem` | `task: Task` |
| `WorkflowItem` | `workflow: Workflow` |
| `EndOfTurnItem` | Marker only |
| `HiddenContextItem` | Integration-defined, not UI-rendered |
| `SDKHiddenContextItem` | SDK-internal context (e.g., cancellation notes) |

---

## Message Content Types

### AssistantMessageContent

```python
AssistantMessageContent(
    type="output_text",
    text: str,
    annotations: list[Annotation],
)
```

### User Message Content

```python
UserMessageTextContent(type="input_text", text=str)
UserMessageTagContent(type="input_tag", id=str, text=str, data=dict, group=str, interactive=bool)
```

### Annotation

```python
Annotation(
    source: URLSource | FileSource | EntitySource,
    index: int,
)
```

### Source Types

| Type | Extra Fields |
|------|-------------|
| `URLSource` | `url`, `attribution` |
| `FileSource` | `filename` |
| `EntitySource` | `id`, `icon`, `label`, `inline_label`, `interactive`, `data` |

All sources share: `title`, `description`, `timestamp`, `group`.

---

## Event Types (discriminated union `ThreadStreamEvent`)

### Persistence Events

| Event | Persists | Purpose |
|-------|----------|---------|
| `ThreadCreatedEvent` | Yes | New thread created |
| `ThreadUpdatedEvent` | Yes | Thread metadata changed |
| `ThreadItemDoneEvent` | Yes | Final item state (triggers storage) |
| `ThreadItemReplacedEvent` | Yes | Swaps item in place |

### Transient Events

| Event | Persists | Purpose |
|-------|----------|---------|
| `ThreadItemAddedEvent` | No | Intermediate state (NOT stored) |
| `ThreadItemUpdatedEvent` | No | Partial update |
| `ThreadItemRemovedEvent` | No | Item removed from stream |
| `StreamOptionsEvent` | No | Stream configuration |
| `ProgressUpdateEvent` | No | Transient progress indicator |
| `ClientEffectEvent` | No | Fire-and-forget client action |
| `ErrorEvent` | No | Error display |
| `NoticeEvent` | No | Notice/warning display |

### ErrorEvent

```python
ErrorEvent(
    code: str | None,
    message: str,
    allow_retry: bool = True,
)
```

### NoticeEvent

```python
NoticeEvent(
    level: str,           # "info", "warning", "error"
    message: str,         # Supports markdown
    title: str | None,
)
```

### ProgressUpdateEvent

```python
ProgressUpdateEvent(
    icon: str | None,     # Icon name (see chatkit.icons)
    text: str,            # Display text
)
```

---

## Attachment Types

```python
FileAttachment(type="file", id=str, name=str, mime_type=str, upload_descriptor=..., thread_id=str)
ImageAttachment(type="image", preview_url=str, ...)

AttachmentUploadDescriptor(url=str, method="POST"|"PUT", headers=dict)
```

---

## Workflow & Task Types

```python
Workflow(type="custom"|"reasoning", tasks=list[Task], summary=..., expanded=bool)

# Task variants (discriminated union):
CustomTask(title=str, status_indicator="none"|"loading"|"complete")
SearchTask(...)
ThoughtTask(...)
FileTask(...)
ImageTask(...)
```

---

## Utility Types

```python
Page[T](data=list[T], has_more=bool, after=str)
InferenceOptions(tool_choice=ToolChoice, model=str)
ToolChoice(id=str)
TranscriptionResult(text=str)
AudioInput(data=bytes, mime_type=str)
FeedbackKind = Literal["positive", "negative"]
StoreItemType = str  # "message", "widget", "thread", etc.
```

---

## Errors Module (`chatkit.errors`)

```python
from chatkit.errors import StreamError, CustomStreamError

# Structured error
raise StreamError(code="rate_limit", status_code=429)

# Custom user-facing error
raise CustomStreamError(message="Service unavailable", allow_retry=True)
```
