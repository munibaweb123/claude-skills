# Kafka Producer Reference

## Java Producer API

### Basic Producer

```java
import org.apache.kafka.clients.producer.*;
import java.util.Properties;

Properties props = new Properties();
props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG,
    "org.apache.kafka.common.serialization.StringSerializer");
props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG,
    "org.apache.kafka.common.serialization.StringSerializer");

KafkaProducer<String, String> producer = new KafkaProducer<>(props);

// Fire and forget
producer.send(new ProducerRecord<>("my-topic", "key", "value"));

// Synchronous
RecordMetadata metadata = producer.send(
    new ProducerRecord<>("my-topic", "key", "value")).get();
System.out.printf("Sent to partition %d, offset %d%n",
    metadata.partition(), metadata.offset());

// Asynchronous with callback
producer.send(new ProducerRecord<>("my-topic", "key", "value"),
    (metadata2, exception) -> {
        if (exception != null) {
            exception.printStackTrace();
        } else {
            System.out.printf("Sent to %s-%d @ %d%n",
                metadata2.topic(), metadata2.partition(), metadata2.offset());
        }
    });

producer.close();
```

### Producer with Headers

```java
ProducerRecord<String, String> record =
    new ProducerRecord<>("my-topic", "key", "value");
record.headers().add("correlation-id", "abc-123".getBytes());
record.headers().add("source", "order-service".getBytes());
producer.send(record);
```

### Idempotent Producer

Prevents duplicate messages caused by retries:

```java
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
// Implied settings:
// acks=all, retries=Integer.MAX_VALUE, max.in.flight.requests.per.connection<=5
```

### Transactional Producer

Exactly-once semantics across multiple partitions/topics:

```java
props.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "order-processor-1");
props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.initTransactions();

try {
    producer.beginTransaction();
    producer.send(new ProducerRecord<>("orders", "key1", "order-data"));
    producer.send(new ProducerRecord<>("audit", "key1", "audit-data"));
    producer.commitTransaction();
} catch (ProducerFencedException | OutOfOrderSequenceException e) {
    producer.close();
} catch (KafkaException e) {
    producer.abortTransaction();
}
```

## Python Producer API

### confluent-kafka

```python
from confluent_kafka import Producer
import json

conf = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'my-producer',
    'acks': 'all',
    'enable.idempotence': True,
    'max.in.flight.requests.per.connection': 5,
    'retries': 10,
    'linger.ms': 5,
    'batch.size': 16384,
}

producer = Producer(conf)

def delivery_callback(err, msg):
    if err:
        print(f'Delivery failed: {err}')
    else:
        print(f'Delivered to {msg.topic()} [{msg.partition()}] @ {msg.offset()}')

# Produce with callback
producer.produce(
    topic='my-topic',
    key='order-123',
    value=json.dumps({'item': 'widget', 'qty': 5}).encode('utf-8'),
    headers={'source': 'api', 'correlation-id': 'abc'},
    callback=delivery_callback
)

# Trigger delivery reports
producer.poll(0)

# Wait for all messages to be delivered
producer.flush()
```

### kafka-python

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    key_serializer=str.encode,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',
    retries=10,
    linger_ms=5,
)

future = producer.send('my-topic', key='order-123', value={'item': 'widget'})
result = future.get(timeout=10)  # Block for synchronous send
print(f"Sent to partition {result.partition}, offset {result.offset}")

producer.flush()
producer.close()
```

## Key Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `acks` | `all` (Kafka 3.0+) | `0`=no wait, `1`=leader only, `all`=all ISR |
| `retries` | 2147483647 | Number of retries on transient failures |
| `retry.backoff.ms` | 100 | Backoff between retries |
| `delivery.timeout.ms` | 120000 | Total time for a message to be delivered (includes retries, batching, network) |
| `batch.size` | 16384 | Max bytes per batch |
| `linger.ms` | 0 | Time to wait for more messages before sending batch |
| `buffer.memory` | 33554432 | Total memory for buffering |
| `max.block.ms` | 60000 | Max time `send()` blocks when buffer is full |
| `max.in.flight.requests.per.connection` | 5 | Max unacknowledged requests per connection |
| `compression.type` | `none` | `none`, `gzip`, `snappy`, `lz4`, `zstd` |
| `enable.idempotence` | true (Kafka 3.0+) | Enable exactly-once per partition |
| `transactional.id` | null | Enables transactions when set |

## Acknowledgment Levels (acks)

### How Each Level Works

```
acks=0 (fire-and-forget):
  Producer ──send──> [network buffer]     ← returns immediately, no broker response
                      message may never arrive

