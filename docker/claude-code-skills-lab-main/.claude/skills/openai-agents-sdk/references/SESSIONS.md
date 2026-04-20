# Sessions

Deep reference for session persistence and conversation state in the OpenAI Agents SDK.

---

## Overview

Sessions automatically maintain conversation history across multiple agent runs, eliminating manual `.to_input_list()` management. The SDK stores client-side memory.

**Cannot combine** sessions with `conversation_id`, `previous_response_id`, or `auto_previous_response_id`.

---

## Quick Start

```python
from agents import Agent, Runner, SQLiteSession

agent = Agent(name="Assistant", instructions="Reply very concisely.")
session = SQLiteSession("conversation_123")

result = await Runner.run(agent, "What city is the Golden Gate Bridge in?", session=session)
print(result.final_output)  # "San Francisco"

result = await Runner.run(agent, "What state is it in?", session=session)
print(result.final_output)  # "California" - remembers previous context
```

---

## Session Behavior

1. **Before each run:** Runner retrieves conversation history and prepends to input
2. **After each run:** All generated items automatically stored in session
3. **Context preservation:** Subsequent runs include full conversation history

---

## Available Session Backends

| Type | Best For | Install |
|------|----------|---------|
| `SQLiteSession` | Local dev, prototyping | Built-in |
| `AsyncSQLiteSession` | Async SQLite | `pip install aiosqlite` |
| `RedisSession` | Shared memory, distributed | `pip install openai-agents[redis]` |
| `SQLAlchemySession` | Production databases | `pip install sqlalchemy asyncpg` |
| `DaprSession` | Cloud-native microservices | `pip install openai-agents[dapr]` |
| `OpenAIConversationsSession` | Server-managed state | Built-in |
| `OpenAIResponsesCompactionSession` | Long conversations | Built-in |
| `AdvancedSQLiteSession` | Branching, analytics | Built-in |
| `EncryptedSession` | Encryption wrapper | Built-in |

---

## SQLiteSession

```python
from agents import SQLiteSession

# In-memory (data lost on exit)
session = SQLiteSession("user_123")

# File-backed (persistent)
session = SQLiteSession("user_123", "conversations.db")
```

---

## AsyncSQLiteSession

```python
from agents.extensions.memory import AsyncSQLiteSession

session = AsyncSQLiteSession("user_123", db_path="conversations.db")
result = await Runner.run(agent, "Hello", session=session)
```

---

## RedisSession

```python
from agents.extensions.memory import RedisSession

session = RedisSession.from_url("user_123", url="redis://localhost:6379/0")
result = await Runner.run(agent, "Hello", session=session)
```

---

## SQLAlchemySession

```python
from agents.extensions.memory import SQLAlchemySession

# From URL
session = SQLAlchemySession.from_url(
    "user_123",
    url="postgresql+asyncpg://user:pass@localhost/db",
    create_tables=True,
)

# From engine
from sqlalchemy.ext.asyncio import create_async_engine
engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
session = SQLAlchemySession("user_123", engine=engine, create_tables=True)
```

---

## DaprSession

```python
from agents.extensions.memory import DaprSession

async with DaprSession.from_address(
    "user_123",
    state_store_name="statestore",
    dapr_address="localhost:50001",
) as session:
    result = await Runner.run(agent, "Hello", session=session)
```

Options: `ttl=...` for automatic expiration, `consistency=DAPR_CONSISTENCY_STRONG` for stronger guarantees.

---

## OpenAIConversationsSession

Server-managed conversation state:

```python
from agents import OpenAIConversationsSession

# New conversation
session = OpenAIConversationsSession()

# Resume existing
session = OpenAIConversationsSession(conversation_id="conv_123")
```

---

## OpenAIResponsesCompactionSession

Auto-compaction for long conversations:

```python
from agents.memory import OpenAIResponsesCompactionSession

underlying = SQLiteSession("conversation_123")
session = OpenAIResponsesCompactionSession(
    session_id="conversation_123",
    underlying_session=underlying,
)
```

Compaction modes: `"auto"` (default), `"previous_response_id"`, `"input"`.

**For low-latency streaming**, disable auto-compaction:

```python
session = OpenAIResponsesCompactionSession(
    session_id="conversation_123",
    underlying_session=underlying,
    should_trigger_compaction=lambda _: False,
)
result = await Runner.run(agent, "Hello", session=session)
await session.run_compaction({"force": True})  # Compact manually after
```

---

## AdvancedSQLiteSession

Adds branching and usage analytics:

```python
from agents.extensions.memory import AdvancedSQLiteSession

session = AdvancedSQLiteSession(
    session_id="user_123",
    db_path="conversations.db",
    create_tables=True,
)

result = await Runner.run(agent, "Hello", session=session)
await session.store_run_usage(result)
await session.create_branch_from_turn(2)
```

---

## EncryptedSession

Wraps any session backend with encryption:

```python
from agents.extensions.memory import EncryptedSession, SQLAlchemySession

underlying = SQLAlchemySession.from_url(
    "user_123",
    url="sqlite+aiosqlite:///conversations.db",
    create_tables=True,
)

session = EncryptedSession(
    session_id="user_123",
    underlying_session=underlying,
    encryption_key="your-secret-key",
    ttl=600,  # 10 minutes
)
```

---

## Session Operations

```python
session = SQLiteSession("user_123", "conversations.db")

# Get all items
items = await session.get_items()

# Add items manually
await session.add_items([
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"},
])

# Remove last item (for corrections)
last_item = await session.pop_item()

# Clear entire session
await session.clear_session()
```

### Pop for Corrections

```python
result = await Runner.run(agent, "What's 2 + 2?", session=session)
await session.pop_item()   # Remove assistant response
await session.pop_item()   # Remove user question
result = await Runner.run(agent, "What's 2 + 3?", session=session)
```

---

## Limiting History

```python
from agents import RunConfig, SessionSettings

result = await Runner.run(
    agent,
    "Summarize our recent discussion.",
    session=session,
    run_config=RunConfig(session_settings=SessionSettings(limit=50)),
)
```

---

## Custom Session Input Callback

```python
from agents import RunConfig

def keep_recent_history(history, new_input):
    return history[-10:] + new_input

result = await Runner.run(
    agent,
    "Continue from latest.",
    session=session,
    run_config=RunConfig(session_input_callback=keep_recent_history),
)
```

---

## Custom Session Implementation

```python
from agents.memory.session import SessionABC
from typing import List

class MyCustomSession(SessionABC):
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._items = []

    async def get_items(self, limit=None):
        items = self._items[-limit:] if limit else self._items
        return items

    async def add_items(self, items):
        self._items.extend(items)

    async def pop_item(self):
        return self._items.pop() if self._items else None

    async def clear_session(self):
        self._items.clear()
```

---

## Session Sharing

```python
# Different users, same database
session_1 = SQLiteSession("user_123", "conversations.db")
session_2 = SQLiteSession("user_456", "conversations.db")

# Shared session across agents
support_agent = Agent(name="Support")
billing_agent = Agent(name="Billing")
session = SQLiteSession("user_123")

result = await Runner.run(support_agent, "Help me", session=session)
result = await Runner.run(billing_agent, "My charges?", session=session)
# billing_agent sees full history including support conversation
```

---

## Warnings

- **Cannot combine** sessions with `conversation_id`, `previous_response_id`, or `auto_previous_response_id`
- Auto-compaction **blocks streaming** - disable for low-latency and compact manually
- Do **not** wrap `OpenAIConversationsSession` with `OpenAIResponsesCompactionSession`
