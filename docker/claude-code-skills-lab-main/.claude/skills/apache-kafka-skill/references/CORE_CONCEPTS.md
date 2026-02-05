# Kafka Core Concepts

## Topics

A **topic** is a named feed of messages. Topics are multi-subscriber — a topic can have zero, one, or many consumers.

```
Topic: "orders"
├── Partition 0: [msg0, msg1, msg2, msg3, ...]
├── Partition 1: [msg0, msg1, msg2, ...]
└── Partition 2: [msg0, msg1, msg2, msg3, msg4, ...]
```

### Topic Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `num.partitions` | 1 | Default partitions for auto-created topics |
| `retention.ms` | 604800000 (7 days) | How long to retain messages |
| `retention.bytes` | -1 (unlimited) | Max bytes per partition before deletion |
| `cleanup.policy` | delete | `delete` or `compact` |
| `min.insync.replicas` | 1 | Min replicas that must acknowledge writes |
| `max.message.bytes` | 1048588 | Max message size |

### Compacted Topics

Log compaction retains the last known value for each message key:

```
Before compaction:
  key=A val=1, key=B val=2, key=A val=3, key=B val=4

After compaction:
  key=A val=3, key=B val=4
```

Use `cleanup.policy=compact` for changelog/state topics.

## Partitions

Partitions provide **parallelism** and **ordering**. Messages within a partition are strictly ordered by offset.

### Partition Assignment

- Messages with the **same key** go to the **same partition** (via `DefaultPartitioner` using murmur2 hash)
- Messages with **no key** use sticky partitioning (batch to one partition, then rotate)
- Custom partitioners can override this behavior

### Choosing Partition Count

| Factor | Guidance |
|--------|----------|
| Throughput | More partitions = more parallelism |
| Consumer count | At most one consumer per partition in a group |
| Ordering | Ordering guaranteed only within a partition |
| Broker load | Each partition has a leader; spread across brokers |
| Recommendation | Start with `max(throughput / consumer_throughput, consumer_count)` |

## Offsets

Each message in a partition has a unique **offset** — a monotonically increasing integer.

```
Partition 0: [offset=0] [offset=1] [offset=2] [offset=3]
                                      ↑
                              consumer position
```

### Offset Management

| Strategy | Description |
|----------|-------------|
| Auto commit | `enable.auto.commit=true` — commits periodically (default 5s) |
| Manual sync | `commitSync()` — blocks until committed |
| Manual async | `commitAsync()` — non-blocking, with optional callback |
| Specific offset | Commit specific offsets per partition |

### Offset Reset Policies

| Policy | Behavior |
|--------|----------|
| `earliest` | Start from beginning of partition |
| `latest` | Start from end of partition (default) |
| `none` | Throw exception if no committed offset |

## Consumer Groups

A consumer group is a set of consumers sharing a `group.id` that cooperatively consume from topic(s).

```
Topic with 4 partitions:
  Group "order-processors" (3 consumers):
    Consumer-1 → Partition 0, Partition 1
    Consumer-2 → Partition 2
    Consumer-3 → Partition 3
```

### Rebalancing

Rebalancing occurs when:
- A consumer joins or leaves the group
- A consumer crashes (session timeout)
- Topic partitions change

#### Partition Assignment Strategies

| Strategy | Description |
|----------|-------------|
| `RangeAssignor` | Assigns consecutive partitions per topic |
| `RoundRobinAssignor` | Round-robin across all partitions |
| `StickyAssignor` | Minimizes partition movement on rebalance |
| `CooperativeStickyAssignor` | Incremental cooperative rebalancing (recommended) |

### Static Group Membership

Set `group.instance.id` to avoid unnecessary rebalances during rolling restarts:

```properties
group.instance.id=consumer-host-1
session.timeout.ms=300000
```

## Replication

Each partition is replicated across multiple brokers for fault tolerance.

```
Topic "orders", Partition 0 (replication-factor=3):
  Broker 1: Leader    ← producers/consumers talk to this
  Broker 2: Follower  ← replicates from leader
  Broker 3: Follower  ← replicates from leader
```

### In-Sync Replicas (ISR)

The ISR is the set of replicas that are "caught up" with the leader. It is the core mechanism behind Kafka's durability and fault tolerance.

**How a replica joins and leaves the ISR:**

```
replica.lag.time.max.ms = 30000 (default)

Broker 3 (follower) fetches from Broker 1 (leader):

  t=0s    Last fetch: up to date         → ISR = {B1, B2, B3}
  t=10s   Broker 3 slow disk, no fetch
  t=20s   Still no fetch from Broker 3
  t=30s   30s since last caught-up fetch → ISR shrinks: {B1, B2}
          (Broker 3 removed from ISR)

  t=35s   Broker 3 resumes fetching
  t=36s   Broker 3 catches up to leader  → ISR grows: {B1, B2, B3}
```

