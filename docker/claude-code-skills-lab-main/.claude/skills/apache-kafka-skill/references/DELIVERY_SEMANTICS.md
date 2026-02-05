# Delivery Semantics Reference

## The Three Guarantees

Every message in a distributed system can be delivered **at most once**, **at least once**, or **effectively exactly once**. Kafka supports all three — the guarantee you get depends on how you configure producers, brokers, and consumers together.

```
                Producer                  Broker                  Consumer
              ┌──────────┐            ┌──────────┐            ┌──────────┐
at-most-once  │ acks=0   │            │          │            │ commit   │
              │ fire and │───────────→│          │───────────→│ BEFORE   │
              │ forget   │            │          │            │ process  │
              └──────────┘            └──────────┘            └──────────┘
              Message may be lost              Message may be lost

              ┌──────────┐            ┌──────────┐            ┌──────────┐
at-least-once │ acks=all │            │ ISR      │            │ process  │
              │ retries  │───────────→│ replicate│───────────→│ THEN     │
              │ enabled  │            │          │            │ commit   │
              └──────────┘            └──────────┘            └──────────┘
              Retry may produce           OK              Crash before commit
              duplicate                                   = reprocessing

              ┌──────────┐            ┌──────────┐            ┌──────────┐
exactly-once  │ idempotent│           │ dedup by │            │ idempotent│
              │ + txn    │───────────→│ PID+seq  │───────────→│ consumer │
              │          │            │          │            │ (app-side)│
              └──────────┘            └──────────┘            └──────────┘
              No broker-side              OK              App deduplicates
              duplicates                                  or uses transactions
```

## At-Most-Once

**Definition:** Each message is delivered zero or one times. Messages can be lost but are never duplicated.

**When to use:** Non-critical, high-volume data where occasional loss is acceptable — metrics, clickstream, debug logs.

### How It Happens

**Producer side:**

```python
# acks=0: fire and forget — producer doesn't wait for broker acknowledgment
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': '0',
})
producer.produce('metrics', value=b'cpu=42%')
# If the broker is down or the network drops, this message is silently lost
```

**Consumer side:**

```python
# Auto-commit (default: every 5 seconds) commits offsets BEFORE processing finishes
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'metrics-ingest',
    'enable.auto.commit': True,     # default
    'auto.commit.interval.ms': 5000,  # default
})

# Timeline:
# t=0s   poll() returns messages [offset 100-109]
# t=3s   auto-commit fires → commits offset 110
# t=4s   consumer CRASHES while processing offset 105
# t=5s   consumer restarts → resumes at offset 110
#         → offsets 105-109 are LOST (never processed)
```

### At-Most-Once Configuration

| Layer | Setting | Effect |
|-------|---------|--------|
| Producer | `acks=0` | Don't wait for broker confirmation |
| Consumer | `enable.auto.commit=true` | Commit before processing finishes |

**Trade-off:** Maximum throughput, minimum latency, but data loss on failure.

## At-Least-Once

**Definition:** Every message is delivered one or more times. No messages are lost, but duplicates are possible.

**When to use:** Most production workloads — orders, payments, audit logs, notifications. This is the **default and recommended starting point**.

### How It Happens

**Producer side:**

```
Producer sends message → broker writes → ACK lost in network
Producer retries (no ACK received) → broker writes AGAIN → duplicate

  Producer              Broker
     │── send(msg) ──→  │ writes msg (offset 42)
     │                   │── ACK ──╳ (network drop)
     │                   │
     │── retry(msg) ──→  │ writes msg AGAIN (offset 43)  ← DUPLICATE
     │← ACK ────────────│
```

With `enable.idempotence=true`, the broker deduplicates using PID+sequence (see PRODUCER.md). This eliminates producer-side duplicates but does NOT solve consumer-side duplicates.

**Consumer side:**

```
Consumer processes message → commits offset → CRASH before commit completes
Consumer restarts → resumes from last committed offset → reprocesses message

  Consumer              Broker
     │← poll() ─────── │ returns offset 100
     │ process(100) ✓   │
     │── commitSync() → │── writing offset...
     │   CRASH ☠        │   commit may or may not persist
     │                   │
     │ restart           │
     │← poll() ─────── │ returns offset 100 AGAIN  ← REPROCESSED
```

### At-Least-Once Configuration

