---
name: apache-kafka
description: Comprehensive Apache Kafka event-driven architecture skill from hello world to professional production systems. Use when building event-driven systems, real-time data pipelines, stream processing, or any Kafka-based messaging architecture including producers, consumers, Kafka Streams, Kafka Connect, security, and production deployment. Before making recommendations, this skill gathers context about your production requirements and constraints.
---

# Apache Kafka Skill

This skill provides comprehensive support for building event-driven architectures with Apache Kafka, from simple hello world examples to professional production-ready systems. Before providing specific recommendations, this skill will gather important context about your production requirements and constraints.

## When to Use This Skill

Use this skill when you need to:
- Build event-driven architectures with Kafka
- Create producers and consumers (Java, Python, or other languages)
- Implement real-time stream processing with Kafka Streams
- Set up data integration pipelines with Kafka Connect
- Configure Kafka security (SSL/TLS, SASL, ACLs)
- Deploy and tune production Kafka clusters
- Design topic structures and partitioning strategies
- Implement exactly-once semantics and transactional messaging
- Monitor and troubleshoot Kafka systems

## Pre-Implementation Context Gathering

Before providing specific recommendations, this skill will gather important context about your production requirements and constraints:

### Team Experience Assessment
- What is your team's current experience with Kafka? (beginner, intermediate, advanced)
- Have you worked with distributed systems before?
- Do you have experience with container orchestration (Docker, Kubernetes)?

### Scale Requirements
- What is your expected message throughput? (messages per second)
- What is your expected message size? (average and maximum)
- How much data retention do you need? (hours, days, weeks)
- Do you anticipate rapid growth in message volume?

### Latency Requirements
- What are your end-to-end latency requirements? (milliseconds, seconds, minutes)
- Are you processing real-time or near-real-time data?
- Do you need exactly-once, at-least-once, or at-most-once delivery semantics?

### Infrastructure Constraints
- What infrastructure do you have available? (cloud, on-premises, hybrid)
- What is your preferred deployment method? (bare metal, VMs, containers, managed service)
- Do you have specific compliance or security requirements?

### Operational Considerations
- What monitoring and observability tools do you currently use?
- Do you have dedicated DevOps/SRE resources for Kafka operations?
- What are your disaster recovery and backup requirements?

## Prerequisites

- Java 11+ (for Kafka brokers and Java clients)
- Apache Kafka binaries or Docker images
- Python 3.8+ with confluent-kafka (for Python clients)

## Quick Start: Hello World

### Start Kafka (KRaft mode - no ZooKeeper)

```bash
# Generate a cluster UUID
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"

# Format storage
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID \
  -c config/kraft/server.properties

# Start Kafka
bin/kafka-server-start.sh config/kraft/server.properties
```

### Create a Topic

```bash
bin/kafka-topics.sh --create \
  --topic hello-world \
  --bootstrap-server localhost:9092 \
  --partitions 3 \
  --replication-factor 1
```

### Produce Messages

```bash
bin/kafka-console-producer.sh \
  --topic hello-world \
  --bootstrap-server localhost:9092 \
  --property "key.separator=:" \
  --property "parse.key=true"
```

### Consume Messages

```bash
bin/kafka-console-consumer.sh \
  --topic hello-world \
  --from-beginning \
  --bootstrap-server localhost:9092 \
  --property "print.key=true"
```

### Docker Compose (Quick Start)

```yaml
# docker-compose.yml
services:
  kafka:
    image: apache/kafka:3.9.0
    hostname: broker
    container_name: broker
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@broker:29093
      KAFKA_LISTENERS: PLAINTEXT://broker:29092,CONTROLLER://broker:29093,PLAINTEXT_HOST://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://broker:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
```

```bash
docker compose up -d
```

## Architecture Overview

```
Producers → [Topic (Partitions)] → Consumers
              ↓
         Kafka Broker(s)        → Consumer Groups
              ↓
         Kafka Connect          → External Systems
              ↓
         Kafka Streams          → Stream Processing
```

### Core Components

