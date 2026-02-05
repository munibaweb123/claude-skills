# Change Data Capture & Transactional Outbox Reference

## The Dual-Write Problem

When a service needs to update a database AND publish an event, doing both independently creates an inconsistency window:

```
API request → update database → produce to Kafka

Failure scenarios:

1. DB succeeds, Kafka produce fails:
   Database: order = "created"     ✓
   Kafka:    (no event)            ✗
   → Downstream services never learn about the order

2. Kafka produce succeeds, DB fails:
   Database: (no order)            ✗
   Kafka:    order.created event   ✓
   → Downstream services process a phantom order

3. DB succeeds, app crashes before produce:
   Database: order = "created"     ✓
   Kafka:    (no event)            ✗
   → Same as scenario 1, but harder to detect
```

**These are not edge cases.** Under load, network timeouts, broker restarts, and process crashes happen regularly. Any system that writes to two independent stores without coordination will eventually have inconsistent data.

### Why You Can't Fix It With Retries

```python
# WRONG — retry doesn't help
def create_order(data):
    db.execute("INSERT INTO orders ...")   # ← committed
    try:
        producer.produce("order-events", ...) # ← might fail
        producer.flush()
    except Exception:
        # What now? Can't un-commit the database.
        # Retry? What if the app crashes before retry?
        # Log and hope? That's data loss.
        pass
```

Even with retries, there's always a window between the DB commit and the Kafka produce where a crash loses the event permanently.

### Why You Can't Fix It With Kafka Transactions

Kafka transactions only cover Kafka writes. They cannot include a database write:

```python
# WRONG — Kafka transaction doesn't include the DB
producer.begin_transaction()
db.execute("INSERT INTO orders ...")      # NOT part of Kafka transaction
producer.produce("order-events", ...)     # Part of Kafka transaction
producer.commit_transaction()             # Only commits the Kafka side
```

## Solutions

### Solution 1: Transactional Outbox (Recommended)

Write the event to an **outbox table** in the **same database transaction** as the business data. A separate process (CDC or poller) reads the outbox and produces to Kafka.

```
               Single database transaction
              ┌────────────────────────────┐
API request → │ INSERT INTO orders (...)   │
              │ INSERT INTO outbox (...)   │ ← same transaction
              └────────────────────────────┘
                          │
              Outbox relay (Debezium CDC)
                          │
                          ↓
                   Kafka: order.events
```

**Why it works:** The database transaction is atomic. Either both the order and the outbox row exist, or neither does. Debezium reads committed rows from the WAL — no lost events.

### Solution 2: CDC on Business Tables (Listen to Changes)

Skip the outbox entirely. Point Debezium at the business tables and capture every INSERT/UPDATE/DELETE:

```
              ┌─────────────────┐
API request → │ INSERT INTO     │
              │ orders (...)    │ ← just the business write
              └─────────────────┘
                      │
              Debezium reads WAL
              (captures all mutations)
                      │
                      ↓
               Kafka: cdc.public.orders
```

**Trade-off:** Simpler (no outbox table), but CDC events expose the database schema to consumers. Schema changes in the database become breaking changes for consumers.

### Outbox vs Direct CDC

| Aspect | Transactional Outbox | Direct CDC on Business Tables |
|--------|---------------------|-------------------------------|
| **Event format** | You control the event schema — clean domain events | Mirrors the DB schema — column names, types, nullable changes |
| **Schema coupling** | Decoupled — DB schema changes don't affect events | Tight — ALTER TABLE breaks consumers |
| **Event content** | Include only what consumers need | Includes all columns (can filter with SMTs) |
| **Event types** | Explicit: `task.created`, `task.completed` | Implicit: INSERT = created, UPDATE = modified (consumer infers) |
| **Selective publishing** | Only write outbox rows for events you want to publish | Captures ALL mutations — including internal bookkeeping |
| **Additional table** | Yes — outbox table with cleanup needed | No extra table |
| **Complexity** | Medium — outbox DDL, insert logic, cleanup | Low — just point Debezium at the table |
| **Best for** | Event-driven microservices, domain events | Data replication, data lake ingestion, analytics |

**Recommendation:** Use the outbox pattern when events represent business actions consumed by other services. Use direct CDC when replicating data for analytics or warehousing.

## CDC vs Polling