acks=1 (leader-only):
  Producer ──send──> Leader writes to local log ──ack──> Producer
                      ↓
                      Followers replicate AFTER ack
                      ↓
                      Leader crashes before replication → MESSAGE LOST

acks=all (all in-sync replicas):
  Producer ──send──> Leader writes ──> Follower 1 writes ──> Follower 2 writes
                                                                    ↓
                                                              All ISR confirmed
                                                                    ↓
                                                              ack ──> Producer
```

### When to Use Each

| Level | Guarantee | Latency | Data Loss Risk | Use When |
|-------|-----------|---------|----------------|----------|
| `acks=0` | None — fire and forget | Lowest (~0.5ms) | High — no confirmation at all | Metrics, debug logs, clickstream where loss is acceptable |
| `acks=1` | Leader persisted | Low (~2-5ms) | Medium — leader can crash before replication | General workloads where occasional loss is tolerable (user activity, non-critical events) |
| `acks=all` | All ISR replicas persisted | Higher (~5-15ms) | Lowest — data survives any single broker failure | Payments, orders, audit logs, anything where loss is unacceptable |

### The acks=1 Failure Scenario

```
Timeline:
  t=0    Producer sends message to Leader (Broker 1)
  t=2ms  Leader writes to local log, sends ack to producer
  t=3ms  Producer receives ack — considers message "delivered" ✓
  t=4ms  Leader begins replicating to followers...
  t=5ms  Broker 1 crashes ✗
  t=6ms  Broker 2 becomes new leader — it never received the message

  Result: Producer thinks message was delivered, but it's GONE
```

This is why `acks=all` exists. With `acks=all`, the ack at t=3ms would not happen until followers confirm.

## Idempotent Producer — How It Prevents Duplicates

### The Duplicate Problem Without Idempotence

```
  t=0    Producer sends message (sequence=10) to broker
  t=1ms  Broker writes message, sends ack
  t=2ms  Network drops the ack — producer never receives it
  t=3ms  Producer retries (same message, sequence=10)
  t=4ms  Broker writes it AGAIN — now the log has TWO copies

  Partition: [..., msg(seq=10), msg(seq=10)]  ← DUPLICATE
```

### How Idempotence Fixes It

When `enable.idempotence=true`, the broker tracks a **Producer ID (PID)** and **sequence number** per partition:

```
  t=0    Producer sends message (PID=7, sequence=10)
  t=1ms  Broker writes message, records: PID=7 last_seq=10, sends ack
  t=2ms  Network drops the ack
  t=3ms  Producer retries (PID=7, sequence=10)
  t=4ms  Broker sees: PID=7 sequence=10 == last_seq=10 → DUPLICATE, skip write
         Broker sends ack (success) without writing again

  Partition: [..., msg(seq=10)]  ← exactly ONE copy
```

### Idempotence Configuration

```properties
enable.idempotence=true

# Implied constraints (Kafka enforces these):
#   acks=all                                    (must be all)
#   retries >= 1                                (must allow retries)
#   max.in.flight.requests.per.connection <= 5  (broker tracks up to 5 in-flight)
```

Setting `enable.idempotence=true` with `acks=0` or `acks=1` will throw a `ConfigException`. Idempotence requires `acks=all`.

### Idempotence Scope and Limitations

| Scope | Covered | Not Covered |
|-------|---------|-------------|
| **Per-partition deduplication** | Yes — same PID + sequence on same partition | Different partitions (use transactions) |
| **Within a producer session** | Yes — PID is assigned on init | Across restarts (PID changes; use `transactional.id` for cross-session) |
| **Retry deduplication** | Yes — the core use case | Application-level duplicates (e.g., user clicks twice → two different produce calls) |

For cross-partition or cross-session exactly-once, use **transactions** (`transactional.id`).

## End-to-End Reliability Chain

No-message-loss requires correct configuration across **three layers**. Missing any one layer creates a gap:

```
┌─────────────── PRODUCER ───────────────┐
│ acks=all                               │
│ enable.idempotence=true                │
│ retries=2147483647                     │
│ delivery.timeout.ms=300000             │
│ max.in.flight.requests.per.connection=5│
│ flush() at shutdown                    │
└────────────────┬───────────────────────┘
                 ▼
