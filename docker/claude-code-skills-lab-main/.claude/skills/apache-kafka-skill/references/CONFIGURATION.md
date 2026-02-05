# Kafka Configuration Reference

## Broker Configuration

### Essential Settings

```properties
# Identity
node.id=1
process.roles=broker,controller

# Network
listeners=PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
advertised.listeners=PLAINTEXT://broker1.example.com:9092
listener.security.protocol.map=PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT
controller.listener.names=CONTROLLER
inter.broker.listener.name=PLAINTEXT

# KRaft
controller.quorum.voters=1@broker1:9093,2@broker2:9093,3@broker3:9093

# Storage
log.dirs=/var/kafka/data
```

### Topic Defaults

```properties
num.partitions=6
default.replication.factor=3
min.insync.replicas=2
auto.create.topics.enable=false
unclean.leader.election.enable=false
```

### Retention

```properties
log.retention.hours=168                    # 7 days
log.retention.bytes=-1                     # Unlimited
log.segment.bytes=1073741824               # 1 GB
log.cleanup.policy=delete                  # delete | compact | delete,compact
log.retention.check.interval.ms=300000     # 5 minutes
```

### Performance

```properties
num.network.threads=8
num.io.threads=16
num.replica.fetchers=4
socket.send.buffer.bytes=102400
socket.receive.buffer.bytes=102400
socket.request.max.bytes=104857600
message.max.bytes=1048576
replica.fetch.max.bytes=10485760
```

### Compression

```properties
compression.type=producer    # producer | none | gzip | snappy | lz4 | zstd
```

## Producer Configuration

| Property | Default | Range | Description |
|----------|---------|-------|-------------|
| `bootstrap.servers` | — | — | Broker list |
| `acks` | `all` | 0, 1, all | Acknowledgment level |
| `retries` | 2147483647 | ≥0 | Retry count |
| `retry.backoff.ms` | 100 | ≥0 | Retry backoff |
| `batch.size` | 16384 | ≥0 | Max batch bytes |
| `linger.ms` | 0 | ≥0 | Batch wait time |
| `buffer.memory` | 33554432 | ≥0 | Total buffer memory |
| `max.block.ms` | 60000 | ≥0 | Max time send() blocks |
| `max.request.size` | 1048576 | ≥0 | Max request bytes |
| `max.in.flight.requests.per.connection` | 5 | ≥1 | Concurrent requests |
| `compression.type` | `none` | none/gzip/snappy/lz4/zstd | Compression |
| `enable.idempotence` | true | — | Idempotent producer |
| `transactional.id` | null | — | Enables transactions |
| `delivery.timeout.ms` | 120000 | ≥0 | Max delivery time |
| `request.timeout.ms` | 30000 | ≥0 | Request timeout |

### Tuning Profiles

```properties
# High throughput
linger.ms=20
batch.size=65536
compression.type=lz4
buffer.memory=67108864
max.in.flight.requests.per.connection=5

# Low latency
linger.ms=0
batch.size=16384
acks=1

# High reliability
acks=all
enable.idempotence=true
retries=2147483647
max.in.flight.requests.per.connection=5
delivery.timeout.ms=300000
```

## Consumer Configuration

| Property | Default | Range | Description |
|----------|---------|-------|-------------|
| `bootstrap.servers` | — | — | Broker list |
| `group.id` | — | — | Consumer group ID |
| `auto.offset.reset` | `latest` | earliest/latest/none | Offset reset policy |
| `enable.auto.commit` | true | — | Auto-commit offsets |
| `auto.commit.interval.ms` | 5000 | ≥0 | Auto-commit interval |
| `max.poll.records` | 500 | ≥1 | Max records per poll |
| `max.poll.interval.ms` | 300000 | ≥1 | Max poll interval |
| `session.timeout.ms` | 45000 | — | Session timeout |
| `heartbeat.interval.ms` | 3000 | — | Heartbeat interval |
| `fetch.min.bytes` | 1 | ≥0 | Min fetch size |
| `fetch.max.bytes` | 52428800 | ≥0 | Max fetch size |
| `fetch.max.wait.ms` | 500 | ≥0 | Max fetch wait |
| `max.partition.fetch.bytes` | 1048576 | ≥0 | Max per-partition fetch |
| `isolation.level` | `read_uncommitted` | read_uncommitted/read_committed | Transaction isolation |
| `partition.assignment.strategy` | Range,CooperativeSticky | — | Assignment strategy |
| `group.instance.id` | null | — | Static group membership |

### Tuning Profiles

```properties
# High throughput batch processing
fetch.min.bytes=1048576
fetch.max.wait.ms=500
max.poll.records=1000
max.poll.interval.ms=600000

# Low latency
fetch.min.bytes=1
fetch.max.wait.ms=100
max.poll.records=100

# Stable consumer group (rolling restarts)
group.instance.id=consumer-host-1
session.timeout.ms=300000
heartbeat.interval.ms=10000
```

## Kafka Streams Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `application.id` | — | Application identifier |
| `bootstrap.servers` | — | Broker list |
| `num.stream.threads` | 1 | Processing threads |
| `processing.guarantee` | `at_least_once` | `at_least_once` or `exactly_once_v2` |
| `state.dir` | `/tmp/kafka-streams` | State store directory |
| `cache.max.bytes.buffering` | 10485760 | Record cache size |
| `commit.interval.ms` | 30000 | Commit interval |
| `replication.factor` | -1 | Internal topic replication |
| `num.standby.replicas` | 0 | Standby replicas for HA |
| `topology.optimization` | `none` | `none` or `all` |
| `default.key.serde` | — | Default key SerDe |
| `default.value.serde` | — | Default value SerDe |

## Kafka Connect Configuration

### Worker Settings

```properties
bootstrap.servers=localhost:9092
group.id=connect-cluster
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter.schemas.enable=false

config.storage.topic=connect-configs
offset.storage.topic=connect-offsets
status.storage.topic=connect-status

config.storage.replication.factor=3
offset.storage.replication.factor=3
status.storage.replication.factor=3

plugin.path=/usr/share/java,/opt/connectors

# Error handling
errors.tolerance=all
errors.deadletterqueue.topic.name=connect-dlq
errors.deadletterqueue.topic.replication.factor=3
```

## Topic-Level Configuration

Override broker defaults per topic:

```bash
# Create with config
bin/kafka-topics.sh --create --topic my-topic \
  --bootstrap-server localhost:9092 \
  --partitions 12 \
  --replication-factor 3 \
  --config retention.ms=86400000 \
  --config cleanup.policy=compact \
  --config min.insync.replicas=2 \
  --config max.message.bytes=2097152 \
  --config compression.type=zstd

# Alter config
bin/kafka-configs.sh --alter --entity-type topics --entity-name my-topic \
  --add-config retention.ms=172800000 \
  --bootstrap-server localhost:9092

# Describe config
bin/kafka-configs.sh --describe --entity-type topics --entity-name my-topic \
  --bootstrap-server localhost:9092
```

| Property | Description |
|----------|-------------|
| `retention.ms` | Retention time |
| `retention.bytes` | Retention size per partition |
| `cleanup.policy` | `delete`, `compact`, or `delete,compact` |
| `min.insync.replicas` | Min ISR for acks=all |
| `max.message.bytes` | Max message size |
| `compression.type` | Topic-level compression |
| `segment.bytes` | Log segment size |
| `segment.ms` | Log segment roll time |
| `message.timestamp.type` | `CreateTime` or `LogAppendTime` |