| Aspect | CDC (Debezium) | Polling (JDBC Source) |
|--------|---------------|----------------------|
| **Mechanism** | Reads database WAL (write-ahead log) | Queries table with `WHERE id > last_seen` |
| **Latency** | Near real-time (ms) | Poll interval (seconds to minutes) |
| **Captures deletes** | Yes — DELETE appears in the WAL | No — deleted rows are invisible to queries |
| **Database load** | Minimal — reads WAL stream, no queries | Adds query load on every poll interval |
| **Schema changes** | Captured automatically | Not captured |
| **Requires** | Logical replication enabled (`wal_level=logical`) | Incrementing or timestamp column |
| **Exactly-once** | Source connector supports it | Possible with careful offset management |
| **Operational** | Replication slot, publication, WAL retention | Simple — just SQL queries |
| **Best for** | Production event streaming, outbox pattern | Simple data sync, legacy systems without WAL access |

## Outbox Table Schema (PostgreSQL)

The table follows Debezium's **Outbox Event Router** expected column names:

```sql
CREATE TABLE outbox (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aggregatetype   TEXT NOT NULL,    -- entity type → used for topic routing
    aggregateid     TEXT NOT NULL,    -- entity ID   → becomes Kafka message key
    type            TEXT NOT NULL,    -- event type  → becomes a Kafka header
    payload         JSONB NOT NULL,   -- event data  → becomes Kafka message value
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Column purposes in the Debezium pipeline:**

```
outbox row:
  id:            "abc-123"          → Kafka header: id=abc-123 (deduplication)
  aggregatetype: "task"             → topic routing (task → task.events)
  aggregateid:   "task-456"         → Kafka message key (partition by entity)
  type:          "task.created"     → Kafka header: type=task.created
  payload:       {"task_id": ...}   → Kafka message value
  created_at:    "2025-..."         → Kafka header/timestamp
```

### Outbox Cleanup

Debezium reads from the WAL, not from the table. Old outbox rows serve no purpose and waste disk space.

**Option A: Trigger-based cleanup**

```sql
CREATE OR REPLACE FUNCTION cleanup_old_outbox() RETURNS trigger AS $$
BEGIN
    DELETE FROM outbox WHERE created_at < now() - INTERVAL '3 days';
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_cleanup_outbox
    AFTER INSERT ON outbox
    FOR EACH STATEMENT
    EXECUTE FUNCTION cleanup_old_outbox();
```

**Option B: Scheduled job (pg_cron or application-level)**

```sql
-- pg_cron: run daily at 3 AM
SELECT cron.schedule('cleanup-outbox', '0 3 * * *',
    $$DELETE FROM outbox WHERE created_at < now() - INTERVAL '3 days'$$);
```

**Option C: Table partitioning by time (best for high volume)**

```sql
CREATE TABLE outbox (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    aggregatetype   TEXT NOT NULL,
    aggregateid     TEXT NOT NULL,
    type            TEXT NOT NULL,
    payload         JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
) PARTITION BY RANGE (created_at);

-- Create partitions (daily)
CREATE TABLE outbox_2025_01 PARTITION OF outbox
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

-- Drop old partitions instantly (no row-by-row delete)
DROP TABLE outbox_2024_12;
```

## Transactional Insert Pattern

### Python (asyncpg + FastAPI)

```python
import json, uuid
from datetime import datetime, timezone


def build_outbox_event(aggregate_id: str, event_type: str, data: dict) -> dict:
    """Build an outbox row following Debezium EventRouter conventions."""
    return {
        "id": str(uuid.uuid4()),
        "aggregatetype": event_type.split(".")[0],  # "task.created" → "task"
        "aggregateid": aggregate_id,
        "type": event_type,
        "payload": json.dumps({
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "task-api",
            "data": data,
        }),
    }


async def insert_outbox(conn, event: dict):
    """Insert an outbox row within an existing transaction."""
    await conn.execute("""
        INSERT INTO outbox (id, aggregatetype, aggregateid, type, payload)
        VALUES ($1, $2, $3, $4, $5::jsonb)
    """, event["id"], event["aggregatetype"],
        event["aggregateid"], event["type"], event["payload"])


# --- Usage in a route ---