┌─────────────── BROKER / TOPIC ─────────┐
│ replication.factor=3                   │
│ min.insync.replicas=2                  │
│ unclean.leader.election.enable=false   │
└────────────────┬───────────────────────┘
                 ▼
┌─────────────── CONSUMER ───────────────┐
│ enable.auto.commit=false               │
│ isolation.level=read_committed         │
│ Process THEN commit (not the reverse)  │
└────────────────────────────────────────┘
```

### Why Each Setting Is Required

| Setting | Layer | What Happens Without It |
|---------|-------|------------------------|
| `acks=all` | Producer | Leader crashes after ack, before replication → **message lost** |
| `enable.idempotence=true` | Producer | Retry after network timeout → **duplicate message** |
| `retries=2147483647` | Producer | Low count + transient failure → **message dropped** |
| `delivery.timeout.ms=300000` | Producer | Too short → gives up during broker rolling restart → **message dropped** |
| `max.in.flight<=5` | Producer | >5 with idempotence disabled → **reordering on retry** |
| `flush()` at shutdown | Producer | Buffered messages in memory → **silently lost** |
| `replication.factor=3` | Broker | factor=1 + broker dies → **all data on that broker lost** |
| `min.insync.replicas=2` | Broker | ISR shrinks to 1 + that broker dies → **acknowledged messages lost** |
| `unclean.leader.election=false` | Broker | Out-of-sync replica becomes leader → **missing messages become invisible** |
| `enable.auto.commit=false` | Consumer | Commit before processing + crash → **message skipped, never processed** |
| `isolation.level=read_committed` | Consumer | Reads uncommitted transactional messages that get aborted → **processes phantom data** |

### The min.insync.replicas Failure Scenario

This is the most commonly missed setting:

```
Without min.insync.replicas=2:

  1. Broker 1 (leader), Broker 2 (follower), Broker 3 (follower)
  2. Brokers 2 and 3 fall behind → ISR shrinks to [Broker 1 only]
  3. Producer sends with acks=all → Broker 1 acks (it's the only ISR member)
  4. Broker 1 crashes before replicating
  5. Broker 2 becomes leader — never received the message
  6. MESSAGE LOST despite acks=all

With min.insync.replicas=2:

  Step 3 → Broker REJECTS the write with NotEnoughReplicasException
  → Producer retries until ISR recovers
  → No silent data loss (write availability traded for durability)
```

## Performance Tuning

### High Throughput

```properties
linger.ms=20
batch.size=65536
compression.type=lz4
buffer.memory=67108864
acks=all                    # Still reliable
enable.idempotence=true     # Still safe
```

### Low Latency

```properties
linger.ms=0
batch.size=16384
acks=1                      # Trade durability for speed
compression.type=none
```

### Maximum Reliability (No Message Loss)

```properties
acks=all
enable.idempotence=true
retries=2147483647
delivery.timeout.ms=300000
max.in.flight.requests.per.connection=5
linger.ms=5
compression.type=lz4

# Broker/topic config (required alongside producer config):
# replication.factor=3
# min.insync.replicas=2
# unclean.leader.election.enable=false
```

## Synchronous vs Asynchronous Produce

### When to Use Each

| Pattern | How | Throughput | Use When |
|---------|-----|------------|----------|
| **Fire-and-forget** | `produce()` with no callback, no poll | Highest | Loss is acceptable (metrics, debug logs) |
| **Async with callback** | `produce()` + `poll()` + callback | High | Default for most workloads — non-blocking, still confirms delivery |
| **Synchronous** | Block until broker confirms | Lowest | The caller must know the message was persisted before continuing |

### Python (confluent-kafka) — Async with Callback

`confluent-kafka` is fully asynchronous. `produce()` queues the message internally and returns immediately. **Callbacks only fire when you call `poll()` or `flush()`** — this is the most common mistake.

```python
from confluent_kafka import Producer

producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'enable.idempotence': True,
})