| Layer | Setting | Why |
|-------|---------|-----|
| Producer | `acks=all` | Broker confirms all ISR replicas wrote it |
| Producer | `enable.idempotence=true` | Prevents broker-side duplicates from retries |
| Producer | `retries=2147483647` (default) | Keep retrying on transient failures |
| Broker | `min.insync.replicas=2` | At least 2 replicas must confirm |
| Consumer | `enable.auto.commit=false` | You control when offsets are committed |
| Consumer | `commitSync()` after processing | Ensures process-then-commit order |

### Making At-Least-Once Safe: Idempotent Consumers

At-least-once means duplicates will arrive. The consumer must handle them. Two strategies:

#### Strategy 1: Natural Idempotency (Upsert/PUT Semantics)

If the consumer writes to a database using the entity's natural key, duplicates overwrite the same row:

```python
def handle_task_event(msg):
    event = json.loads(msg.value())
    task_id = event["data"]["task_id"]

    # UPSERT — processing the same event twice produces the same result
    db.execute("""
        INSERT INTO tasks (id, title, status, updated_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            status = EXCLUDED.status,
            updated_at = EXCLUDED.updated_at
    """, (task_id, event["data"]["title"], event["data"]["status"],
          event["timestamp"]))
```

Works when:
- The operation is a PUT (full replacement), not a PATCH (increment)
- The consumer writes to a store that supports upsert (SQL, Redis, Elasticsearch)

Does NOT work when:
- The operation has side effects (sending email, charging a credit card)
- The operation is an increment (`UPDATE ... SET count = count + 1`)

#### Strategy 2: Deduplication Table (Event ID Tracking)

Track processed event IDs and skip duplicates:

```python
def handle_task_event(msg):
    event = json.loads(msg.value())
    event_id = event["event_id"]

    # Check if already processed — use the event_id from the event envelope
    if db.execute("SELECT 1 FROM processed_events WHERE event_id = %s",
                  (event_id,)).fetchone():
        print(f"Skipping duplicate: {event_id}")
        return

    # Process + record in a SINGLE transaction
    with db.begin():
        send_notification(event["data"])
        db.execute(
            "INSERT INTO processed_events (event_id, processed_at) VALUES (%s, NOW())",
            (event_id,),
        )
```

**Critical:** The business logic and the dedup insert must be in the **same transaction**. Otherwise a crash between them creates either a missed event or a duplicate.

#### Strategy 3: Conditional Writes (Optimistic Concurrency)

Use a version or offset as a guard:

```python
def handle_task_event(msg):
    event = json.loads(msg.value())
    task_id = event["data"]["task_id"]

    # Only update if our version is newer
    result = db.execute("""
        UPDATE tasks SET status = %s, version = %s
        WHERE id = %s AND version < %s
    """, (event["data"]["status"], msg.offset(), task_id, msg.offset()))

    if result.rowcount == 0:
        print(f"Skipping: already at version >= {msg.offset()}")
```

### Which Idempotency Strategy to Use

| Strategy | Works For | Fails For | Complexity |
|----------|-----------|-----------|------------|
| **Upsert (PUT)** | DB writes, cache updates, search index updates | Side effects (email, payments), increments | Low |
| **Dedup table** | Any operation including side effects | Requires transactional DB | Medium |
| **Conditional write** | Ordered updates where offset = version | Multi-step workflows | Medium |
| **Kafka transactions** | Consume-transform-produce within Kafka | Side effects outside Kafka | High |

## Exactly-Once Semantics (EOS)

**Definition:** Each message is processed exactly once — no loss, no duplicates, even across failures.

**Reality check:** True exactly-once across arbitrary distributed systems is impossible (FLP impossibility). What Kafka provides is **effectively exactly-once** within specific boundaries.

### Where Exactly-Once Actually Works

| Scope | Mechanism | Guarantee |
|-------|-----------|-----------|
| **Producer → Broker** | Idempotent producer (`enable.idempotence=true`) | No duplicates from retries within a single producer session |
| **Producer → Broker (cross-partition)** | Transactions (`transactional.id`) | Atomic writes across multiple partitions/topics |
| **Kafka Streams (consume-transform-produce)** | `processing.guarantee=exactly_once_v2` | Atomic read + process + write + offset commit |
| **Consumer → External system** | NOT provided by Kafka | You must implement idempotent consumers (see above) |

### Exactly-Once: Producer Transactions

Transactions allow atomic writes across multiple partitions and topics. Either all messages are committed or none are visible to consumers.

