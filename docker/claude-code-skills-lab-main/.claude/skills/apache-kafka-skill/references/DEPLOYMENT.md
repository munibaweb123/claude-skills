# Kafka Deployment Reference

## KRaft Mode (Production)

### Dedicated Controllers + Brokers

```
Controller Nodes (3):        Broker Nodes (3+):
  controller-1 (node.id=1)    broker-1 (node.id=4)
  controller-2 (node.id=2)    broker-2 (node.id=5)
  controller-3 (node.id=3)    broker-3 (node.id=6)
```

#### Controller Configuration

```properties
# controller.properties
node.id=1
process.roles=controller
controller.quorum.voters=1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
listeners=CONTROLLER://0.0.0.0:9093
controller.listener.names=CONTROLLER
listener.security.protocol.map=CONTROLLER:SSL

log.dirs=/var/kafka/kraft-controller-logs
```

#### Broker Configuration

```properties
# broker.properties
node.id=4
process.roles=broker
controller.quorum.voters=1@controller-1:9093,2@controller-2:9093,3@controller-3:9093
listeners=PLAINTEXT://0.0.0.0:9092,SSL://0.0.0.0:9093
advertised.listeners=PLAINTEXT://broker-1:9092,SSL://broker-1:9093
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT

log.dirs=/var/kafka/data
broker.rack=az-1
```

### Combined Mode (Small Clusters)

```properties
node.id=1
process.roles=broker,controller
controller.quorum.voters=1@node-1:9093,2@node-2:9093,3@node-3:9093
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=PLAINTEXT://node-1:9092
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT
log.dirs=/var/kafka/data
```

### Initialize KRaft Storage

```bash
KAFKA_CLUSTER_ID="$(bin/kafka-storage.sh random-uuid)"

# Run on each node
bin/kafka-storage.sh format \
  -t $KAFKA_CLUSTER_ID \
  -c config/kraft/server.properties
```

## Docker Compose (Multi-Broker)

```yaml
services:
  broker-1:
    image: apache/kafka:3.9.0
    container_name: broker-1
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@broker-1:29093,2@broker-2:29093,3@broker-3:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://broker-1:29092,EXTERNAL://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk

  broker-2:
    image: apache/kafka:3.9.0
    container_name: broker-2
    ports:
      - "9093:9092"
    environment:
      KAFKA_NODE_ID: 2
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@broker-1:29093,2@broker-2:29093,3@broker-3:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://broker-2:29092,EXTERNAL://localhost:9093
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk

  broker-3:
    image: apache/kafka:3.9.0
    container_name: broker-3
    ports:
      - "9094:9092"
    environment:
      KAFKA_NODE_ID: 3
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@broker-1:29093,2@broker-2:29093,3@broker-3:29093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,EXTERNAL://0.0.0.0:9092
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://broker-3:29092,EXTERNAL://localhost:9094
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,EXTERNAL:PLAINTEXT
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_LOG_DIRS: /tmp/kraft-combined-logs
      CLUSTER_ID: MkU3OEVBNTcwNTJENDM2Qk
```

## Broker Tuning

### Storage

```properties
# Multiple log directories (separate disks)
log.dirs=/disk1/kafka-logs,/disk2/kafka-logs

# Segment configuration
log.segment.bytes=1073741824         # 1 GB segment files
log.segment.ms=604800000             # Roll segment every 7 days
log.retention.hours=168              # Retain for 7 days
log.retention.bytes=-1               # No size limit
log.cleanup.policy=delete            # delete or compact

# Flush (prefer OS page cache defaults)
log.flush.interval.messages=10000
log.flush.interval.ms=1000
```

### Network & Threads

```properties
num.network.threads=8                # Network I/O threads
num.io.threads=16                    # Disk I/O threads
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600   # 100 MB max request

# Request handling
num.replica.fetchers=4
replica.fetch.min.bytes=1
replica.fetch.max.bytes=10485760
```

### Memory

```bash
# JVM settings (kafka-server-start.sh or KAFKA_HEAP_OPTS)
export KAFKA_HEAP_OPTS="-Xms6g -Xmx6g"
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC -XX:MaxGCPauseMillis=20 \
  -XX:InitiatingHeapOccupancyPercent=35 -XX:+ExplicitGCInvokesConcurrent"
```

**Rule of thumb:** Allocate 6-8 GB heap to Kafka, leave the rest for OS page cache.