def delivery_callback(err, msg):
    if err is not None:
        logger.error("Delivery failed key=%s: %s", msg.key(), err)
    else:
        logger.info("Delivered to %s [%d] @ %d",
                     msg.topic(), msg.partition(), msg.offset())

# Produce — queues internally, returns immediately
producer.produce('task-events', key=b'task-1', value=b'...', callback=delivery_callback)

# CRITICAL: poll() triggers callbacks from previous produce() calls
# Without this, callbacks never fire until flush()
producer.poll(0)

# At shutdown: flush() blocks until all queued messages are delivered (or timeout)
remaining = producer.flush(timeout=10)
if remaining > 0:
    logger.error("%d messages were not delivered", remaining)
```

**`poll()` rules of thumb:**
- Call `producer.poll(0)` after every `produce()` in a loop — non-blocking, fires any ready callbacks
- Call `producer.poll(1.0)` if you need to wait for callbacks (e.g., after a `BufferError`)
- Call `producer.flush(timeout)` at shutdown or when you need all messages confirmed

### Python (confluent-kafka) — Synchronous

confluent-kafka has no native synchronous send. Simulate it with an Event:

```python
import threading

def produce_sync(producer, topic, key, value, timeout=10):
    """Block until message is delivered or fails."""
    result = {}
    event = threading.Event()

    def on_delivery(err, msg):
        result['err'] = err
        result['msg'] = msg
        event.set()

    producer.produce(topic, key=key, value=value, callback=on_delivery)
    producer.poll(0)

    if not event.wait(timeout):
        raise TimeoutError(f"Produce to {topic} timed out after {timeout}s")
    if result['err'] is not None:
        raise Exception(f"Delivery failed: {result['err']}")

    return result['msg']

# Usage
msg = produce_sync(producer, 'task-events', b'task-1', b'{"event": "task.created"}')
print(f"Confirmed at offset {msg.offset()}")
```

### Java — All Three Patterns

```java
// Fire-and-forget
producer.send(new ProducerRecord<>("topic", "key", "value"));

// Asynchronous with callback
producer.send(new ProducerRecord<>("topic", "key", "value"),
    (metadata, exception) -> {
        if (exception != null) {
            logger.error("Delivery failed", exception);
        } else {
            logger.info("Delivered to {} [{}] @ {}",
                metadata.topic(), metadata.partition(), metadata.offset());
        }
    });

// Synchronous — .get() blocks until broker confirms
RecordMetadata metadata = producer.send(
    new ProducerRecord<>("topic", "key", "value")).get(10, TimeUnit.SECONDS);
```

### Python (kafka-python) — Sync and Async

```python
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers='localhost:9092')

# Asynchronous — returns a Future
future = producer.send('task-events', key=b'task-1', value=b'...')

# Add callback
future.add_callback(lambda meta: print(f"Sent to {meta.partition} @ {meta.offset}"))
future.add_errback(lambda exc: print(f"Failed: {exc}"))

# Synchronous — block on the Future
metadata = future.get(timeout=10)
```

## Error Handling

### Retriable vs Non-Retriable Errors

**Retriable** (Kafka retries automatically up to `retries` config):
- `NetworkException` — transient network issues
- `NotLeaderOrFollowerException` — leader changed
- `UnknownTopicOrPartitionException` — metadata not yet propagated

**Non-retriable** (fail immediately, no automatic retry):
- `SerializationException` — bad data
- `RecordTooLargeException` — message exceeds `max.request.size`
- `AuthorizationException` — insufficient permissions
- `ProducerFencedException` — transactional producer fenced

### Python (confluent-kafka) Error Handling

confluent-kafka has two error surfaces: exceptions from `produce()` (synchronous/local errors) and errors delivered via callback (asynchronous/broker errors).

```python
from confluent_kafka import Producer, KafkaException

producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'enable.idempotence': True,
    'queue.buffering.max.messages': 100000,
})

failed_messages = []

def delivery_callback(err, msg):
    """Handle async broker-side delivery results."""
    if err is not None:
        logger.error("Delivery failed key=%s: %s (code=%s)",
                     msg.key(), err, err.code())
        # Collect for retry or dead-letter
        failed_messages.append({
            'topic': msg.topic(),
            'key': msg.key(),
            'value': msg.value(),
            'error': str(err),
        })
    else:
        logger.info("Delivered to %s [%d] @ %d",
                     msg.topic(), msg.partition(), msg.offset())