| Component | Purpose |
|-----------|---------|
| **Broker** | Server that stores and serves messages |
| **Topic** | Named feed of messages, divided into partitions |
| **Partition** | Ordered, immutable sequence of records |
| **Producer** | Client that publishes messages to topics |
| **Consumer** | Client that reads messages from topics |
| **Consumer Group** | Set of consumers that cooperate to consume a topic |
| **Kafka Streams** | Library for stream processing applications |
| **Kafka Connect** | Framework for integrating with external systems |
| **KRaft** | Consensus protocol replacing ZooKeeper (default since Kafka 3.3+)

## Kafka Core Mental Model

### Topics and Partitions

A **topic** is a named log. A **partition** is an ordered, append-only segment of that log. Every topic has one or more partitions.

```
Topic: task-events (6 partitions)

  P0: [offset 0] [offset 1] [offset 2] [offset 3] ...
  P1: [offset 0] [offset 1] [offset 2] ...
  P2: [offset 0] [offset 1] [offset 2] [offset 3] [offset 4] ...
  P3: [offset 0] [offset 1] ...
  P4: [offset 0] [offset 1] [offset 2] [offset 3] ...
  P5: [offset 0] [offset 1] [offset 2] ...

Multiple producers write to the SAME topic:
  API-1 ──┐
  API-2 ──┤──> task-events ──> partitioned by key hash
  API-3 ──┘

Key rule: murmur2(task_id) % partition_count → target partition
  → All events for task_id=42 land in the SAME partition
  → Ordering is guaranteed per partition (and therefore per key)
```

### When and How to Partition

| Factor | Guidance |
|--------|----------|
| **Parallelism** | More partitions = more consumers can read in parallel. One partition can only be read by one consumer within a group |
| **Ordering needs** | Ordering is guaranteed only within a partition. Key by entity ID (e.g., `task_id`, `order_id`) to keep related events together |
| **Consumer count** | Partition count is the upper bound on parallelism within a group. 6 partitions = max 6 consumers per group |
| **Broker load** | Each partition has a leader on one broker. Spread across brokers for balance. Avoid thousands of small partitions |
| **Starting point** | `max(expected_throughput / per_consumer_throughput, max_consumer_count)` — for most workloads, 6-12 partitions is a reasonable start |

**Partitions can be increased but never decreased.** Choose based on your expected peak consumer count. Over-partitioning wastes broker resources; under-partitioning caps parallelism.

### Offsets

Every message in a partition has a unique **offset** — a monotonically increasing integer assigned by the broker on append.

```
Partition 2: [0] [1] [2] [3] [4] [5] [6] [7]
                            ↑              ↑
                     committed offset   log-end offset
                     (consumer position) (latest message)

              LAG = log-end offset - committed offset = 3
```

Each consumer group tracks its own committed offset **per partition** in the internal `__consumer_offsets` topic:

```
__consumer_offsets:
  Group: notification  │  task-events P0: 150  │  P1: 142  │  P2: 155
  Group: audit         │  task-events P0: 150  │  P1: 150  │  P2: 155
  Group: analytics     │  task-events P0: 80   │  P1: 75   │  P2: 90
```

**Offset commit strategies:**

| Strategy | How | Risk | Use When |
|----------|-----|------|----------|
| Auto commit | `enable.auto.commit=true` (every 5s default) | May commit before processing finishes — message loss on crash | Low-value, high-throughput events (metrics, logs) |
| Manual sync | `commitSync()` after processing | Blocks the consumer until committed | Correctness matters (payments, orders) |
| Manual async | `commitAsync()` after processing | Non-blocking but no retry on failure | Moderate importance, high throughput |

**Offset reset** — what happens when a consumer has no committed offset:

| Policy | Behavior | Use When |
|--------|----------|----------|
| `earliest` | Read from the beginning of the partition | New consumer group that must process all history |
| `latest` | Read only new messages from this point forward | New consumer group that only cares about future events |
| `none` | Throw an exception | Fail-safe — force explicit offset management |

### Consumer Groups and Parallel Processing

A **consumer group** is a set of consumers sharing the same `group.id`. Kafka distributes partitions across group members so they split the work.

