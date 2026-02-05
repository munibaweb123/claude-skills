# Kafka Consumer Reference

## Java Consumer API

### Basic Consumer

```java
import org.apache.kafka.clients.consumer.*;
import java.time.Duration;
import java.util.List;
import java.util.Properties;

Properties props = new Properties();
props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(ConsumerConfig.GROUP_ID_CONFIG, "my-group");
props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG,
    "org.apache.kafka.common.serialization.StringDeserializer");
props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG,
    "org.apache.kafka.common.serialization.StringDeserializer");
props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("my-topic"));

try {
    while (true) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
        for (ConsumerRecord<String, String> record : records) {
            System.out.printf("topic=%s partition=%d offset=%d key=%s value=%s%n",
                record.topic(), record.partition(), record.offset(),
                record.key(), record.value());
        }
    }
} finally {
    consumer.close();
}
```

### Manual Offset Commit

```java
props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("my-topic"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, String> record : records) {
        processRecord(record);
    }
    // Synchronous commit after processing
    consumer.commitSync();
}
```

### Commit Specific Offsets

```java
Map<TopicPartition, OffsetAndMetadata> offsets = new HashMap<>();
for (ConsumerRecord<String, String> record : records) {
    processRecord(record);
    offsets.put(
        new TopicPartition(record.topic(), record.partition()),
        new OffsetAndMetadata(record.offset() + 1)  // +1: next offset to read
    );
}
consumer.commitSync(offsets);
```

### Assign Specific Partitions (No Consumer Group)

```java
TopicPartition p0 = new TopicPartition("my-topic", 0);
TopicPartition p1 = new TopicPartition("my-topic", 1);
consumer.assign(List.of(p0, p1));
consumer.seekToBeginning(List.of(p0));
consumer.seek(p1, 100);  // Start at offset 100
```

### Consume-Transform-Produce (Exactly-Once)

```java
// Producer with transactions
props.put(ProducerConfig.TRANSACTIONAL_ID_CONFIG, "etl-processor-1");
KafkaProducer<String, String> producer = new KafkaProducer<>(producerProps);
producer.initTransactions();

// Consumer with read_committed
consumerProps.put(ConsumerConfig.ISOLATION_LEVEL_CONFIG, "read_committed");
consumerProps.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);
KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);
consumer.subscribe(List.of("input-topic"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
    if (records.isEmpty()) continue;

    producer.beginTransaction();
    try {
        for (ConsumerRecord<String, String> record : records) {
            String transformed = transform(record.value());
            producer.send(new ProducerRecord<>("output-topic", record.key(), transformed));
        }
        // Commit consumer offsets within the transaction
        producer.sendOffsetsToTransaction(
            currentOffsets(records), consumer.groupMetadata());
        producer.commitTransaction();
    } catch (Exception e) {
        producer.abortTransaction();
    }
}
```

## Python Consumer API

### confluent-kafka

```python
from confluent_kafka import Consumer, KafkaError
import json

conf = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
}

consumer = Consumer(conf)
consumer.subscribe(['my-topic'])

try:
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            print(f"Error: {msg.error()}")
            break

        data = json.loads(msg.value().decode('utf-8'))
        print(f"Key: {msg.key()}, Value: {data}, "
              f"Partition: {msg.partition()}, Offset: {msg.offset()}")

        consumer.commit(asynchronous=False)
finally:
    consumer.close()
```

### Batch Processing

```python
from confluent_kafka import Consumer

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'batch-group',
    'enable.auto.commit': False,
    'auto.offset.reset': 'earliest',
    'max.poll.interval.ms': 300000,
    'fetch.min.bytes': 1048576,       # 1MB min fetch
    'fetch.max.wait.ms': 500,
})
consumer.subscribe(['events'])

batch = []
BATCH_SIZE = 100

while True:
    msg = consumer.poll(1.0)
    if msg and not msg.error():
        batch.append(msg)
        if len(batch) >= BATCH_SIZE:
            process_batch(batch)
            consumer.commit(asynchronous=False)
            batch = []
```