The ISR is dynamic — replicas are added and removed automatically based on `replica.lag.time.max.ms`. The leader tracks this and updates the ISR in the cluster metadata.

**What "committed" means:**

A message is **committed** (durable) only when all current ISR members have written it. The **high-water mark** is the offset of the last committed message. Consumers with `isolation.level=read_committed` only see messages up to the high-water mark.

```
Leader (B1):   [0] [1] [2] [3] [4] [5] [6]
Follower (B2): [0] [1] [2] [3] [4] [5]
Follower (B3): [0] [1] [2] [3] [4]
                                 ↑
                          high-water mark = 4
                          (last offset replicated to ALL ISR members)

Messages [5] and [6] exist on the leader but are NOT yet committed.
If the leader crashes now, [5] and [6] may be lost.
```

### min.insync.replicas and acks=all Interaction

`acks=all` tells the producer to wait for all ISR members to acknowledge. `min.insync.replicas` (set on the broker or topic) sets the **floor** — the broker rejects writes if the ISR is smaller than this value.

```
replication.factor=3, min.insync.replicas=2

Scenario 1: All brokers healthy (ISR = 3)
  Producer → Leader → replicate to B2 ✓, B3 ✓ → ACK to producer ✓
  Tolerates: 1 broker failure

Scenario 2: One broker down (ISR = 2)
  Producer → Leader → replicate to B2 ✓ → ACK to producer ✓
  ISR=2 >= min.insync.replicas=2 → writes accepted
  Tolerates: 0 more failures (but no data loss so far)

Scenario 3: Two brokers down (ISR = 1)
  Producer → Leader → ISR=1 < min.insync.replicas=2
  → NotEnoughReplicasException → producer retries
  Writes BLOCKED until ISR recovers (data integrity preserved)
```

**The fault tolerance formula:**

```
Tolerated broker failures = replication.factor - min.insync.replicas

  RF=3, min.isr=2 → tolerates 1 failure  (recommended for most production)
  RF=3, min.isr=1 → tolerates 2 failures (but data at risk if leader dies with ISR=1)
  RF=5, min.isr=3 → tolerates 2 failures (high durability, higher storage cost)
```

| Setting | RF=3, min.isr=2 | RF=3, min.isr=1 | RF=5, min.isr=3 |
|---------|-----------------|-----------------|-----------------|
| **Tolerated failures** | 1 | 2 (with risk) | 2 |
| **Write availability** | Needs 2+ brokers | Needs 1+ broker | Needs 3+ brokers |
| **Data safety** | Strong | Weak if ISR=1 | Strongest |
| **Storage cost** | 3x | 3x | 5x |
| **Use case** | Most production | Dev/staging | Financial, regulated |

### Leader Election

- Preferred leader: first replica in the assignment list
- When the leader fails, a new leader is elected from the ISR
- `unclean.leader.election.enable=false` (recommended) prevents out-of-sync replicas from becoming leader

**Why unclean leader election is dangerous:**

```
ISR = {B1 (leader)}  ← B2 and B3 fell out of ISR
B1 crashes

  unclean.leader.election.enable=true:
    B2 becomes leader even though it's behind
    Messages that only existed on B1 are PERMANENTLY LOST
    New writes continue on B2 — divergent log, silent data loss

  unclean.leader.election.enable=false:
    Partition goes OFFLINE — no reads or writes
    Waits until B1 (or another ISR member) recovers
    Data integrity preserved at the cost of availability
```

**Trade-off:** `false` = data safety over availability (recommended for production). `true` = availability over data safety (acceptable only if losing some messages is tolerable).

## Brokers

A Kafka **broker** is a server that stores topic partitions and serves client requests.

### KRaft Mode (Kafka 3.3+)

KRaft replaces ZooKeeper for metadata management:

```properties
process.roles=broker,controller    # Combined mode
# OR
process.roles=broker               # Dedicated broker
process.roles=controller           # Dedicated controller
```

### Broker Roles

| Role | Responsibility |
|------|---------------|
| **Broker** | Stores data, serves produce/fetch requests |
| **Controller** | Manages metadata, leader elections, config |
| **Combined** | Both roles on same node (small clusters) |

## Message Format

A Kafka record consists of:

| Field | Description |
|-------|-------------|
| Key | Optional, used for partitioning and compaction |
| Value | The message payload |
| Headers | Optional key-value metadata pairs |
| Timestamp | Create time or log append time |
| Offset | Assigned by broker on append |

### Serialization

Common serializers:
- `StringSerializer` / `StringDeserializer`
- `ByteArraySerializer` / `ByteArrayDeserializer`
- `IntegerSerializer` / `IntegerDeserializer`
- `JsonSerializer` (Spring Kafka)
- `KafkaAvroSerializer` (Schema Registry)
- `KafkaProtobufSerializer` (Schema Registry)
