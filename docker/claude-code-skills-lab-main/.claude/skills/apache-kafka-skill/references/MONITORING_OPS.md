# Monitoring & Operational Troubleshooting

## Consumer Lag Diagnosis

### Step 1: List All Consumer Groups

```bash
bin/kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# Output:
# notification-svc
# analytics-svc
# payment-service
# order-saga-orchestrator
```

### Step 2: Describe a Group (Per-Partition Lag)

```bash
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092
```

```
GROUP          TOPIC        PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG    CONSUMER-ID                     HOST          CLIENT-ID
analytics-svc  order-events 0          12050           15230           3180   analytics-1-abc123              /10.0.1.15    analytics-1
analytics-svc  order-events 1          11980           15195           3215   analytics-1-abc123              /10.0.1.15    analytics-1
analytics-svc  order-events 2          12100           15210           3110   analytics-2-ghi789              /10.0.1.16    analytics-2
analytics-svc  order-events 3          14900           15180           280    analytics-2-ghi789              /10.0.1.16    analytics-2
analytics-svc  order-events 4          15050           15220           170    analytics-3-mno345              /10.0.1.17    analytics-3
analytics-svc  order-events 5          15100           15240           140    analytics-3-mno345              /10.0.1.17    analytics-3
```

### Reading the Output

```
CURRENT-OFFSET  = last committed offset (where the consumer IS)
LOG-END-OFFSET  = latest message in the partition (where the topic IS)
LAG             = LOG-END-OFFSET - CURRENT-OFFSET (messages behind)
CONSUMER-ID     = which consumer instance owns this partition
HOST            = IP of the consumer pod/machine

Observations:
  analytics-1 (10.0.1.15): P0 lag=3180, P1 lag=3215    ← PROBLEM: both partitions lagging
  analytics-2 (10.0.1.16): P2 lag=3110, P3 lag=280     ← P2 lagging, P3 fine (hot partition?)
  analytics-3 (10.0.1.17): P4 lag=170,  P5 lag=140     ← healthy

  Total lag: 10,095 messages
```

### Step 3: Check if Lag Is Growing or Stable

Run `--describe` twice, 30 seconds apart, and compare:

```bash
# Snapshot 1
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092 2>/dev/null \
  | awk 'NR>1 {print $3, $6}' > /tmp/lag1.txt

sleep 30

# Snapshot 2
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092 2>/dev/null \
  | awk 'NR>1 {print $3, $6}' > /tmp/lag2.txt

paste /tmp/lag1.txt /tmp/lag2.txt
# P0 3180  P0 3400   ← growing (+220 in 30s = ~7.3 msg/s falling behind)
# P4 170   P4 155    ← shrinking (catching up)
```

### Lag Pattern Diagnosis

| Pattern | Meaning | Action |
|---------|---------|--------|
| Growing steadily | Consumer slower than producer rate | Scale consumers or optimize processing |
| Stable but high | Past incident, now keeping pace | Will recover on its own if stable |
| Stuck (offset not moving) | Consumer is dead or blocked | Check pod health, restart, check for poison messages |
| Spikes then recovers | Temporary slowdown (GC, network, DB) | Monitor; usually self-healing |
| One partition much higher | Hot partition (key skew) | Check key distribution |
| All partitions equal | Producer rate increased uniformly | Scale consumers (up to partition count) |

---

## Group State Inspection

### Group State

```bash
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092 --state

# GROUP          COORDINATOR (ID)  ASSIGNMENT-STRATEGY  STATE     #MEMBERS
# analytics-svc  broker2:9092 (2)  range                Stable    3
```

| State | Meaning | Action |
|-------|---------|--------|
| `Stable` | Normal operation, all partitions assigned | Check lag if needed |
| `PreparingRebalance` | Consumer joined/left, redistribution starting | Wait — usually resolves in seconds |
| `CompletingRebalance` | Almost done rebalancing | Wait |
| `Empty` | **No consumers running** — lag grows unbounded | Deploy/restart consumer pods immediately |
| `Dead` | Group metadata expired (no consumers for a long time) | Recreate consumer deployment |