## Key Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `group.id` | — | Consumer group identifier (required for subscribe) |
| `auto.offset.reset` | `latest` | `earliest`, `latest`, or `none` |
| `enable.auto.commit` | true | Auto-commit offsets periodically |
| `auto.commit.interval.ms` | 5000 | Auto-commit frequency |
| `max.poll.records` | 500 | Max records per poll() call |
| `max.poll.interval.ms` | 300000 | Max time between polls before rebalance |
| `session.timeout.ms` | 45000 | Consumer heartbeat timeout |
| `heartbeat.interval.ms` | 3000 | Heartbeat frequency (1/3 of session timeout) |
| `fetch.min.bytes` | 1 | Min data per fetch request |
| `fetch.max.wait.ms` | 500 | Max wait for fetch.min.bytes |
| `fetch.max.bytes` | 52428800 | Max data per fetch request |
| `max.partition.fetch.bytes` | 1048576 | Max data per partition per fetch |
| `isolation.level` | `read_uncommitted` | `read_committed` for transactional reads |
| `partition.assignment.strategy` | `RangeAssignor, CooperativeStickyAssignor` | Rebalance strategy |
| `group.instance.id` | null | Static membership ID |

## Partition Assignment and Rebalancing

### How Partition Assignment Works

When consumers join a group, the **group coordinator** (a broker) selects one consumer as the **group leader**. The leader runs the assignment strategy and distributes partitions.

```
1. Consumers send JoinGroup to coordinator
2. Coordinator picks a leader (first consumer to join)
3. Leader receives full member list + subscriptions
4. Leader runs assignment strategy → produces partition map
5. Leader sends map to coordinator → coordinator distributes to all members
6. Each consumer receives its assignment and begins fetching
```

### When Rebalancing Occurs

| Trigger | Detection Time | Example |
|---------|---------------|---------|
| **Consumer joins** | Immediate | New instance deployed, scale-up |
| **Consumer leaves gracefully** | Immediate | `consumer.close()` sends LeaveGroup |
| **Consumer crashes** | `session.timeout.ms` (default 45s) | Process killed, OOM, network partition |
| **Consumer too slow** | `max.poll.interval.ms` (default 300s) | Slow processing, GC pause, blocked thread |
| **Topic partitions change** | Immediate | `--alter --partitions 9` adds partitions |
| **Subscription change** | Immediate | Consumer subscribes to additional topics |

### Eager vs Cooperative Rebalancing

#### Eager Protocol (RangeAssignor, RoundRobinAssignor)

All partitions are revoked from all consumers, then reassigned. **Every consumer stops processing** during the rebalance, even if its partitions don't change.

```
notification-service (3 consumers, 6 partitions)
Consumer-4 joins the group:

  Step 1 — REVOKE ALL:
    C1→(stop)  C2→(stop)  C3→(stop)         ← ALL consumers halt
    All 6 partitions unowned, no processing

  Step 2 — REASSIGN ALL:
    C1→P0,P1  C2→P2,P3  C3→P4  C4→P5       ← ALL consumers restart

  Downtime: entire group stopped during reassignment
  C1 and C2 kept the same partitions but still had to stop and restart
```

#### Cooperative Protocol (CooperativeStickyAssignor)

Only affected partitions are revoked, in two incremental phases. **Unaffected consumers keep processing.**

```
Consumer-4 joins the group:

  Phase 1 — REVOKE only what needs to move:
    C1→P0,P1  C2→P2,P3  C3→P4              ← only P5 revoked from C3
    C1, C2 never stop. C3 keeps processing P4.

  Phase 2 — ASSIGN revoked partitions:
    C1→P0,P1  C2→P2,P3  C3→P4  C4→P5       ← P5 assigned to C4

  Downtime: only P5 was briefly unprocessed
  C1 and C2 processed continuously through both phases
```

#### Comparison