```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("enable.idempotence", true);
props.put("transactional.id", "task-processor-1");  // Must be stable across restarts
props.put("acks", "all");

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.initTransactions();

try {
    producer.beginTransaction();

    // Write to multiple topics atomically
    producer.send(new ProducerRecord<>("task-events", taskId, taskEvent));
    producer.send(new ProducerRecord<>("audit-log", taskId, auditEntry));
    producer.send(new ProducerRecord<>("notifications", userId, notification));

    producer.commitTransaction();
} catch (ProducerFencedException e) {
    // Another producer with the same transactional.id took over — shut down
    producer.close();
} catch (KafkaException e) {
    producer.abortTransaction();
}
```

```python
from confluent_kafka import Producer

producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,
    'transactional.id': 'task-processor-1',
    'acks': 'all',
})
producer.init_transactions()

try:
    producer.begin_transaction()
    producer.produce('task-events', key=task_id, value=task_event)
    producer.produce('audit-log', key=task_id, value=audit_entry)
    producer.commit_transaction()
except Exception:
    producer.abort_transaction()
```

**Key rules for `transactional.id`:**
- Must be **stable** across restarts (e.g., based on the service instance ID)
- Must be **unique** per producer instance — two producers with the same ID will fence each other
- Enables **zombie fencing**: if a producer crashes and restarts, the new instance fences the old one so it can't commit stale transactions

### Exactly-Once: Consume-Transform-Produce

The most common exactly-once pattern: read from one topic, process, write to another topic, and commit the consumer offset — all atomically.

```java
// Atomic: consume from input-topic, process, produce to output-topic, commit offset
KafkaProducer<String, String> producer = new KafkaProducer<>(producerProps);
KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);
producer.initTransactions();
consumer.subscribe(List.of("input-topic"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));

    producer.beginTransaction();
    try {
        for (ConsumerRecord<String, String> record : records) {
            // Transform
            String result = process(record.value());

            // Produce to output topic
            producer.send(new ProducerRecord<>("output-topic", record.key(), result));
        }

        // Commit consumer offsets as part of the transaction
        producer.sendOffsetsToTransaction(
            currentOffsets(records),
            consumer.groupMetadata()
        );

        producer.commitTransaction();
    } catch (ProducerFencedException e) {
        producer.close();
        break;
    } catch (KafkaException e) {
        producer.abortTransaction();
        // On abort: offsets not committed → consumer re-polls same messages
    }
}
```

**How it works atomically:**
1. `beginTransaction()` — start transaction
2. `send()` — buffer output messages (not yet visible to consumers)
3. `sendOffsetsToTransaction()` — include consumer offset commit in the transaction
4. `commitTransaction()` — atomically: write output messages + commit input offsets
5. If any step fails → `abortTransaction()` — nothing is committed, consumer re-reads

### Exactly-Once: Kafka Streams

Kafka Streams has built-in exactly-once with a single config change:

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "task-stream-processor");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");
// That's it. Streams handles transactions, offset commits, and state stores atomically.

StreamsBuilder builder = new StreamsBuilder();
builder.<String, String>stream("task-events")
    .filter((key, value) -> value.contains("CREATED"))
    .mapValues(value -> transform(value))
    .to("task-notifications");

KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();
```

`exactly_once_v2` (Kafka 3.0+) wraps the consume → process → state-store-update → produce → offset-commit in a single transaction per task. It replaces the older `exactly_once` (now called `exactly_once_beta`) which used one transaction per partition and was slower.

### Exactly-Once: Consumer to External System (The Hard Part)

Kafka transactions only cover Kafka-to-Kafka flows. When the consumer writes to an **external system** (database, API, file), Kafka cannot guarantee exactly-once. You must make the consumer idempotent.

```
┌─────────────────────────────────────────────────────────────┐
│                 Kafka's exactly-once boundary                │
│                                                             │
│  [input topic] → Consumer → Producer → [output topic]      │
│       ↑                                       │             │
│       └── offset commit (part of transaction) ┘             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │
         │  Outside Kafka's boundary:
         ↓
  Consumer → Database    ← You must make this idempotent
  Consumer → HTTP API    ← You must make this idempotent
  Consumer → Email       ← You must make this idempotent