```
Topic: task-events (6 partitions)

Group: notification (2 consumers)     Group: analytics (3 consumers)
  consumer-1 → P0, P1, P2              consumer-1 → P0, P1
  consumer-2 → P3, P4, P5              consumer-2 → P2, P3
                                        consumer-3 → P4, P5

Group: audit (1 consumer)
  consumer-1 → P0, P1, P2, P3, P4, P5
```

**Key rules:**
- Each partition is assigned to **exactly one** consumer within a group
- Each group gets a **full copy** of every message (independent offsets)
- Adding a group = adding a new subscriber (zero changes to producers)
- Adding consumers within a group = more parallelism (up to partition count)
- More consumers than partitions = idle consumers doing nothing

**Scaling example:**

```
Start:  1 consumer, 6 partitions → 1 consumer reads all 6 (bottleneck)
Scale:  3 consumers, 6 partitions → each reads 2 (3x throughput)
Scale:  6 consumers, 6 partitions → each reads 1 (max parallelism)
Scale:  8 consumers, 6 partitions → 6 active, 2 idle (wasted)
```

**Rebalancing** occurs when consumers join or leave a group. Kafka redistributes partitions:

```
analytics group — consumer-2 crashes:
  Before: C1→P0,P1  C2→P2,P3  C3→P4,P5
  After:  C1→P0,P1,P2  C3→P3,P4,P5     ← P2,P3 redistributed
```

Use `CooperativeStickyAssignor` (recommended) to minimize disruption during rebalancing — only the affected partitions move, not all of them.

### Consumer Lag — When Consumers Can't Keep Up

Lag = `log-end offset - committed offset` per partition. Growing lag means the consumer is falling behind.

```bash
# Check lag
bin/kafka-consumer-groups.sh --describe --group analytics \
  --bootstrap-server localhost:9092

# GROUP      TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# analytics  task-events  0          80              155             75
# analytics  task-events  1          75              150             75
```

| Lag Pattern | Diagnosis | Action |
|-------------|-----------|--------|
| Lag is stable and small | Consumer keeping up | No action needed |
| Lag is growing steadily | Consumer is slower than producer rate | Add consumers (up to partition count), or increase partitions and consumers together |
| Lag spikes then recovers | Temporary slowdown (GC, network) | Monitor, usually self-healing |
| Lag is stuck (offset not moving) | Consumer is down or stuck | Check consumer health, restart if needed |

## Event-Driven Architecture Fundamentals

### When to Use Event-Driven Architecture

| Use EDA When | Stay Synchronous When |
|--------------|-----------------------|
| Downstream work is independent of the API response | The caller needs the result to continue (e.g., validate payment before confirming) |
| Multiple services react to the same event | Only one service needs the data |
| Services have different throughput/availability needs | The operation must be atomic and immediate |
| You need to add new consumers without changing producers | The interaction is simple request/response with one downstream |
| Audit trails or event replay are required | Latency budget is < 10ms end-to-end |

### Producers and Consumers

A **producer** is any service that publishes events to a topic. A **consumer** is any service that subscribes to a topic and reacts to events. A single service can be both.

```
                    ┌─ Consumer Group A ─┐
Producer ──> Topic ─┤                    │
                    └─ Consumer Group B ─┘

Key rules:
  • Producer knows only the topic, never the consumers
  • Each consumer group gets a full copy of every event
  • Within a group, partitions are split across consumers (parallelism)
  • Adding a consumer group = adding a new subscriber (zero producer changes)
```

**Dual-role example (consume-transform-produce):**

```
Payment Service:
  Consumes from: checkout.initiated
  Produces to:   payment.result

  → It is a consumer of checkout events
  → It is a producer of payment result events
```

### Eventual Consistency

In an event-driven system, services do **not** share a database or transaction. Each service updates its own state independently after consuming events. This means there is a **consistency window** where different services have different views of the world.

```
Timeline — Order #42:

t=0ms    Checkout API:      order = "pending"     ← produces checkout.initiated
t=50ms   Payment Service:   payment = "charged"   ← produces payment.result
t=80ms   Inventory Service: stock = "reserved"    ← produces inventory.result
t=150ms  Orchestrator:      order = "confirmed"   ← produces order.confirmed
t=200ms  Email Service:     email = "sent"

Consistency window: t=0 to t=150ms
During this window, Payment sees "charged" but the order is still "pending"
```