| Aspect | Eager | Cooperative |
|--------|-------|-------------|
| Revocation | All partitions from all consumers | Only partitions that need to move |
| Processing during rebalance | Fully stopped | Continues on unaffected partitions |
| Number of rebalance rounds | 1 | 2 (revoke round + assign round) |
| Partition stickiness | None — may shuffle everything | Maximizes stability — keeps assignments that work |
| Config | `partition.assignment.strategy=range` or `roundrobin` | `partition.assignment.strategy=cooperative-sticky` |
| Recommendation | Legacy only | **Use this for all new consumers** |

### Static Group Membership — Eliminating Rebalances During Deploys

Without static membership, restarting a consumer triggers two rebalances: one for leave, one for rejoin. During a rolling deployment of N instances, that's up to 2N rebalances.

With static membership, each consumer gets a permanent `group.instance.id`. When it disconnects, the broker **holds its partition assignment** for `session.timeout.ms` instead of immediately rebalancing. If the consumer comes back with the same ID within that window, it resumes its old assignment with zero rebalance.

```
Rolling deploy WITHOUT static membership (3 instances):
  t=0s    Stop C1 → LeaveGroup → rebalance #1 (C2 gets P0,P1)
  t=10s   Start C1 → JoinGroup → rebalance #2 (C1 gets P0,P1 back)
  t=20s   Stop C2 → rebalance #3
  t=30s   Start C2 → rebalance #4
  t=40s   Stop C3 → rebalance #5
  t=50s   Start C3 → rebalance #6
  Total: 6 rebalances, all consumers disrupted repeatedly

Rolling deploy WITH static membership:
  t=0s    Stop C1 → broker holds assignment (no LeaveGroup sent)
  t=15s   Start C1 → same group.instance.id → resumes P0,P1 → NO rebalance
  t=20s   Stop C2 → broker holds assignment
  t=35s   Start C2 → resumes P2,P3 → NO rebalance
  t=40s   Stop C3 → broker holds assignment
  t=55s   Start C3 → resumes P4,P5 → NO rebalance
  Total: 0 rebalances
```

#### Configuration

```python
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'notification-service',
    'enable.auto.commit': False,

    # Cooperative rebalancing
    'partition.assignment.strategy': 'cooperative-sticky',

    # Static membership — unique per instance, stable across restarts
    'group.instance.id': f'notif-{hostname}',

    # Hold assignment for 5 minutes — longer than restart time
    'session.timeout.ms': 300000,
    'heartbeat.interval.ms': 10000,
})
```

**`session.timeout.ms` tradeoff with static membership:** A longer timeout means more time for restarts without rebalancing, but also more time before a truly dead consumer is detected. Set it to slightly longer than your longest expected restart.

| Deploy Method | `session.timeout.ms` Recommendation |
|---------------|--------------------------------------|
| Rolling restart (10-20s per instance) | 60000 (1 min) |
| Rolling deploy with health checks | 120000 (2 min) |
| Blue-green / canary with slow startup | 300000 (5 min) |

### Failure Scenarios

```
Scenario: Consumer-2 crashes (3 consumers, 6 partitions, cooperative-sticky)

  Before: C1→P0,P1   C2→P2,P3   C3→P4,P5

  Without static membership:
    t=0s     C2 crashes, no heartbeat
    t=45s    session.timeout.ms expires → broker triggers rebalance
    t=45.5s  Phase 1: C3 gives up P4 (cooperative)
    t=46s    Phase 2: C1→P0,P1,P2  C3→P3,P4,P5  (or similar)
    Impact:  P2,P3 unprocessed for ~45 seconds

  With static membership:
    t=0s     C2 crashes
    t=300s   session.timeout.ms expires → broker triggers rebalance
    Impact:  P2,P3 unprocessed for ~5 minutes (but zero rebalances if C2 restarts)
    Tradeoff: longer detection = longer gap if truly dead
```