```

**Pattern: Transactional outbox with dedup**

```python
def handle(msg):
    event = json.loads(msg.value())
    event_id = event["event_id"]

    with db.begin():  # Single database transaction
        # 1. Check dedup
        if db.execute("SELECT 1 FROM processed WHERE id = %s", (event_id,)).fetchone():
            return  # Already processed

        # 2. Business logic
        db.execute("UPDATE tasks SET status = %s WHERE id = %s",
                   (event["data"]["status"], event["data"]["task_id"]))

        # 3. Record processing
        db.execute("INSERT INTO processed (id, processed_at) VALUES (%s, NOW())",
                   (event_id,))

    # 4. Commit Kafka offset AFTER db transaction succeeds
    consumer.commit(asynchronous=False)
```

**Failure modes and outcomes:**

| Failure Point | What Happens | Result |
|---------------|-------------|--------|
| Crash before DB commit | DB rolls back, offset not committed | Consumer re-reads → retry ✓ |
| Crash after DB commit, before Kafka commit | DB committed, offset not committed | Consumer re-reads → dedup table catches it ✓ |
| Crash after both commits | Everything committed | Clean ✓ |

## When to Use Which Guarantee

| Guarantee | Throughput | Latency | Data Safety | Use When |
|-----------|-----------|---------|-------------|----------|
| **At-most-once** | Highest | Lowest | Messages can be lost | Metrics, logs, clickstream where gaps are acceptable |
| **At-least-once** | High | Low | No loss, possible duplicates | **Default for most workloads.** Orders, events, notifications + idempotent consumer |
| **Exactly-once (Kafka-to-Kafka)** | Moderate | Higher | No loss, no duplicates | Stream processing, consume-transform-produce pipelines |
| **Exactly-once (to external)** | Lower | Higher | No loss, no duplicates (app-managed) | Payments, financial records, anything where duplicates have real cost |

### Decision Flowchart

```
Can you tolerate lost messages?
  │
  ├─ YES → At-most-once (acks=0, auto-commit)
  │
  └─ NO → Can your consumer handle duplicates naturally?
           │
           ├─ YES (upsert/PUT) → At-least-once (acks=all, manual commit)
           │                      No extra work needed
           │
           └─ NO → Is the output another Kafka topic?
                    │
                    ├─ YES → Kafka transactions or Kafka Streams exactly_once_v2
                    │
                    └─ NO (database, API, email) →
                         At-least-once + idempotent consumer
                         (dedup table or conditional writes)
```

### Cost of Exactly-Once

| Cost | Impact |
|------|--------|
| **Throughput** | Transactions add ~3-10% overhead (two-phase commit to broker) |
| **Latency** | Transaction commit adds a round-trip (~5-20ms) |
| **Complexity** | `transactional.id` management, fencing, abort handling |
| **Consumer isolation** | Consumers must use `isolation.level=read_committed` to avoid reading uncommitted messages |
| **Operational** | Transaction coordinator on brokers, transaction log topic, timeout tuning |

**Recommendation:** Start with **at-least-once + idempotent consumers**. This handles 95% of use cases with lower complexity. Reserve Kafka transactions for Kafka-to-Kafka stream processing where Kafka Streams' `exactly_once_v2` handles it automatically.

## Consumer `isolation.level`

When producers use transactions, consumers must choose what to read:

| Setting | Behavior | Use When |
|---------|----------|----------|
| `read_uncommitted` (default) | See all messages including uncommitted transactions | No transactions in use, maximum throughput |
| `read_committed` | Only see committed transaction messages | Consuming from topics written by transactional producers |

```python
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'task-processor',
    'isolation.level': 'read_committed',  # Required with transactional producers
})
```

Without `read_committed`, the consumer may process messages from a transaction that is later aborted — leading to phantom reads.

## Kafka Transactions vs Database Transactions

Kafka transactions look similar to database transactions (`begin` → operations → `commit`/`abort`) but have fundamentally different scope and guarantees.

### Key Differences

| Aspect | Database Transaction | Kafka Transaction |
|--------|---------------------|-------------------|
| **Scope** | Arbitrary reads + writes to any table | Writes to Kafka topics + consumer offset commits |
| **Reads** | Transactional (snapshot isolation, serializable) | No transactional reads — `read_committed` only filters aborted messages |
| **Isolation levels** | READ COMMITTED, REPEATABLE READ, SERIALIZABLE | Only `read_committed` vs `read_uncommitted` |
| **Rollback** | Undoes all writes — rows never visible | Marks messages as aborted — they still exist in the log, just skipped by `read_committed` consumers |
| **Locks** | Row/table locks prevent concurrent writes | No locks — multiple producers write concurrently; transactions only gate visibility |
| **Durability** | Write-ahead log, fsync | Replicated across ISR brokers |
| **Participants** | Tables within one database (or XA for distributed) | Kafka topics and partitions only — no external systems |
| **Abort cost** | Undo log replay | Cheap — write abort marker to transaction log |
| **Timeout** | Configurable per query/transaction | `transaction.timeout.ms` (default 60s, max 15min) |

### What Kafka Transactions Actually Do

```
Database transaction:
  BEGIN
  UPDATE accounts SET balance = balance - 100 WHERE id = 1;  ← read + write
  UPDATE accounts SET balance = balance + 100 WHERE id = 2;  ← read + write
  COMMIT  ← both updates visible atomically, or neither