@app.post("/tasks", status_code=201)
async def create_task(body: TaskCreate):
    task_id = str(uuid.uuid4())

    async with pool.acquire() as conn:
        async with conn.transaction():  # ← single DB transaction
            # 1. Business write
            await conn.execute("""
                INSERT INTO tasks (id, title, assignee, status)
                VALUES ($1, $2, $3, 'pending')
            """, task_id, body.title, body.assignee)

            # 2. Outbox write (same transaction — atomic)
            outbox = build_outbox_event(task_id, "task.created", {
                "task_id": task_id,
                "title": body.title,
                "assignee": body.assignee,
                "status": "pending",
            })
            await insert_outbox(conn, outbox)

    # No Kafka producer here — Debezium handles it
    return {"task_id": task_id, "status": "pending"}


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    async with pool.acquire() as conn:
        async with conn.transaction():
            result = await conn.execute("""
                UPDATE tasks SET status = 'completed', updated_at = now()
                WHERE id = $1 AND status != 'completed'
            """, task_id)

            if result == "UPDATE 0":
                raise HTTPException(404, "Task not found or already completed")

            outbox = build_outbox_event(task_id, "task.completed", {
                "task_id": task_id,
                "status": "completed",
            })
            await insert_outbox(conn, outbox)

    return {"task_id": task_id, "status": "completed"}
```

### Java (Spring + JPA)

```java
@Service
@Transactional  // ← single DB transaction wraps both writes
public class TaskService {

    @Autowired private TaskRepository taskRepo;
    @Autowired private OutboxRepository outboxRepo;

    public Task createTask(String title, String assignee) {
        // 1. Business write
        Task task = new Task(UUID.randomUUID(), title, assignee, "pending");
        taskRepo.save(task);

        // 2. Outbox write (same transaction)
        OutboxEvent event = OutboxEvent.builder()
            .id(UUID.randomUUID())
            .aggregateType("task")
            .aggregateId(task.getId().toString())
            .type("task.created")
            .payload(Map.of(
                "event_id", UUID.randomUUID().toString(),
                "event_type", "task.created",
                "timestamp", Instant.now().toString(),
                "data", Map.of("task_id", task.getId(), "title", title,
                               "assignee", assignee, "status", "pending")
            ))
            .build();
        outboxRepo.save(event);

        return task;
    }
}
```

## PostgreSQL WAL Setup for Debezium

```sql
-- 1. Verify WAL level (must be 'logical')
SHOW wal_level;

-- If not 'logical', set in postgresql.conf:
--   wal_level = logical
--   max_replication_slots = 4
--   max_wal_senders = 4
-- Then restart PostgreSQL.

-- 2. Create a dedicated Debezium user
CREATE ROLE debezium WITH LOGIN PASSWORD 'password' REPLICATION;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
GRANT USAGE ON SCHEMA public TO debezium;

-- 3. Create a publication for the outbox table only
CREATE PUBLICATION outbox_pub FOR TABLE public.outbox;