## Producer Tuning: Latency vs Throughput

The producer batches messages before sending. Three settings control the trade-off:

```
Producer internal buffer:
  ┌─────────────────────────────────────────┐
  │  batch for partition 0                  │
  │  [msg][msg][msg][msg]___________        │  ← batch.size (bytes)
  │                                         │
  │  batch for partition 1                  │
  │  [msg][msg]_____________________        │
  └─────────────────────────────────────────┘
         │                             │
    buffer.memory                 linger.ms timer
    (total buffer)               (wait before send)
```

**How batching works:**
1. Producer appends message to the batch for the target partition
2. If the batch reaches `batch.size` → send immediately
3. If `linger.ms` expires since the first message was added → send whatever is in the batch
4. Whichever triggers first (size or time) flushes the batch

### The Three Knobs

| Setting | Default | Effect |
|---------|---------|--------|
| `linger.ms` | 0 | How long to wait for more messages before sending. 0 = send immediately (lowest latency). Higher = more batching (higher throughput) |
| `batch.size` | 16384 (16 KB) | Max bytes per batch per partition. Larger = more messages per request. Does NOT add latency — just sets the ceiling |
| `buffer.memory` | 33554432 (32 MB) | Total memory for all unsent batches. If full, `produce()` blocks (or raises `BufferError` in Python after `queue.buffering.max.ms`) |

### Tuning Profiles

#### Low Latency (real-time events, user-facing)

```python
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 0,          # Send immediately
    'batch.size': 16384,     # Default — rarely fills before linger fires
    'compression.type': 'none',  # No compression delay
})
```

- Each message sent in its own request (or very small batch)
- Higher network overhead: more requests per second
- Typical produce latency: 2-10ms

#### Balanced (most production workloads)

```python
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 5,          # Wait up to 5ms to fill batch
    'batch.size': 32768,     # 32 KB batches
    'compression.type': 'lz4',  # Fast compression
})
```

- Small delay (5ms max) allows batching multiple messages
- Compression reduces network and disk usage
- Good for 1K-100K messages/sec

#### High Throughput (bulk ingestion, log shipping, analytics)

```python
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'acks': 'all',
    'enable.idempotence': True,
    'linger.ms': 50,         # Wait up to 50ms to fill large batches
    'batch.size': 524288,    # 512 KB batches
    'buffer.memory': 67108864,  # 64 MB buffer
    'compression.type': 'zstd',  # Best compression ratio
})
```

- Large batches maximize throughput (fewer requests, better compression)
- Adds up to 50ms latency to each message
- Handles 500K+ messages/sec with fewer broker requests

### Tuning Summary

| Profile | `linger.ms` | `batch.size` | `compression.type` | Latency | Throughput |
|---------|-------------|-------------|-------------------|---------|------------|
| **Low latency** | 0 | 16 KB | none | 2-10ms | Lower |
| **Balanced** | 5 | 32 KB | lz4 | 5-15ms | Good |
| **High throughput** | 50 | 512 KB | zstd | 50-70ms | Highest |

### Compression Comparison

| Algorithm | Compression Ratio | CPU Cost | Use When |
|-----------|------------------|----------|----------|
| `none` | 1x | None | Lowest latency, small messages |
| `lz4` | ~2-3x | Low | **Default choice** — fast with good ratio |
| `snappy` | ~2x | Low | Similar to lz4, slightly worse ratio |
| `zstd` | ~3-5x | Medium | Best ratio, good for large batches and high throughput |
| `gzip` | ~3-4x | High | Avoid — slow compression, no advantage over zstd |

Compression is applied per batch. Larger batches compress better. The broker stores compressed batches as-is — consumers decompress.

### Consumer Fetch Tuning

The consumer also has batching knobs that mirror the producer:

| Setting | Default | Effect |
|---------|---------|--------|
| `fetch.min.bytes` | 1 | Broker waits until this many bytes are available before responding. Higher = more batching, more latency |
| `fetch.max.wait.ms` | 500 | Max time broker waits to fill `fetch.min.bytes` before responding anyway |
| `max.partition.fetch.bytes` | 1048576 (1 MB) | Max bytes per partition per fetch. Limits memory per poll |
| `max.poll.records` | 500 | Max records returned per `poll()`. Lower = more predictable processing time |

