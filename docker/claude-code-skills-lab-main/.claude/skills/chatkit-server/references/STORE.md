# Store

Deep reference for the Store interface and implementations in the ChatKit Python SDK.

---

## Store[TContext] (Abstract Base Class)

The Store provides persistence for threads, items, and attachments. You must implement all abstract methods.

### Abstract Methods (12 total)

| Method | Parameters | Returns |
|--------|-----------|---------|
| `load_thread` | `thread_id: str, context` | `ThreadMetadata` |
| `save_thread` | `thread: ThreadMetadata, context` | `None` |
| `load_threads` | `limit: int, after: str \| None, order: str, context` | `Page[ThreadMetadata]` |
| `load_thread_items` | `thread_id: str, after: str \| None, limit: int, order: str, context` | `Page[ThreadItem]` |
| `add_thread_item` | `thread_id: str, item: ThreadItem, context` | `None` |
| `save_item` | `thread_id: str, item: ThreadItem, context` | `None` |
| `load_item` | `thread_id: str, item_id: str, context` | `ThreadItem` |
| `delete_thread` | `thread_id: str, context` | `None` |
| `delete_thread_item` | `thread_id: str, item_id: str, context` | `None` |
| `save_attachment` | `attachment: Attachment, context` | `None` |
| `load_attachment` | `attachment_id: str, context` | `Attachment` |
| `delete_attachment` | `attachment_id: str, context` | `None` |

### ID Generation (Overridable)

```python
# Default implementations use default_generate_id()
def generate_thread_id(self, context: TContext) -> str
def generate_item_id(self, item_type: StoreItemType, thread: ThreadMetadata, context: TContext) -> str
```

### Exception

```python
from chatkit.store import NotFoundError

raise NotFoundError(f"Thread {thread_id} not found")
```

### Pagination

```python
from chatkit.types import Page

# Cursor-based pagination
Page(data=[...], has_more=True, after="cursor_value")
```

---

## In-Memory Store (Development)

```python
from collections import defaultdict
from chatkit.store import Store, NotFoundError
from chatkit.types import Page, ThreadMetadata, ThreadItem, Attachment

class MyChatKitStore(Store[dict]):
    def __init__(self):
        self.threads: dict[str, ThreadMetadata] = {}
        self.items: dict[str, list[ThreadItem]] = defaultdict(list)

    async def load_thread(self, thread_id, context):
        if thread_id not in self.threads:
            raise NotFoundError(f"Thread {thread_id} not found")
        return self.threads[thread_id]

    async def save_thread(self, thread, context):
        self.threads[thread.id] = thread

    async def load_threads(self, limit, after, order, context):
        threads = list(self.threads.values())
        return self._paginate(threads, after, limit, order,
            sort_key=lambda t: t.created_at, cursor_key=lambda t: t.id)

    async def load_thread_items(self, thread_id, after, limit, order, context):
        items = self.items.get(thread_id, [])
        return self._paginate(items, after, limit, order,
            sort_key=lambda i: i.created_at, cursor_key=lambda i: i.id)

    async def add_thread_item(self, thread_id, item, context):
        self.items[thread_id].append(item)

    async def save_item(self, thread_id, item, context):
        items = self.items[thread_id]
        for idx, existing in enumerate(items):
            if existing.id == item.id:
                items[idx] = item
                return
        items.append(item)

    async def load_item(self, thread_id, item_id, context):
        for item in self.items.get(thread_id, []):
            if item.id == item_id:
                return item
        raise NotFoundError(f"Item {item_id} not found")

    async def delete_thread(self, thread_id, context):
        self.threads.pop(thread_id, None)
        self.items.pop(thread_id, None)

    async def delete_thread_item(self, thread_id, item_id, context):
        self.items[thread_id] = [
            i for i in self.items.get(thread_id, []) if i.id != item_id
        ]

    async def save_attachment(self, attachment, context): pass
    async def load_attachment(self, attachment_id, context):
        raise NotFoundError(f"Attachment {attachment_id} not found")
    async def delete_attachment(self, attachment_id, context): pass

    def _paginate(self, rows, after, limit, order, sort_key, cursor_key):
        rows = sorted(rows, key=sort_key, reverse=(order == "desc"))
        if after:
            idx = next((i for i, r in enumerate(rows) if cursor_key(r) == after), -1)
            rows = rows[idx + 1:] if idx >= 0 else rows
        has_more = len(rows) > limit
        return Page(data=rows[:limit], has_more=has_more,
                    after=cursor_key(rows[limit - 1]) if rows[:limit] else "")
```

---

## PostgreSQL Store (Production)

**Key design principle**: Store thread items as JSONB to accommodate schema evolution without migrations.

```python
import psycopg
from psycopg.rows import tuple_row
from chatkit.store import Store, NotFoundError
from chatkit.types import ThreadMetadata, ThreadItem, Page

class PostgresStore(Store[RequestContext]):
    def __init__(self, conninfo: str):
        self._conninfo = conninfo
        self._init_schema()

    def _connection(self):
        return psycopg.connect(self._conninfo)

    def _init_schema(self):
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    data JSONB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_threads_user
                    ON threads(user_id, created_at DESC);
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                    user_id TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    data JSONB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_items_thread
                    ON items(thread_id, created_at ASC);
            """)
            conn.commit()

    async def load_thread(self, thread_id, context):
        with self._connection() as conn, conn.cursor(row_factory=tuple_row) as cur:
            cur.execute(
                "SELECT data FROM threads WHERE id = %s AND user_id = %s",
                (thread_id, context.user_id),
            )
            row = cur.fetchone()
            if row is None:
                raise NotFoundError(f"Thread {thread_id} not found")
            return ThreadMetadata.model_validate(row[0])

    async def save_thread(self, thread, context):
        payload = thread.model_dump(mode="json")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO threads (id, user_id, created_at, data)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data
            """, (thread.id, context.user_id, thread.created_at, payload))
            conn.commit()

    async def add_thread_item(self, thread_id, item, context):
        payload = item.model_dump(mode="json")
        with self._connection() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO items (id, thread_id, user_id, created_at, data)
                VALUES (%s, %s, %s, %s, %s)
            """, (item.id, thread_id, context.user_id, item.created_at, payload))
            conn.commit()

    # ... implement remaining methods following the same pattern
```

---

## AttachmentStore[TContext]

Additional abstract base for file attachment operations:

```python
class AttachmentStore(ABC, Generic[TContext]):
    async def delete_attachment(self, attachment_id: str, context: TContext) -> None: ...
    async def create_attachment(self, input: AttachmentCreateParams, context: TContext) -> Attachment:
        raise NotImplementedError  # Override for upload support
    def generate_attachment_id(self, mime_type: str, context: TContext) -> str: ...
```

---

## Best Practices

- **JSONB storage**: Serialize thread items as JSON blobs so schema changes don't break storage
- **Filter by user_id**: Always include `WHERE user_id = %s` in queries for tenant isolation
- **Tune history limit**: Adjust `limit` in `load_thread_items` based on model context budget
- **Cursor pagination**: Use `after` parameter for efficient pagination of large thread lists
- **Connection pooling**: Use a connection pool (asyncpg, psycopg pool) in production