### Member Details

```bash
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092 --members --verbose

# GROUP          CONSUMER-ID            HOST        CLIENT-ID    #PARTITIONS  ASSIGNMENT
# analytics-svc  analytics-1-abc123     /10.0.1.15  analytics-1  2            order-events(0,1)
# analytics-svc  analytics-2-ghi789     /10.0.1.16  analytics-2  2            order-events(2,3)
# analytics-svc  analytics-3-mno345     /10.0.1.17  analytics-3  2            order-events(4,5)
```

**What to check:**
- Uneven partition distribution → consider `CooperativeStickyAssignor`
- One host with all high-lag partitions → that instance is the bottleneck
- Missing members → consumer pod crashed or was evicted

### Unassigned Partitions

If `CONSUMER-ID` shows `-`, the partition has no consumer:

```
# analytics-svc  order-events 0  12050  18500  6450  -  -  -
# analytics-svc  order-events 1  11980  18400  6420  -  -  -
```

This means the consumer for those partitions crashed and rebalancing hasn't completed (or there aren't enough consumers).

---

## Root Cause Decision Tree

```
Lag is growing
  │
  ├─ All partitions equally?
  │    └─→ Producer rate increased
  │        Action: Scale consumers (up to partition count)
  │                or increase partitions + consumers together
  │
  ├─ One consumer's partitions?
  │    └─→ Slow consumer instance
  │        ├─ Check CPU/memory on that host
  │        ├─ Check GC pauses (-XX:+PrintGCDetails or gc.log)
  │        ├─ Check downstream dependency (DB, HTTP call latency)
  │        └─ Action: Fix slow instance or restart it
  │
  ├─ One specific partition?
  │    └─→ Hot partition (key skew)
  │        ├─ Check key distribution (see below)
  │        └─ Action: Improve key design or re-partition
  │
  ├─ Lag stuck (offset not moving)?
  │    ├─ CONSUMER-ID = "-"
  │    │    └─→ Consumer is dead → restart consumer pod
  │    │
  │    ├─ Consumer exists but offset stuck
  │    │    └─→ Processing is blocked
  │    │        Check: Poison message? Downstream hanging?
  │    │        Action: Check logs, skip message if needed
  │    │
  │    └─ Group state = "Empty"
  │         └─→ No consumers running → deploy/restart
  │
  └─ Lag spikes after rebalance?
       └─→ Rebalance storm
           Check: Consumers joining/leaving repeatedly
           Action: Increase session.timeout.ms
                   Use CooperativeStickyAssignor
```

---

## Hot Partition Detection

### Check Message Distribution Across Partitions

```bash
# Get earliest and latest offsets per partition
bin/kafka-get-offsets.sh --topic order-events \
  --bootstrap-server localhost:9092

# order-events:0:0:15230      (partition:earliest:latest)
# order-events:1:0:15195
# order-events:2:0:25410      ← 10K more messages than others = hot partition
# order-events:3:0:15180
# order-events:4:0:15220
# order-events:5:0:15240
```

### Diagnose Key Skew

```bash
# Sample keys from a partition to find hot keys
bin/kafka-console-consumer.sh \
  --topic order-events \
  --bootstrap-server localhost:9092 \
  --partition 2 \
  --from-beginning \
  --max-messages 1000 \
  --property print.key=true \
  --property print.value=false \
  | sort | uniq -c | sort -rn | head -20

# Output:
#  412 customer-999     ← this key is dominating partition 2
#   23 customer-123
#   18 customer-456
#   ...
```

**Solutions for hot partitions:**
- Use a more granular key (e.g., `order_id` instead of `customer_id`)
- Add a sub-key: `customer_id + "-" + random_suffix` (breaks per-customer ordering)
- Use a custom partitioner that spreads hot keys across multiple partitions