def send_event(producer, topic, key, value, headers=None):
    """Produce with local error handling."""
    try:
        producer.produce(
            topic=topic,
            key=key,
            value=value,
            headers=headers or {},
            callback=delivery_callback,
        )
        producer.poll(0)  # Trigger ready callbacks
    except BufferError:
        # Internal queue is full — back-pressure
        logger.warning("Producer queue full, draining...")
        producer.poll(1.0)  # Block briefly to drain queue
        # Retry once
        producer.produce(
            topic=topic,
            key=key,
            value=value,
            headers=headers or {},
            callback=delivery_callback,
        )
    except KafkaException as e:
        # Configuration or fatal errors
        logger.error("Kafka error: %s", e)
        raise
    except ValueError as e:
        # Invalid arguments (e.g., key/value type mismatch)
        logger.error("Invalid produce arguments: %s", e)
        raise
```

**Error surface summary:**

| Error | Raised Where | Type | Action |
|-------|-------------|------|--------|
| `BufferError` | `produce()` call | Local queue full | `poll(1.0)` to drain, then retry |
| `KafkaException` | `produce()` call | Config/fatal error | Log and raise |
| `ValueError` | `produce()` call | Bad arguments | Fix caller code |
| `KafkaError` in callback | `delivery_callback(err, msg)` | Broker rejected message | Log, retry, or send to dead-letter topic |

### Java Error Handling

```java
producer.send(new ProducerRecord<>("topic", "key", "value"),
    (metadata, exception) -> {
        if (exception == null) {
            logger.info("Delivered to {} [{}] @ {}",
                metadata.topic(), metadata.partition(), metadata.offset());
            return;
        }
        if (exception instanceof RetriableException) {
            // Already retried up to 'retries' config — now exhausted
            logger.error("Retriable error exhausted: {}", exception.getMessage());
            sendToDeadLetter("topic", "key", "value", exception);
        } else if (exception instanceof RecordTooLargeException) {
            logger.error("Message too large, skipping: {}", exception.getMessage());
        } else if (exception instanceof AuthorizationException) {
            logger.error("Not authorized: {}", exception.getMessage());
            // Fatal — stop producing or alert
        } else {
            logger.error("Unexpected producer error: {}", exception.getMessage());
            sendToDeadLetter("topic", "key", "value", exception);
        }
    });
```

## Event Envelope Pattern

Standardize event structure across all producers for consistent serialization, idempotent consumers, and event routing.

```python
import json
import uuid
import time


def build_event(event_type: str, entity_id: str, data: dict) -> dict:
    """Build a standard event envelope."""
    return {
        "event_id": str(uuid.uuid4()),   # Unique per event — consumers use for deduplication
        "event_type": event_type,          # e.g. "task.created", "task.completed"
        "timestamp": time.time(),          # Producer-side timestamp
        "source": "task-api",              # Producing service name
        "data": data,                      # Business payload
    }


def serialize(event: dict) -> bytes:
    """Serialize event to JSON bytes."""
    return json.dumps(event, default=str).encode("utf-8")


# Usage
event = build_event(
    event_type="task.created",
    entity_id="task-42",
    data={"task_id": "task-42", "title": "Design API", "assignee": "alice"},
)

producer.produce(
    topic="task-events",
    key="task-42".encode("utf-8"),     # Key = entity ID for partition affinity
    value=serialize(event),
    headers={
        "event_type": "task.created",  # Header for routing without deserializing
        "source": "task-api",
    },
    callback=delivery_callback,
)
producer.poll(0)
```

**Why each field matters:**

| Field | Purpose |
|-------|---------|
| `event_id` | Consumer-side idempotency — deduplicate by this ID |
| `event_type` | Consumers filter/route without parsing the full payload |
| `timestamp` | Ordering, debugging, time-based windowing in Kafka Streams |
| `source` | Trace which service produced the event |
| `data` | Business payload — varies per event type |
| Key (Kafka) | Partition affinity — all events for same entity go to same partition |
| Headers (Kafka) | Lightweight metadata for routing, filtering, tracing |