Kafka transaction:
  beginTransaction()
  produce("transfers", key="txn-1", value=debit)    ← write only
  produce("audit-log", key="txn-1", value=entry)    ← write only
  sendOffsetsToTransaction(offsets, groupMetadata)   ← offset commit
  commitTransaction()  ← all messages visible atomically, or none
```

A Kafka transaction guarantees:
1. **Atomic visibility** — consumers see all messages in the transaction, or none
2. **Atomic offset commit** — consumer offsets are committed as part of the transaction
3. **No cross-system guarantee** — if you write to a database AND Kafka in the same "transaction", only the Kafka part is atomic

### Common Mistake: Mixing Kafka and DB Transactions

```python
# WRONG — this is NOT atomic across both systems
producer.begin_transaction()
db.execute("INSERT INTO orders ...")   # DB write — NOT part of Kafka transaction
producer.produce("order-events", ...)  # Kafka write — part of Kafka transaction
producer.commit_transaction()          # Only commits the Kafka side
# If DB committed but Kafka aborts → inconsistency
# If Kafka committed but DB rolled back → inconsistency
```

**Solution: Outbox pattern** — write to the database only, then a separate process reads the outbox table and produces to Kafka:

```
                   Single DB transaction
                  ┌──────────────────────┐
API request ────→ │ INSERT INTO orders   │
                  │ INSERT INTO outbox   │ ← same DB transaction
                  └──────────────────────┘
                           │
               Outbox relay (CDC or poller)
                           │
                           ↓
                    Kafka topic: order-events
```

```python
# CORRECT — single DB transaction, Kafka produced separately
with db.begin():
    db.execute("INSERT INTO orders (id, ...) VALUES (%s, ...)", (order_id,))
    db.execute("""
        INSERT INTO outbox (aggregate_id, event_type, payload)
        VALUES (%s, %s, %s)
    """, (order_id, "order.created", json.dumps(event)))

# Separate process (Debezium CDC or a poller) reads outbox → produces to Kafka
```

### Outbox Pattern: Relay Options

| Relay Method | How It Works | Trade-off |
|-------------|-------------|-----------|
| **Debezium CDC** | Captures INSERT on outbox table via database WAL, produces to Kafka automatically | Near real-time, no polling, but requires Kafka Connect + Debezium |
| **Polling relay** | Background job queries outbox table periodically, produces to Kafka, marks rows as sent | Simple to implement, but adds latency (poll interval) and requires idempotent consumers |
| **Application relay** | After DB commit, application produces to Kafka in the same process | Simplest, but if the app crashes after DB commit and before produce → message lost until retry |

## Transaction Internals

### How Kafka Transactions Work Under the Hood

```
Producer                  Transaction         Partition        Consumer
                         Coordinator          Leaders          (read_committed)
   │                         │                   │                  │
   │── initTransactions() ──→│                   │                  │
   │   (registers PID +      │                   │                  │
   │    transactional.id)     │                   │                  │
   │                         │                   │                  │
   │── beginTransaction() ──→│                   │                  │
   │                         │ write BEGIN        │                  │
   │                         │ to txn log         │                  │
   │                         │                   │                  │
   │── produce(topicA) ─────────────────────────→│ write msg        │
   │── produce(topicB) ─────────────────────────→│ write msg        │
   │   (messages written     │                   │ (not yet visible │
   │    but not visible)     │                   │  to read_committed)
   │                         │                   │                  │
   │── commitTransaction() ─→│                   │                  │
   │                         │ write COMMIT       │                  │
   │                         │ markers to all     │                  │
   │                         │ partitions ───────→│                  │
   │                         │                   │ messages now     │
   │                         │                   │ visible ─────────→│ can read