---

## Offset Management

### Inspect Current Offsets

```bash
# Where each group is in each partition
bin/kafka-consumer-groups.sh --describe --group analytics-svc \
  --bootstrap-server localhost:9092

# Where the topic ends (latest offsets)
bin/kafka-get-offsets.sh --topic order-events --time latest \
  --bootstrap-server localhost:9092

# Where the topic begins (earliest retained offsets)
bin/kafka-get-offsets.sh --topic order-events --time earliest \
  --bootstrap-server localhost:9092
```

### Reset Offsets

**IMPORTANT:** The consumer group must be **stopped** before resetting offsets.

```bash
# Dry run first (--dry-run shows what would change)
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events \
  --to-latest --dry-run --bootstrap-server localhost:9092

# Reset to latest (skip all unprocessed messages)
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events \
  --to-latest --execute --bootstrap-server localhost:9092

# Reset to earliest (reprocess everything)
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events \
  --to-earliest --execute --bootstrap-server localhost:9092

# Reset to a specific timestamp
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events \
  --to-datetime 2025-01-15T10:00:00.000 --execute \
  --bootstrap-server localhost:9092

# Skip ahead by N messages on a specific partition
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events:2 \
  --shift-by 100 --execute --bootstrap-server localhost:9092

# Reset to a specific offset on a specific partition
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events:2 \
  --to-offset 15000 --execute --bootstrap-server localhost:9092
```

### When to Use Each Reset

| Reset Type | Use When |
|------------|----------|
| `--to-latest` | Skip poison messages, abandon unprocessed messages, fresh start |
| `--to-earliest` | Reprocess all data (new projection, backfill) |
| `--to-datetime` | Reprocess from a known-good point in time |
| `--shift-by N` | Skip N poison messages on a specific partition |
| `--to-offset` | Resume from a known offset (surgical fix) |

---

## Poison Message Handling

A **poison message** (or "poison pill") is a message that crashes the consumer every time it's processed — causing an infinite loop of crash → restart → re-consume → crash.

### Symptoms

```
Consumer logs:
  Processing message offset=15234... ERROR: NullPointerException
  Consumer restarting...
  Processing message offset=15234... ERROR: NullPointerException
  Consumer restarting...

Lag observation:
  CURRENT-OFFSET stays at 15234 (never advances)
  LOG-END-OFFSET keeps growing
```

### Solution 1: Dead Letter Topic (Recommended)

Build poison message handling into the consumer:

```python
DLT_TOPIC = "order-events.dlq"
MAX_RETRIES = 3

def consume_with_dlt(consumer, producer):
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue

        retries = 0
        while retries < MAX_RETRIES:
            try:
                process(msg)
                break
            except Exception as e:
                retries += 1
                if retries >= MAX_RETRIES:
                    # Send to dead letter topic
                    producer.produce(
                        DLT_TOPIC,
                        key=msg.key(),
                        value=msg.value(),
                        headers={
                            "original-topic": msg.topic(),
                            "original-partition": str(msg.partition()),
                            "original-offset": str(msg.offset()),
                            "error": str(e),
                            "retry-count": str(retries),
                        },
                    )
                    producer.poll(0)

        consumer.commit(asynchronous=False)
```

### Solution 2: Skip via Offset Reset

```bash
# Stop the consumer group, then skip past the poison message
bin/kafka-consumer-groups.sh --reset-offsets \
  --group analytics-svc --topic order-events:2 \
  --shift-by 1 --execute --bootstrap-server localhost:9092
```

### Solution 3: Error Tolerance in Kafka Connect

```json
{
  "errors.tolerance": "all",
  "errors.deadletterqueue.topic.name": "connect-dlq",
  "errors.deadletterqueue.topic.replication.factor": 3,
  "errors.deadletterqueue.context.headers.enable": true
}
```

---

## Rebalance Storm Diagnosis