```python
# High-throughput consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'bulk-ingest',
    'fetch.min.bytes': 65536,      # 64 KB min before broker responds
    'fetch.max.wait.ms': 500,      # Wait up to 500ms to fill
    'max.poll.records': 1000,      # Process up to 1000 per poll
})

# Low-latency consumer
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'real-time',
    'fetch.min.bytes': 1,          # Respond immediately with any data
    'fetch.max.wait.ms': 100,      # Short wait
    'max.poll.records': 100,       # Small batches, fast processing
})
```

## Monitoring

### Key JMX Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|----------------|
| `kafka.server:type=ReplicaManager,name=UnderReplicatedPartitions` | Partitions below replication factor | > 0 |
| `kafka.server:type=ReplicaManager,name=IsrShrinksPerSec` | ISR shrink rate | Sustained > 0 |
| `kafka.server:type=BrokerTopicMetrics,name=BytesInPerSec` | Incoming bytes/sec | Near network capacity |
| `kafka.server:type=BrokerTopicMetrics,name=BytesOutPerSec` | Outgoing bytes/sec | Near network capacity |
| `kafka.network:type=RequestMetrics,name=TotalTimeMs,request=Produce` | Produce latency | p99 > 100ms |
| `kafka.network:type=RequestMetrics,name=TotalTimeMs,request=FetchConsumer` | Fetch latency | p99 > 100ms |
| `kafka.server:type=KafkaRequestHandlerPool,name=RequestHandlerAvgIdlePercent` | Handler thread idle % | < 30% |
| `kafka.controller:type=KafkaController,name=ActiveControllerCount` | Active controllers | != 1 |
| `kafka.controller:type=KafkaController,name=OfflinePartitionsCount` | Offline partitions | > 0 |
| `kafka.log:type=LogFlushStats,name=LogFlushRateAndTimeMs` | Disk flush rate/time | High values |

### Prometheus + Grafana Setup

```yaml
# docker-compose monitoring addition
  jmx-exporter:
    image: bitnami/jmx-exporter:latest
    ports:
      - "5556:5556"
    volumes:
      - ./jmx-exporter-config.yml:/etc/jmx-exporter/config.yml
    command: ["5556", "/etc/jmx-exporter/config.yml"]
```

```yaml
# jmx-exporter-config.yml
hostPort: broker-1:9999
rules:
  - pattern: kafka.server<type=(.+), name=(.+)><>Value
    name: kafka_server_$1_$2
  - pattern: kafka.network<type=(.+), name=(.+), request=(.+)><>(\w+)
    name: kafka_network_$1_$2_$4
    labels:
      request: $3
```

### Consumer Lag Monitoring

```bash
# Check consumer lag
bin/kafka-consumer-groups.sh --describe --group my-group \
  --bootstrap-server localhost:9092

# Programmatic monitoring with Burrow or kafka-lag-exporter
```

## Rolling Restart Procedure

```bash
# 1. Check cluster health
bin/kafka-metadata.sh --snapshot /var/kafka/data/__cluster_metadata-0/00000000000000000000.log \
  --cluster-id $CLUSTER_ID

# 2. For each broker (one at a time):
#    a. Stop the broker gracefully
bin/kafka-server-stop.sh

#    b. Apply changes (config, upgrade, etc.)

#    c. Start the broker
bin/kafka-server-start.sh -daemon config/kraft/server.properties

#    d. Wait for ISR recovery before proceeding to next broker
bin/kafka-topics.sh --describe --under-replicated-partitions \
  --bootstrap-server localhost:9092
# Wait until output is empty
```

## Partition Reassignment

```bash
# Generate reassignment plan
bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --topics-to-move-json-file topics.json \
  --broker-list "1,2,3" --generate

# Execute reassignment
bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json --execute

# Verify progress
bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json --verify

# Throttle replication to avoid impacting production
bin/kafka-reassign-partitions.sh --bootstrap-server localhost:9092 \
  --reassignment-json-file reassignment.json --execute \
  --throttle 50000000  # 50 MB/s
```

## Hardware Recommendations

| Component | Development | Production |
|-----------|-------------|------------|
| **CPU** | 2 cores | 8-16 cores |
| **Memory** | 4 GB | 32-64 GB (6-8 GB heap, rest for page cache) |
| **Disk** | Any SSD | Dedicated SSDs, RAID 10 or JBOD |
| **Network** | 1 GbE | 10 GbE |
| **Brokers** | 1 | 3+ across availability zones |
| **Controllers** | Combined | 3 dedicated (large clusters) |