#### Designing for Eventual Consistency

| Challenge | Solution |
|-----------|----------|
| **Customer reads stale state** | Return current status from the owning service's DB ("pending" → "confirmed"). Set UI expectations: "Processing your order..." |
| **Partial failure mid-saga** | Use compensation events. If payment succeeds but inventory fails, produce an `order.failed` event that triggers a refund |
| **Duplicate events (at-least-once delivery)** | Make consumers idempotent — use event ID or entity ID as a deduplication key, or use upsert/PUT semantics in DB writes |
| **Out-of-order events** | Key events by entity ID (e.g., `order_id`) so all events for one entity go to the same partition, preserving order |
| **"Read your own writes" needed** | After producing, update the local DB in the same service. Read from local state, not from downstream consumers |

#### When Eventual Consistency Is Acceptable vs. Not

| Acceptable | Not Acceptable |
|------------|----------------|
| Order confirmation email arrives seconds after checkout | Charging the customer twice for the same order |
| Analytics dashboard reflects a sale after a short delay | Overselling inventory beyond physical stock |
| Search index updates within seconds of a product change | Showing "payment confirmed" when payment actually failed |

For the "not acceptable" cases, use **idempotent producers** (`enable.idempotence=true`), **transactions** for atomic multi-topic writes, and **consumer-side deduplication** to prevent duplicate processing.

### Orchestration vs. Choreography

Two patterns for coordinating multi-service workflows:

**Choreography** — each service reacts to events independently, no central coordinator:

```
checkout.initiated → Payment Service → payment.result
                   → Inventory Service → inventory.result
payment.result + inventory.result → ??? (who decides the order is complete?)
```

- Simpler for 2-3 services
- Harder to trace and debug as services grow
- No single place that knows the full workflow state

**Orchestration** — a central service (orchestrator) coordinates the saga:

```
checkout.initiated → Order Orchestrator
  → consumes payment.result, inventory.result, fraud.result
  → when all succeed → produces order.confirmed
  → when any fail → produces order.failed (triggers compensation)
```

- One place owns the workflow logic and state
- Easier to monitor, debug, and add steps
- The orchestrator is a consumer of result topics and a producer of decision topics

**Recommendation:** Start with choreography for simple flows (2 services). Move to orchestration when you have 3+ services, compensation logic, or need to track saga state.

## Reference Documentation

### Core References

| Reference | Description |
|-----------|-------------|
| [CORE_CONCEPTS.md](references/CORE_CONCEPTS.md) | Topics, partitions, brokers, offsets, consumer groups, and replication |
| [PRODUCER.md](references/PRODUCER.md) | Producer API (Java & Python), configuration, idempotency, transactions |
| [CONSUMER.md](references/CONSUMER.md) | Consumer API (Java & Python), consumer groups, offset management |
| [STREAMS.md](references/STREAMS.md) | Kafka Streams DSL, Processor API, topologies, state stores |
| [CONNECT.md](references/CONNECT.md) | Source/sink connectors, REST API, transforms, dead letter queues |
| [SECURITY.md](references/SECURITY.md) | SSL/TLS, SASL (SCRAM, OAUTHBEARER, Kerberos), ACLs, SASL_SSL client config (Python/Java), security protocol matrix, auth mechanism comparison |
| [DEPLOYMENT.md](references/DEPLOYMENT.md) | Production deployment, KRaft, broker tuning, monitoring |
| [CONFIGURATION.md](references/CONFIGURATION.md) | Broker, producer, consumer, and Streams configuration reference |
| [STRIMZI.md](references/STRIMZI.md) | Strimzi Kafka on Kubernetes: CRDs, KRaft mode, dev/prod clusters, topics, users, Connect, client Deployment manifests, PDB, NetworkPolicy, cert rotation, Cruise Control, resource quotas, tiered node pools |
| [SERIALIZATION.md](references/SERIALIZATION.md) | Avro schemas, Schema Registry, compatibility modes, schema evolution rules, SerializingProducer/DeserializingConsumer |
| [DELIVERY_SEMANTICS.md](references/DELIVERY_SEMANTICS.md) | At-most-once, at-least-once, exactly-once; idempotent consumers; transactions; Kafka Streams EOS; decision flowchart |
| [CDC_OUTBOX.md](references/CDC_OUTBOX.md) | Dual-write problem, CDC vs polling, transactional outbox, outbox table DDL, Debezium Outbox Event Router, PostgreSQL WAL setup |
| [AGENT_TRACING.md](references/AGENT_TRACING.md) | correlation_id/causation_id patterns, EventContext propagation, causality tree reconstruction, agent event taxonomy, depth circuit breaker, OpenTelemetry bridge |
| [SAGA_PATTERNS.md](references/SAGA_PATTERNS.md) | Orchestration vs choreography, saga state machine, command/reply envelopes, compensation design, participant pattern, state persistence, timeout handling, idempotency |
| [MONITORING_OPS.md](references/MONITORING_OPS.md) | Consumer lag diagnosis, group state inspection, offset management, poison message handling, rebalance storms, hot partition detection, Prometheus alerting, CLI reference, troubleshooting checklist |