A **rebalance storm** is when consumers repeatedly join/leave the group, causing constant partition reassignment and zero progress.

### Symptoms

```bash
# Consumer logs show repeated rebalance messages:
Revoking partitions [order-events-0, order-events-1]
Assigning partitions [order-events-0, order-events-1]
Revoking partitions [order-events-0, order-events-1]
Assigning partitions [order-events-0, order-events-1]
...

# Group state oscillates:
Stable → PreparingRebalance → CompletingRebalance → Stable → PreparingRebalance ...
```

### Common Causes and Fixes

| Cause | Symptom | Fix |
|-------|---------|-----|
| `max.poll.interval.ms` too low | Consumer processing takes longer than poll interval | Increase `max.poll.interval.ms` (default 5min) |
| `session.timeout.ms` too low | Consumer misses heartbeat during GC or slowdown | Increase `session.timeout.ms` (e.g., 45s) |
| `heartbeat.interval.ms` too high | Heartbeats too infrequent relative to session timeout | Set to `session.timeout.ms / 3` |
| Consumer OOM/crash loop | Pod restarts repeatedly | Fix memory, check resource limits |
| Rolling deployment too fast | Old pods leaving, new pods joining simultaneously | Use `maxSurge: 1, maxUnavailable: 0` |
| `range` assignment strategy | All partitions revoked during rebalance | Use `CooperativeStickyAssignor` |

### Recommended Consumer Config to Prevent Storms

```python
consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "analytics-svc",

    # Prevent rebalance during slow processing
    "max.poll.interval.ms": 300000,         # 5 min max between polls
    "session.timeout.ms": 45000,            # 45s heartbeat timeout
    "heartbeat.interval.ms": 15000,         # Heartbeat every 15s (= timeout / 3)

    # Limit batch size so polls complete within max.poll.interval
    "max.poll.records": 500,

    # Minimize rebalance disruption
    "partition.assignment.strategy": "cooperative-sticky",
})
```

---

## Consumer Tuning for Lag Recovery

When a consumer needs to catch up on a large backlog:

```python
# High-throughput catch-up configuration
consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "analytics-svc",

    # Pull more data per fetch
    "fetch.min.bytes": 1048576,              # 1 MB minimum per fetch (default: 1 byte)
    "fetch.max.wait.ms": 500,                # Wait up to 500ms to accumulate
    "max.partition.fetch.bytes": 1048576,     # 1 MB per partition per fetch
    "max.poll.records": 1000,                # Up to 1000 records per poll

    # Prevent rebalance during large batch processing
    "max.poll.interval.ms": 600000,          # 10 min
    "session.timeout.ms": 45000,
    "heartbeat.interval.ms": 15000,
    "partition.assignment.strategy": "cooperative-sticky",
    "enable.auto.commit": False,
})
```

### Scaling Consumers to Reduce Lag

```
Current:  3 consumers, 6 partitions → 2 partitions each
Problem:  Lag growing on all partitions

Option A: Scale consumers (partitions >= consumers)
  → Scale to 6 consumers: 1 partition each = 2x throughput
  kubectl scale deployment analytics-consumer --replicas=6

Option B: Scale partitions + consumers (need more than partition count)
  bin/kafka-topics.sh --alter --topic order-events \
    --partitions 12 --bootstrap-server localhost:9092
  kubectl scale deployment analytics-consumer --replicas=12
  → 4x throughput

  WARNING: Increasing partitions changes key→partition mapping
  (murmur2 hash mod new count). Existing keys may land in
  different partitions. Only safe if ordering across old/new
  messages is not critical for your use case.

Option C: Temporary catch-up consumer group
  → Deploy a fast consumer group that reads the backlog and
    writes results to a cache/DB. Decommission after caught up.
```

---

## Broker Health Checks

### Quick Cluster Health