-- 4. Verify
SELECT * FROM pg_publication;
SELECT * FROM pg_replication_slots;
```

**WAL retention warning:** Debezium creates a replication slot. If Debezium is down for a long time, the WAL accumulates and can fill the disk. Monitor `pg_replication_slots` and set `max_slot_wal_keep_size` (PostgreSQL 13+):

```sql
-- postgresql.conf: limit WAL retention to 10 GB per slot
max_slot_wal_keep_size = '10GB'
```

## Debezium Outbox Event Router

The **Outbox Event Router** is a Debezium SMT that transforms raw CDC events from the outbox table into clean domain events.

### Without EventRouter (Raw CDC Output)

```json
{
  "before": null,
  "after": {
    "id": "abc-123",
    "aggregatetype": "task",
    "aggregateid": "task-456",
    "type": "task.created",
    "payload": "{\"event_id\": \"...\", ...}",
    "created_at": 1706000000000
  },
  "source": { "connector": "postgresql", "db": "taskdb", ... },
  "op": "c",
  "ts_ms": 1706000000000
}
```

Consumers would need to unwrap `after.payload`, parse it as JSON, and ignore the CDC envelope. Not ideal.

### With EventRouter (Clean Domain Event)

```json
{
  "event_id": "evt-789",
  "event_type": "task.created",
  "timestamp": "2025-01-23T10:00:00Z",
  "source": "task-api",
  "data": {
    "task_id": "task-456",
    "title": "Review PR #42",
    "assignee": "alice",
    "status": "pending"
  }
}
```

Topic: `task.events`, Key: `task-456`, Headers: `id=abc-123, type=task.created`

### Connector Configuration (REST API)

```json
{
  "name": "task-outbox-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "password",
    "database.dbname": "taskdb",
    "topic.prefix": "task-cdc",
    "table.include.list": "public.outbox",
    "plugin.name": "pgoutput",
    "slot.name": "task_outbox_slot",
    "publication.name": "outbox_pub",

    "tombstones.on.delete": "false",
    "key.converter": "org.apache.kafka.connect.storage.StringConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter.schemas.enable": false,

    "transforms": "outbox",
    "transforms.outbox.type": "io.debezium.transforms.outbox.EventRouter",
    "transforms.outbox.table.field.event.id": "id",
    "transforms.outbox.table.field.event.key": "aggregateid",
    "transforms.outbox.table.field.event.type": "type",
    "transforms.outbox.table.field.event.payload": "payload",
    "transforms.outbox.table.field.event.timestamp": "created_at",
    "transforms.outbox.route.topic.replacement": "task.events",
    "transforms.outbox.table.expand.json.payload": true,

    "errors.tolerance": "all",
    "errors.deadletterqueue.topic.name": "task-outbox-dlq",
    "errors.deadletterqueue.topic.replication.factor": "3",
    "errors.deadletterqueue.context.headers.enable": true
  }
}
```

### EventRouter Configuration Reference

| Config | Default | Purpose |
|--------|---------|---------|
| `table.field.event.id` | `id` | Column used as event ID (dedup key in Kafka header) |
| `table.field.event.key` | `aggregateid` | Column used as Kafka message key |
| `table.field.event.type` | `type` | Column used as event type (Kafka header) |
| `table.field.event.payload` | `payload` | Column used as Kafka message value |
| `table.field.event.timestamp` | — | Column used as Kafka record timestamp |
| `route.topic.replacement` | `outbox.event.{aggregatetype}` | Target topic name. Use `${routedByValue}` for dynamic routing by aggregatetype |
| `table.expand.json.payload` | `false` | If `true`, parse payload string as JSON in the Kafka value |

### Dynamic Topic Routing

Route different aggregate types to different topics:

```json
"transforms.outbox.route.topic.replacement": "outbox.event.${routedByValue}"
```

With this config:
- `aggregatetype = "task"` → topic `outbox.event.task`
- `aggregatetype = "order"` → topic `outbox.event.order`
- `aggregatetype = "user"` → topic `outbox.event.user`

### Strimzi KafkaConnector CRD

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: task-outbox-connector
  namespace: kafka
  labels:
    strimzi.io/cluster: my-connect
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: postgres.default.svc
    database.port: 5432
    database.user: debezium
    database.password: ${secrets:kafka/postgres-credentials:password}
    database.dbname: taskdb
    topic.prefix: task-cdc
    table.include.list: public.outbox
    plugin.name: pgoutput
    slot.name: task_outbox_slot
    publication.name: outbox_pub
    tombstones.on.delete: false
    key.converter: org.apache.kafka.connect.storage.StringConverter
    value.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter.schemas.enable: false
    transforms: outbox
    transforms.outbox.type: io.debezium.transforms.outbox.EventRouter
    transforms.outbox.table.field.event.id: id
    transforms.outbox.table.field.event.key: aggregateid
    transforms.outbox.table.field.event.type: type
    transforms.outbox.table.field.event.payload: payload
    transforms.outbox.route.topic.replacement: task.events
    transforms.outbox.table.expand.json.payload: true
    errors.tolerance: all
    errors.deadletterqueue.topic.name: task-outbox-dlq
    errors.deadletterqueue.topic.replication.factor: 3
```

## Failure Modes and Recovery

| Failure | What Happens | Result |
|---------|-------------|--------|
| **App crash before DB commit** | Transaction rolls back — no business data, no outbox row | Clean — client retries the API call |
| **App crash after DB commit** | Both business data and outbox row committed | Debezium picks up from WAL — event delivered |
| **Debezium crash** | Restarts, resumes from last WAL position (replication slot retains) | At-least-once delivery — consumers must be idempotent |
| **Kafka unavailable** | Debezium retries until Kafka recovers | Events delayed but not lost (WAL retains data) |
| **PostgreSQL restart** | Replication slot persists across restarts | Debezium reconnects and resumes |
| **Replication slot deleted** | Debezium loses its position in the WAL | Must perform a new snapshot — may produce duplicates |

### End-to-End Guarantee

```
DB transaction (atomic) → WAL → Debezium (at-least-once) → Kafka → Consumer (idempotent)

Guarantee chain:
  DB:        Exactly-once (transaction)
  WAL→Kafka: At-least-once (Debezium may replay on crash)
  Consumer:  Effectively exactly-once (with dedup table or upsert)
```

The outbox pattern provides **effectively exactly-once** end-to-end when consumers are idempotent. The `event_id` in the payload (or the outbox `id` in the Kafka header) serves as the deduplication key.