## Service Coupling Types & Event-Driven Solutions

When services call each other directly (synchronous HTTP/gRPC), three types of coupling emerge. Kafka-based event-driven architecture addresses all three.

### Temporal Coupling

**Problem:** The caller blocks until all downstream services respond. Latency is additive.

```
API ──sync──> Service A (500ms)
    ──sync──> Service B (500ms)
    ──sync──> Service C (500ms)
                    Total: 1500ms
```

**How events solve it:** The API produces an event (~5ms) and returns immediately. Consumers process asynchronously.

```
API ──produce──> [topic] → Service A (async)
                         → Service B (async)
                         → Service C (async)
        Response: ~5ms
```

### Availability Coupling

**Problem:** If any downstream service is down, the caller fails. Effective availability is multiplicative.

```
Combined availability = 99.9% × 99.9% × 99.9% = 99.7%
                        (+2.6 hours downtime/year vs single service)
```

**How events solve it:** The API only depends on Kafka (99.95%+ availability). If a consumer is down, messages queue in the topic and are processed when the consumer recovers. No data loss, no caller failure.

### Behavioral Coupling

**Problem:** The caller must know every downstream service. Adding a new consumer requires changing the caller's code.

```
# Adding Analytics requires modifying the API:
def create_task(data):
    notify(data)      # existing
    audit(data)        # existing
    remind(data)       # existing
    analytics(data)    # ← new code change, new deployment
```

**How events solve it:** The API publishes events to a topic. New consumers subscribe independently — zero changes to the producer.

```
# API code never changes:
producer.produce('task-events', value=event)

# New service just subscribes:
consumer = Consumer({'group.id': 'analytics-service'})
consumer.subscribe(['task-events'])
```

### Coupling Summary

| Coupling Type | Symptom | Sync (HTTP) | Async (Kafka) |
|---------------|---------|-------------|---------------|
| **Temporal** | Slow responses | Latency = sum of all calls | Latency = produce time (~5ms) |
| **Availability** | Cascading failures | All services must be up | Only Kafka must be up |
| **Behavioral** | Frequent producer changes | Producer knows all consumers | Producer knows only the topic |

> **When to keep synchronous calls:** Use direct calls when the caller needs the response to continue (e.g., validating payment before confirming an order). Use events when downstream processing is independent of the caller's response.

## Common Patterns

### Event-Driven Microservices

```
Order Service → [orders topic] → Payment Service
                                → Inventory Service
                                → Notification Service
```

### Event Sourcing

```
Commands → [command topic] → Aggregate → [event topic] → Projections
                                                        → Read Models
```

### CQRS (Command Query Responsibility Segregation)

```
Write API → [events topic] → Kafka Streams → Materialized Views → Read API
```

### Change Data Capture (CDC)

```
Database → Debezium (Source Connector) → [change topic] → Sink Connector → Data Warehouse
```