```bash
# List all brokers
bin/kafka-metadata.sh --snapshot /var/kafka/data/__cluster_metadata-0/00000000000000000000.log \
  --cluster-id $CLUSTER_ID

# Describe topics — look for under-replicated partitions
bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 \
  --under-replicated-partitions

# If output is empty → all partitions are fully replicated (healthy)
# If partitions listed → those are under-replicated (investigate)
```

### Check for Offline Partitions

```bash
bin/kafka-topics.sh --describe --bootstrap-server localhost:9092 \
  --unavailable-partitions

# Empty = all partitions available (healthy)
# Listed partitions = CRITICAL — those partitions cannot serve reads/writes
```

### Disk Usage

```bash
# Check log directory sizes per topic
bin/kafka-log-dirs.sh --describe --bootstrap-server localhost:9092 \
  --topic-list order-events

# Output shows per-partition log sizes across brokers
# Watch for: one broker significantly larger (unbalanced)
#            total size approaching disk capacity
```

### Controller Status (KRaft)

```bash
# Check which broker is the active controller
bin/kafka-metadata.sh --snapshot /var/kafka/data/__cluster_metadata-0/00000000000000000000.log \
  --cluster-id $CLUSTER_ID

# Strimzi: check via kubectl
kubectl get pods -n kafka -l strimzi.io/pool-name=controllers
kubectl logs prod-cluster-controllers-0 -n kafka | grep -i "elected"
```

---

## Topic Inspection

### Describe Topic Configuration

```bash
bin/kafka-topics.sh --describe --topic order-events \
  --bootstrap-server localhost:9092

# Topic: order-events  TopicId: abc123  PartitionCount: 6  ReplicationFactor: 3
# Topic: order-events  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3
# Topic: order-events  Partition: 1  Leader: 2  Replicas: 2,3,1  Isr: 2,3,1
# ...

# Key fields:
#   Leader:   which broker serves reads/writes for this partition
#   Replicas: which brokers have copies
#   Isr:      which replicas are in-sync (should match Replicas)
```

**Isr smaller than Replicas** = under-replicated. A broker is behind or down.

### View Topic Configs

```bash
bin/kafka-configs.sh --describe --topic order-events \
  --bootstrap-server localhost:9092

# Dynamic configs for topic order-events:
#   retention.ms=604800000
#   min.insync.replicas=2
#   cleanup.policy=delete
#   compression.type=lz4
```

### Read Messages from a Topic (Debugging)

```bash
# Read the last 5 messages from a topic
bin/kafka-console-consumer.sh \
  --topic order-events \
  --bootstrap-server localhost:9092 \
  --from-beginning --max-messages 5 \
  --property print.key=true \
  --property print.timestamp=true \
  --property print.headers=true

# Read from a specific partition and offset
bin/kafka-console-consumer.sh \
  --topic order-events \
  --bootstrap-server localhost:9092 \
  --partition 2 --offset 15234 \
  --max-messages 1 \
  --property print.key=true \
  --property print.value=true
```

---

## Prometheus Alerting Rules

### Consumer Lag Alerts

```yaml
groups:
  - name: kafka-consumer-lag
    rules:
      # Lag is growing (warning)
      - alert: KafkaConsumerLagGrowing
        expr: |
          delta(kafka_consumergroup_lag_sum[5m]) > 0
          and kafka_consumergroup_lag_sum > 1000
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Consumer {{ $labels.consumergroup }} lag growing on {{ $labels.topic }}"
          description: "Lag is {{ $value }} and increasing for 10 minutes"

      # Lag critical (> 100K messages)
      - alert: KafkaConsumerLagCritical
        expr: kafka_consumergroup_lag_sum > 100000
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Consumer {{ $labels.consumergroup }} lag exceeds 100K"

      # Consumer group has no members
      - alert: KafkaConsumerGroupEmpty
        expr: kafka_consumergroup_members == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Consumer group {{ $labels.consumergroup }} has zero members"
```

### Broker Health Alerts