```
Scenario: Scale from 3 to 4 consumers (cooperative-sticky)

  Before:  C1→P0,P1   C2→P2,P3   C3→P4,P5
  Phase 1: C1→P0,P1   C2→P2,P3   C3→P4      ← P5 revoked from C3
  Phase 2: C1→P0,P1   C2→P2,P3   C3→P4  C4→P5

  C1 and C2 never stopped. C3 briefly lost P5 only.
```

```
Scenario: All 3 consumers crash simultaneously

  Before:  C1→P0,P1   C2→P2,P3   C3→P4,P5
  After:   No consumers in group
  Impact:  All 6 partitions unprocessed, messages queue in Kafka
  Recovery: New consumers join → full assignment from scratch
            All queued messages processed (no data loss, just delay)
```

## Offset Commit Timing — Why It Matters

The order of "process" and "commit" determines your delivery guarantee. Getting this wrong is the most common source of consumer data loss.

### Commit AFTER Processing (Correct — At-Least-Once)

```
poll() → process() → commit()
                        ↓
         If crash happens BEFORE commit:
           Offset not persisted → restart re-reads same message → SAFE (reprocessed)
         If crash happens AFTER commit:
           Message was processed AND committed → SAFE (done)
```

### Commit BEFORE Processing (Wrong — At-Most-Once / Data Loss)

```
poll() → commit() → process() → crash!
                                  ↓
         Offset already committed, but message never processed
         On restart: consumer picks up NEXT message → SKIPPED = DATA LOSS
```

### Auto-Commit (Risky — Implicit Commit-Before-Process)

```
poll() → [auto-commit fires on timer] → process() → crash!
                                                      ↓
         Same as commit-before-process — offset committed, message not processed
```

Auto-commit commits on a timer (default 5s) inside `poll()`, regardless of whether you finished processing the previous batch. If processing is slow, auto-commit fires before you're done.

## Auto-Commit vs Manual Commit

| Strategy | Config | Guarantee | Risk | Use When |
|----------|--------|-----------|------|----------|
| **Auto-commit** | `enable.auto.commit=true` | At-most-once | Commits before processing finishes → message loss on crash | Low-value events where loss is acceptable (metrics, logs, clickstream) |
| **Manual sync** | `enable.auto.commit=false` + `commitSync()` | At-least-once | Blocks the consumer thread until broker confirms; slower throughput | Correctness matters (payments, orders, audit) |
| **Manual async** | `enable.auto.commit=false` + `commitAsync()` | At-least-once (mostly) | Non-blocking but no retry on commit failure; rare offset regression on crash | High throughput where occasional reprocessing is acceptable |
| **Manual sync + async** | Async during loop, sync on shutdown | At-least-once | Best balance of throughput and safety | Production default for most workloads |

### Python — Manual Sync (Recommended for Correctness)

```python
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'task-processor',
    'enable.auto.commit': False,       # CRITICAL: disable auto-commit
    'auto.offset.reset': 'earliest',
})
consumer.subscribe(['task-events'])

try:
    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            handle_kafka_error(msg)
            continue

        process_event(msg)                  # Process FIRST
        consumer.commit(asynchronous=False)  # Commit AFTER — blocks until confirmed
finally:
    consumer.close()
```

### Python — Async + Sync Hybrid (Recommended for Throughput)

```python
try:
    while running:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            handle_kafka_error(msg)
            continue

        process_event(msg)
        consumer.commit(asynchronous=True)   # Non-blocking during normal operation
finally:
    consumer.commit(asynchronous=False)      # Final sync commit on shutdown
    consumer.close()
```

### Java — Manual Commit

```java
props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false);

try (KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props)) {
    consumer.subscribe(List.of("task-events"));
    while (running) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
        for (ConsumerRecord<String, String> record : records) {
            processRecord(record);
        }
        if (!records.isEmpty()) {
            consumer.commitSync();  // Commit after entire batch processed
        }
    }
}
```

## Graceful Shutdown