### Saga Pattern (Distributed Transactions)

```
Order Saga:
  1. [order-created] → Payment Service
  2. [payment-confirmed] → Inventory Service
  3. [inventory-reserved] → Shipping Service
  4. [shipping-scheduled] → Order Service (complete)

  Compensation:
  [payment-failed] → Order Service (cancel)
  [inventory-failed] → Payment Service (refund)
```

## Language Support

### Java (Native Client)

```java
// Producer
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", "org.apache.kafka.common.serialization.StringSerializer");

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.send(new ProducerRecord<>("my-topic", "key", "value"));
producer.close();
```

### Python (confluent-kafka)

```python
from confluent_kafka import Producer, Consumer

# Producer
producer = Producer({'bootstrap.servers': 'localhost:9092'})
producer.produce('my-topic', key='key', value='value')
producer.flush()

# Consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'my-group',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['my-topic'])
msg = consumer.poll(1.0)
```

### Python (kafka-python)

```python
from kafka import KafkaProducer, KafkaConsumer

# Producer
producer = KafkaProducer(bootstrap_servers='localhost:9092')
producer.send('my-topic', key=b'key', value=b'value')

# Consumer
consumer = KafkaConsumer('my-topic',
    bootstrap_servers='localhost:9092',
    group_id='my-group',
    auto_offset_reset='earliest')
for msg in consumer:
    print(msg.value)
```

## Framework Integration: FastAPI + Kafka

`confluent-kafka` is a blocking C-based library. In async frameworks like FastAPI, use these patterns to avoid blocking the event loop.

### Key Principles

| Concern | Solution |
|---------|----------|
| **Producer poll()** | Run `producer.poll(0)` in a background `asyncio` task (non-blocking) |
| **Producer singleton** | One `Producer` instance per process — it's thread-safe with an internal buffer + background thread |
| **Consumer blocking loop** | Run in `asyncio.to_thread()` — the consumer's `poll()` blocks and must not run on the event loop |
| **Lifecycle management** | Use FastAPI's `lifespan` context manager to start/stop Kafka connections |
| **Graceful shutdown** | `producer.flush()` on shutdown; set a flag to stop the consumer loop, then `consumer.close()` |

### Complete Example

```python
import json, asyncio, uuid, signal
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from confluent_kafka import Producer, Consumer, KafkaError
from fastapi import FastAPI
from pydantic import BaseModel


class KafkaProducerPool:
    """One Producer per process. Background task polls delivery callbacks."""

    def __init__(self, config: dict):
        self._producer = Producer(config)
        self._poll_task: asyncio.Task | None = None

    async def start(self):
        self._poll_task = asyncio.create_task(self._poll_loop())

    async def _poll_loop(self):
        while True:
            self._producer.poll(0)       # non-blocking — triggers callbacks
            await asyncio.sleep(0.1)     # yields to event loop

    def produce(self, topic: str, key: str, value: dict, on_delivery=None):
        self._producer.produce(
            topic, key=key,
            value=json.dumps(value).encode("utf-8"),
            on_delivery=on_delivery,
        )

    async def stop(self):
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
        remaining = self._producer.flush(timeout=10)
        if remaining > 0:
            print(f"WARNING: {remaining} messages not delivered on shutdown")


class KafkaConsumerWorker:
    """Runs blocking consumer.poll() in a thread via asyncio.to_thread()."""

    def __init__(self, config: dict, topics: list[str], handler):
        self._config = config
        self._topics = topics
        self._handler = handler
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(asyncio.to_thread(self._loop))

    def _loop(self):
        consumer = Consumer(self._config)
        consumer.subscribe(self._topics)
        try:
            while self._running:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    print(f"Consumer error: {msg.error()}")
                    continue
                try:
                    self._handler(msg)
                    consumer.commit(asynchronous=False)
                except Exception as e:
                    print(f"Processing error: {e}")
        finally:
            consumer.close()

    async def stop(self):
        self._running = False
        if self._task:
            await self._task


# --- App setup ---

producer_pool: KafkaProducerPool | None = None
consumer_worker: KafkaConsumerWorker | None = None


def handle_task_event(msg):
    data = json.loads(msg.value().decode("utf-8"))
    print(f"Received: {data['event_type']} for {data['data']['task_id']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer_pool, consumer_worker
    producer_pool = KafkaProducerPool({
        "bootstrap.servers": "localhost:9092",
        "acks": "all",
        "enable.idempotence": True,
        "linger.ms": 10,
    })
    await producer_pool.start()
    consumer_worker = KafkaConsumerWorker(
        config={
            "bootstrap.servers": "localhost:9092",
            "group.id": "fastapi-task-consumer",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        },
        topics=["task-events"],
        handler=handle_task_event,
    )
    await consumer_worker.start()
    yield
    await consumer_worker.stop()
    await producer_pool.stop()


app = FastAPI(lifespan=lifespan)


class TaskCreate(BaseModel):
    title: str
    assignee: str


@app.post("/tasks")
async def create_task(task: TaskCreate):
    task_id = str(uuid.uuid4())
    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": "task.created",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "task-api",
        "data": {"task_id": task_id, "title": task.title, "assignee": task.assignee},
    }
    producer_pool.produce("task-events", key=task_id, value=event)
    return {"task_id": task_id, "status": "accepted"}
```