```yaml
  - name: kafka-broker-health
    rules:
      # Under-replicated partitions
      - alert: KafkaUnderReplicatedPartitions
        expr: kafka_server_replicamanager_underreplicatedpartitions > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Broker {{ $labels.instance }} has {{ $value }} under-replicated partitions"

      # Offline partitions (critical)
      - alert: KafkaOfflinePartitions
        expr: kafka_controller_kafkacontroller_offlinepartitionscount > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "{{ $value }} offline partitions — data unavailable"

      # ISR shrinking
      - alert: KafkaISRShrinking
        expr: rate(kafka_server_replicamanager_isrshrinkspersec[5m]) > 0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "ISR shrinking on broker {{ $labels.instance }}"

      # Request handler threads saturated
      - alert: KafkaRequestHandlersSaturated
        expr: kafka_server_kafkarequesthandlerpool_requesthandleravgidlepercent < 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Broker {{ $labels.instance }} request handlers < 30% idle"

      # Active controller count (should always be 1)
      - alert: KafkaNoActiveController
        expr: sum(kafka_controller_kafkacontroller_activecontrollercount) != 1
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Kafka cluster has {{ $value }} active controllers (expected 1)"

      # Disk usage
      - alert: KafkaDiskUsageHigh
        expr: |
          (kafka_log_size_bytes / kafka_log_max_size_bytes) > 0.8
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Broker {{ $labels.instance }} disk usage > 80%"
```

### Produce/Consume Latency Alerts

```yaml
  - name: kafka-latency
    rules:
      - alert: KafkaProduceLatencyHigh
        expr: |
          histogram_quantile(0.99,
            rate(kafka_network_requestmetrics_totaltimems_bucket{request="Produce"}[5m])
          ) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Produce p99 latency > 100ms on broker {{ $labels.instance }}"

      - alert: KafkaFetchLatencyHigh
        expr: |
          histogram_quantile(0.99,
            rate(kafka_network_requestmetrics_totaltimems_bucket{request="FetchConsumer"}[5m])
          ) > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Fetch p99 latency > 100ms on broker {{ $labels.instance }}"
```

### Alerting Thresholds Summary

| Metric | Warning | Critical |
|--------|---------|----------|
| Consumer lag (total) | > 1,000 and growing for 10m | > 100,000 for 5m |
| Consumer group members | — | = 0 for 2m |
| Under-replicated partitions | > 0 for 5m | — |
| Offline partitions | — | > 0 for 1m |
| ISR shrink rate | > 0 for 10m | — |
| Request handler idle % | < 30% for 5m | < 10% for 5m |
| Active controller count | — | != 1 for 1m |
| Disk usage | > 80% for 15m | > 90% for 5m |
| Produce p99 latency | > 100ms for 5m | > 500ms for 5m |

---

## Kafka Lag Exporter (Prometheus-native)

For continuous lag monitoring without polling `kafka-consumer-groups.sh`:

```yaml
# Helm install
helm repo add kafka-lag-exporter https://seglo.github.io/kafka-lag-exporter/repo/
helm install kafka-lag-exporter kafka-lag-exporter/kafka-lag-exporter \
  --namespace kafka \
  --set clusters[0].name=prod-cluster \
  --set clusters[0].bootstrapBrokers=prod-cluster-kafka-bootstrap:9093 \
  --set clusters[0].securityProtocol=SASL_SSL \
  --set clusters[0].saslMechanism=SCRAM-SHA-512
```

Exposes metrics:
- `kafka_consumergroup_group_lag` — lag per group/topic/partition
- `kafka_consumergroup_group_max_lag` — max lag across all partitions
- `kafka_consumergroup_group_sum_lag` — total lag for a group

---

## Common CLI Commands Reference

### Consumer Groups