`consumer.close()` does three things: commits current offsets, sends a leave-group request to the broker, and triggers an immediate rebalance for remaining consumers. **Skipping `close()` means the broker waits for `session.timeout.ms` (default 45s) before rebalancing** — a 45-second stall where assigned partitions are unprocessed.

### Python — Signal-Based Shutdown

```python
import signal

running = True

def shutdown_handler(sig, frame):
    global running
    logger.info("Shutdown signal received, finishing current message...")
    running = False

signal.signal(signal.SIGINT, shutdown_handler)
signal.signal(signal.SIGTERM, shutdown_handler)

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'task-processor',
    'enable.auto.commit': False,
})
consumer.subscribe(['task-events'])

try:
    while running:                          # Signal sets running=False
        msg = consumer.poll(timeout=1.0)    # Returns None within 1s → exits loop
        if msg is None:
            continue
        if msg.error():
            handle_kafka_error(msg)
            continue

        process_event(msg)
        consumer.commit(asynchronous=False)
finally:
    # Always reached — even on exception
    consumer.close()     # Commits offsets + leave-group + triggers rebalance
    logger.info("Consumer shut down cleanly")
```

### What Happens on Shutdown

```
SIGTERM received
  │
  ▼
running = False
  │
  ▼
poll(timeout=1.0) returns None (within 1 second)
  │
  ▼
while loop exits
  │
  ▼
finally: consumer.close()
  ├── Commits current offsets to broker
  ├── Sends LeaveGroup request
  └── Broker immediately reassigns partitions to other group members
      (no 45-second wait)
```

### Java — Shutdown Hook

```java
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    running.set(false);
    try { shutdownLatch.await(); } catch (InterruptedException ignored) {}
}));

try {
    while (running.get()) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));
        for (ConsumerRecord<String, String> record : records) {
            processRecord(record);
        }
        consumer.commitSync();
    }
} finally {
    consumer.close();
    shutdownLatch.countDown();
}
```

## Processing Failure Patterns

### Deserialization Errors (Poison Messages)

A message with invalid JSON or wrong encoding prevents `json.loads()` from succeeding. Without handling, the consumer retries the same bad message forever.

```python
try:
    event = json.loads(msg.value().decode('utf-8'))
except (json.JSONDecodeError, UnicodeDecodeError) as e:
    logger.error("Poison message at %s [%d] @ %d: %s",
                 msg.topic(), msg.partition(), msg.offset(), e)
    send_to_dlq(msg, error=str(e))
    consumer.commit(asynchronous=False)   # Skip past the bad message
    continue
```

### Processing Errors — Retry Then DLQ

```python
MAX_RETRIES = 3

def process_with_retry(msg):
    event = json.loads(msg.value().decode('utf-8'))
    for attempt in range(MAX_RETRIES):
        try:
            process_event(event)
            return  # Success
        except RetriableError as e:
            wait = (2 ** attempt) * 0.1  # 100ms, 200ms, 400ms
            logger.warning("Retry %d/%d for offset %d: %s",
                           attempt + 1, MAX_RETRIES, msg.offset(), e)
            time.sleep(wait)
        except NonRetriableError as e:
            logger.error("Non-retriable error at offset %d: %s", msg.offset(), e)
            break  # Skip to DLQ immediately

    # All retries exhausted or non-retriable — send to DLQ
    send_to_dlq(msg, error="retries exhausted")
```

### Dead Letter Queue (Python)

```python
dlq_producer = Producer({'bootstrap.servers': 'localhost:9092'})

def send_to_dlq(msg, error):
    """Route failed message to dead-letter topic with diagnostic headers."""
    dlq_producer.produce(
        topic=f"{msg.topic()}.DLQ",
        key=msg.key(),
        value=msg.value(),
        headers={
            'original_topic': msg.topic(),
            'original_partition': str(msg.partition()),
            'original_offset': str(msg.offset()),
            'error': error,
            'consumer_group': 'task-processor',
        },
    )
    dlq_producer.poll(0)
```