## Common Commands

```bash
# Topic management
bin/kafka-topics.sh --list --bootstrap-server localhost:9092
bin/kafka-topics.sh --describe --topic my-topic --bootstrap-server localhost:9092
bin/kafka-topics.sh --alter --topic my-topic --partitions 6 --bootstrap-server localhost:9092
bin/kafka-topics.sh --delete --topic my-topic --bootstrap-server localhost:9092

# Consumer groups
bin/kafka-consumer-groups.sh --list --bootstrap-server localhost:9092
bin/kafka-consumer-groups.sh --describe --group my-group --bootstrap-server localhost:9092
bin/kafka-consumer-groups.sh --reset-offsets --group my-group --topic my-topic --to-earliest --execute --bootstrap-server localhost:9092

# Performance testing
bin/kafka-producer-perf-test.sh --topic perf-test --num-records 1000000 --record-size 1024 --throughput -1 --producer-props bootstrap.servers=localhost:9092
bin/kafka-consumer-perf-test.sh --topic perf-test --messages 1000000 --bootstrap-server localhost:9092

# ACLs
bin/kafka-acls.sh --add --allow-principal User:app1 --operation Read --topic my-topic --bootstrap-server localhost:9092
bin/kafka-acls.sh --list --bootstrap-server localhost:9092
```

## Production Checklist

Before deploying to production:

### Infrastructure
- [ ] Minimum 3 brokers across availability zones
- [ ] KRaft mode enabled (no ZooKeeper dependency)
- [ ] Dedicated disks for Kafka log directories
- [ ] Network bandwidth sufficient (10 GbE recommended)
- [ ] `broker.rack` configured for rack awareness

### Configuration
- [ ] Replication factor >= 3
- [ ] `min.insync.replicas` = 2
- [ ] `unclean.leader.election.enable` = false
- [ ] Producer `acks=all` for critical topics
- [ ] Appropriate `retention.ms` and `retention.bytes`

### Security
- [ ] SSL/TLS encryption for all connections
- [ ] SASL authentication enabled
- [ ] ACLs configured with least-privilege
- [ ] Inter-broker communication encrypted

### Monitoring
- [ ] Under-replicated partitions alert
- [ ] Consumer lag monitoring
- [ ] Broker disk usage alerts
- [ ] Request latency dashboards
- [ ] JMX metrics exported to monitoring system

### Operations
- [ ] Backup strategy for topic configurations
- [ ] Disaster recovery plan tested
- [ ] Rolling restart procedure documented
- [ ] Partition reassignment tooling ready

## Official Documentation

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Confluent Documentation](https://docs.confluent.io/)
- [Kafka Streams Developer Guide](https://kafka.apache.org/documentation/streams/)
- [Kafka Connect User Guide](https://kafka.apache.org/documentation/#connect)
- [confluent-kafka-python](https://docs.confluent.io/kafka-clients/python/current/overview.html)