```bash
# List groups
bin/kafka-consumer-groups.sh --list --bootstrap-server localhost:9092

# Describe (lag per partition)
bin/kafka-consumer-groups.sh --describe --group GROUP \
  --bootstrap-server localhost:9092

# Group state
bin/kafka-consumer-groups.sh --describe --group GROUP \
  --state --bootstrap-server localhost:9092

# Member details (which consumer owns which partitions)
bin/kafka-consumer-groups.sh --describe --group GROUP \
  --members --verbose --bootstrap-server localhost:9092

# Delete a group (must be empty)
bin/kafka-consumer-groups.sh --delete --group GROUP \
  --bootstrap-server localhost:9092
```

### Topics

```bash
# List topics
bin/kafka-topics.sh --list --bootstrap-server localhost:9092

# Describe topic (partitions, replicas, ISR)
bin/kafka-topics.sh --describe --topic TOPIC --bootstrap-server localhost:9092

# Under-replicated partitions across all topics
bin/kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092

# Unavailable partitions
bin/kafka-topics.sh --describe --unavailable-partitions \
  --bootstrap-server localhost:9092

# Get offsets (earliest/latest per partition)
bin/kafka-get-offsets.sh --topic TOPIC --time latest \
  --bootstrap-server localhost:9092
bin/kafka-get-offsets.sh --topic TOPIC --time earliest \
  --bootstrap-server localhost:9092

# Describe topic config overrides
bin/kafka-configs.sh --describe --topic TOPIC \
  --bootstrap-server localhost:9092

# Alter topic config
bin/kafka-configs.sh --alter --topic TOPIC \
  --add-config retention.ms=86400000 \
  --bootstrap-server localhost:9092
```

### Reading Messages

```bash
# Read from beginning (first N messages)
bin/kafka-console-consumer.sh --topic TOPIC --from-beginning \
  --max-messages 10 --bootstrap-server localhost:9092 \
  --property print.key=true --property print.timestamp=true

# Read specific partition + offset
bin/kafka-console-consumer.sh --topic TOPIC \
  --partition 2 --offset 15234 --max-messages 1 \
  --bootstrap-server localhost:9092 \
  --property print.key=true --property print.headers=true

# Read with consumer group (tracks offsets)
bin/kafka-console-consumer.sh --topic TOPIC \
  --group debug-consumer --bootstrap-server localhost:9092 \
  --property print.key=true
```

### Broker / Cluster

```bash
# List broker IDs
bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 \
  | head -5

# Log directory sizes per topic
bin/kafka-log-dirs.sh --describe --bootstrap-server localhost:9092 \
  --topic-list TOPIC

# Reassign partitions (after adding brokers)
bin/kafka-reassign-partitions.sh --generate \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3,4,5" \
  --bootstrap-server localhost:9092
```

---

## Troubleshooting Checklist

| Issue | First Check | Second Check | Resolution |
|-------|-------------|--------------|------------|
| Consumer lag growing | `--describe --group` (which partitions?) | `--members --verbose` (which consumer?) | Scale consumers or fix slow instance |
| Consumer group empty | `kubectl get pods` (are pods running?) | `kubectl logs` (crash reason?) | Fix crash, redeploy |
| Offset stuck on one partition | Read message at stuck offset | Check consumer logs for errors | Skip poison message or fix handler |
| Frequent rebalances | Consumer logs (revoke/assign frequency) | `session.timeout.ms` / `max.poll.interval.ms` | Increase timeouts, use sticky assignor |
| Under-replicated partitions | `--under-replicated-partitions` | Check broker health (`kubectl logs`) | Restart unhealthy broker |
| Offline partitions | `--unavailable-partitions` | Check if ISR is empty | Restart broker; if `min.isr` met, may need `unclean.leader.election` (data loss risk) |
| High produce latency | JMX request handler idle % | Disk I/O (`iostat`) | Add brokers, faster disks, tune `linger.ms` |
| Disk full | `kafka-log-dirs.sh` | Check retention settings | Reduce `retention.ms`/`retention.bytes`, add disk |