### Full Error Handling Flow

```
poll() → msg
  │
  ├── msg.error()?
  │     ├── PARTITION_EOF → continue (normal, end of partition)
  │     └── other → raise KafkaException (fatal)
  │
  ├── deserialize
  │     └── fails → DLQ + commit + continue (poison message)
  │
  ├── process_with_retry()
  │     ├── succeeds → commit
  │     └── all retries fail → DLQ + commit + continue
  │
  └── commit(asynchronous=False)
```

## max.poll.interval.ms — Avoiding Unexpected Rebalances

If `process_event()` takes longer than `max.poll.interval.ms` (default 300s / 5 min), the broker assumes the consumer is dead and triggers a rebalance — revoking its partitions and assigning them to other consumers.

```
  t=0s     poll() returns batch of 500 messages
  t=0-280s processing messages... (slow DB writes, external API calls)
  t=300s   max.poll.interval.ms exceeded — NO poll() call yet
           broker: "consumer is dead" → triggers rebalance
           consumer loses its partitions mid-processing
  t=310s   processing finishes, commitSync() → ERROR: partitions revoked
```

### Solutions

| Approach | How | When |
|----------|-----|------|
| **Increase the timeout** | `max.poll.interval.ms=600000` (10 min) | Processing is inherently slow (batch DB writes, ML inference) |
| **Reduce batch size** | `max.poll.records=50` (default 500) | Process fewer messages per poll to stay within the timeout |
| **Move slow work async** | Produce to another topic, process in separate consumer | Processing time is unpredictable or very long |

```python
# For slow consumers: reduce batch size + increase timeout
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'slow-processor',
    'enable.auto.commit': False,
    'max.poll.records': 50,            # Small batches
    'max.poll.interval.ms': 600000,    # 10 minutes
    'session.timeout.ms': 45000,       # Keep default (heartbeat-based)
    'heartbeat.interval.ms': 3000,     # Keep default
})
```

`session.timeout.ms` and `heartbeat.interval.ms` are separate from `max.poll.interval.ms`. Heartbeats are sent from a background thread — they confirm the consumer process is alive. `max.poll.interval.ms` confirms the consumer is *making progress* (calling `poll()` regularly).

## Consumer Group Management

### Monitoring Consumer Lag

```bash
# Describe consumer group
bin/kafka-consumer-groups.sh --describe --group my-group \
  --bootstrap-server localhost:9092

# Output:
# GROUP    TOPIC      PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# my-group my-topic   0          1000            1050            50
# my-group my-topic   1          2000            2000            0
```

### Reset Offsets

```bash
# Reset to earliest
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group --topic my-topic \
  --to-earliest --execute \
  --bootstrap-server localhost:9092

# Reset to specific offset
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group --topic my-topic:0 \
  --to-offset 500 --execute \
  --bootstrap-server localhost:9092

# Reset to timestamp
bin/kafka-consumer-groups.sh --reset-offsets \
  --group my-group --topic my-topic \
  --to-datetime 2024-01-01T00:00:00.000 --execute \
  --bootstrap-server localhost:9092
```

## Error Handling Patterns

### Dead Letter Queue

```java
while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(100));
    for (ConsumerRecord<String, String> record : records) {
        try {
            processRecord(record);
        } catch (Exception e) {
            // Send to DLQ
            producer.send(new ProducerRecord<>(
                "my-topic.DLQ",
                record.key(),
                record.value()
            ));
        }
    }
    consumer.commitSync();
}
```

### Retry with Backoff

```java
int maxRetries = 3;
for (ConsumerRecord<String, String> record : records) {
    boolean success = false;
    for (int attempt = 0; attempt < maxRetries && !success; attempt++) {
        try {
            processRecord(record);
            success = true;
        } catch (RetriableException e) {
            Thread.sleep((long) Math.pow(2, attempt) * 100);
        }
    }
    if (!success) {
        sendToDlq(record);
    }
}
```