```

**Key components:**
- **Transaction Coordinator** — a broker that manages the transaction state machine for a given `transactional.id` (determined by hash of `transactional.id` % 50)
- **Transaction Log** (`__transaction_state`) — internal compacted topic storing transaction state (BEGIN, PREPARE_COMMIT, COMMIT, ABORT)
- **Control messages** — COMMIT/ABORT markers written to each partition involved in the transaction

### Zombie Fencing in Detail

When a producer crashes mid-transaction and restarts, two instances may briefly exist:

```
Timeline:
  t=0   Producer A (epoch=1, txn.id=task-proc-1) begins transaction
  t=1   Producer A crashes mid-transaction
  t=2   Producer B starts with same txn.id=task-proc-1
  t=3   Producer B calls initTransactions()
           → Coordinator bumps epoch to 2
           → Coordinator aborts Producer A's pending transaction
           → Any future writes from epoch=1 are rejected (fenced)
  t=4   Producer B begins new transaction safely

Fencing guarantee:
  Old producer (epoch=1): all writes rejected → ProducerFencedException
  New producer (epoch=2): sole owner of transactional.id
```

This is why `transactional.id` must be:
- **Stable across restarts** — same instance gets the same ID so it can fence its predecessor
- **Unique per instance** — two concurrent producers must not share an ID

**Assigning transactional.id in practice:**

| Deployment | Strategy | Example |
|-----------|----------|---------|
| Single instance | Hardcoded or config-based | `"order-processor"` |
| Multiple instances, static | Instance index | `"order-processor-0"`, `"order-processor-1"` |
| Kubernetes | StatefulSet pod name | `"order-processor-" + os.environ["HOSTNAME"]` |
| Kafka Streams | Automatic | Streams assigns `{application.id}-{task_id}` internally |

### Transaction Timeout and Failure Handling

```python
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'transactional.id': 'order-processor-0',
    'transaction.timeout.ms': 60000,  # Default. Max: 900000 (15 min)
    'enable.idempotence': True,
    'acks': 'all',
})
producer.init_transactions()

try:
    producer.begin_transaction()
    producer.produce('order-events', key=order_id, value=event)
    producer.produce('audit-log', key=order_id, value=audit)

    # Include consumer offset in the transaction
    producer.send_offsets_to_transaction(
        consumer.position(consumer.assignment()),
        consumer.consumer_group_metadata(),
    )
    producer.commit_transaction()

except BufferError:
    # Internal buffer full — abort and retry
    producer.abort_transaction()

except KafkaException as e:
    if e.args[0].code() == KafkaError._FENCED:
        # Another instance took over our transactional.id — shut down
        print("Fenced by newer producer instance, shutting down")
        producer.close()
        sys.exit(1)
    else:
        # Transient error — abort and retry
        producer.abort_transaction()
```

**Failure scenarios:**

| Failure | What Happens | Recovery |
|---------|-------------|----------|
| Producer crashes before commit | Coordinator times out transaction → auto-abort | New producer instance fences old one, re-reads from last committed offset |
| Network partition during commit | Coordinator retries internally | Commit eventually succeeds or times out → abort |
| Coordinator broker fails | New coordinator elected from ISR, reads transaction log | Transaction resumes (commit or abort) |
| `transaction.timeout.ms` exceeded | Coordinator aborts the transaction | Producer gets `InvalidProducerEpochException` on next operation |

## When to Use Kafka Transactions

### Use Transactions

| Scenario | Why |
|----------|-----|
| **Consume-transform-produce** | Atomic read + process + write + offset commit prevents duplicates and data loss |
| **Multi-topic atomic writes** | Event + audit log + notification must all appear or none |
| **Kafka Streams exactly_once_v2** | Built-in, one config change, no manual transaction code |
| **Fan-out from single event** | One input event → writes to 3 output topics atomically |

### Don't Use Transactions

| Scenario | Why Not | Use Instead |
|----------|---------|-------------|
| **Single topic, single partition writes** | Idempotent producer already prevents duplicates | `enable.idempotence=true` alone |
| **Consumer → database** | Kafka transactions don't cover external systems | Idempotent consumer (dedup table) |
| **Consumer → HTTP API** | Can't roll back an API call | Idempotent consumer + retry |
| **Long-running processing (>15 min)** | `transaction.timeout.ms` max is 15 minutes | Break into smaller units, use checkpointing |
| **High-throughput, low-latency** | Transaction commit adds 5-20ms per batch | At-least-once + idempotent consumer |
| **Simple produce-only** | No offset to commit, no multi-topic atomicity needed | Idempotent producer |
