# Kafka Connect Reference

Kafka Connect is a framework for streaming data between Kafka and external systems using connectors.

## When to Use Kafka Connect vs Custom Code

### Use Kafka Connect When

| Scenario | Why Connect Wins |
|----------|-----------------|
| **Database → Kafka (CDC)** | Debezium reads the WAL — no application changes, captures all mutations including deletes |
| **Database → Kafka (polling)** | JDBC Source connector handles offset tracking, schema detection, incremental loads |
| **Kafka → Database** | JDBC Sink handles upserts, auto-create tables, schema evolution — no custom consumer needed |
| **Kafka → S3/GCS/ADLS** | S3 Sink handles partitioning by time, format conversion (Parquet, Avro, JSON), exactly-once via offset tracking |
| **Kafka → Elasticsearch/OpenSearch** | ES Sink handles indexing, key-based upserts, schema mapping |
| **Kafka ↔ another Kafka cluster** | MirrorMaker 2 (built on Connect) handles cross-cluster replication |
| **Any standard data pipeline** | 200+ pre-built connectors on Confluent Hub — proven, maintained, tested at scale |

### Write Custom Code When

| Scenario | Why Custom Wins |
|----------|----------------|
| **Complex business logic during transfer** | Connect SMTs are limited to single-message transforms — no joins, aggregations, or lookups |
| **Non-standard protocol** | Proprietary API, custom binary format, or system with no existing connector |
| **Low-latency event processing** | Connect adds overhead (worker framework, REST API, offset management) — a direct consumer is faster |
| **Application-level side effects** | Sending emails, calling APIs, triggering workflows — these need application code with error handling |
| **Transactional consistency** | Consumer + DB in same transaction (dedup table pattern) — Connect can't coordinate external transactions |

### Decision Flowchart

```
Is there a pre-built connector for your source/sink?
  │
  ├─ YES → Does the connector meet your requirements?
  │         │
  │         ├─ YES → Use Kafka Connect
  │         │        (configure, don't code)
  │         │
  │         └─ NO → Can an SMT bridge the gap?
  │                  │
  │                  ├─ YES → Use Connect + SMT
  │                  │
  │                  └─ NO → Need joins/aggregation? → Kafka Streams
  │                          Need side effects?     → Custom consumer
  │
  └─ NO → Is the integration a simple data pipeline?
           │
           ├─ YES → Write a custom connector (Source/SinkConnector API)
           │        Reuse Connect's offset tracking, scaling, monitoring
           │
           └─ NO → Write a custom producer/consumer
                   Full control over logic, transactions, error handling
```

### Connect vs Custom: Side-by-Side

| Aspect | Kafka Connect | Custom Producer/Consumer |
|--------|--------------|------------------------|
| **Setup** | JSON config, REST API | Write and deploy application code |
| **Scaling** | Change `tasks.max`, workers auto-distribute | Manually scale application instances |
| **Offset tracking** | Automatic (internal topics) | Manual (`commitSync`/`commitAsync`) |
| **Fault tolerance** | Task restart, DLQ for bad records | You handle retries, DLQ, circuit breakers |
| **Schema evolution** | Converters + Schema Registry built in | You integrate `SerializingProducer`/`DeserializingConsumer` |
| **Monitoring** | JMX metrics, REST status endpoint | You instrument with your own metrics |
| **Transformations** | SMTs (single message only) | Arbitrary code — joins, aggregations, API calls |
| **Exactly-once** | Source connectors support it natively | You implement with transactions or idempotent consumers |
| **Deployment** | Connect cluster (separate JVM) or Strimzi CRD | Your application's deployment pipeline |
| **Latency** | ~50-500ms (poll interval + batching) | ~2-50ms (direct produce/consume) |

## Architecture

```
External System → Source Connector → Kafka Topic → Sink Connector → External System

Connect Cluster:
  Worker 1: [Task 1, Task 2]
  Worker 2: [Task 3, Task 4]
  Worker 3: [Task 5]
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Connector** | Defines the integration logic (source or sink) |
| **Task** | Unit of work; connectors split work into tasks for parallelism |
| **Worker** | JVM process that runs connectors and tasks |
| **Converter** | Serializes/deserializes data (JSON, Avro, Protobuf) |
| **Transform (SMT)** | Single Message Transform applied inline |

## Deployment Modes

### Standalone Mode

Single worker, useful for development/testing:

```bash
bin/connect-standalone.sh config/connect-standalone.properties \
  config/my-connector.properties
```

```properties
# connect-standalone.properties
bootstrap.servers=localhost:9092
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
offset.storage.file.filename=/tmp/connect.offsets
```

### Distributed Mode

Multiple workers for production:

```bash
bin/connect-distributed.sh config/connect-distributed.properties
```

```properties
# connect-distributed.properties
bootstrap.servers=localhost:9092
group.id=connect-cluster
key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
config.storage.topic=connect-configs
offset.storage.topic=connect-offsets
status.storage.topic=connect-status
config.storage.replication.factor=3
offset.storage.replication.factor=3
status.storage.replication.factor=3
```

## REST API

All connector management is done via REST API in distributed mode:

```bash
# List connectors
curl http://localhost:8083/connectors

# Create connector
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-connector",
    "config": {
      "connector.class": "org.apache.kafka.connect.file.FileStreamSourceConnector",
      "tasks.max": "1",
      "file": "/tmp/input.txt",
      "topic": "file-topic"
    }
  }'

# Get connector status
curl http://localhost:8083/connectors/my-connector/status

# Get connector config
curl http://localhost:8083/connectors/my-connector/config

# Update connector config
curl -X PUT http://localhost:8083/connectors/my-connector/config \
  -H "Content-Type: application/json" \
  -d '{ "connector.class": "...", "tasks.max": "2" }'

# Pause / Resume / Restart / Delete
curl -X PUT http://localhost:8083/connectors/my-connector/pause
curl -X PUT http://localhost:8083/connectors/my-connector/resume
curl -X POST http://localhost:8083/connectors/my-connector/restart
curl -X DELETE http://localhost:8083/connectors/my-connector

# Restart a specific task
curl -X POST http://localhost:8083/connectors/my-connector/tasks/0/restart

# List installed connector plugins
curl http://localhost:8083/connector-plugins
```

## Common Connectors

### JDBC Source Connector

```json
{
  "name": "jdbc-source",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "connection.url": "jdbc:postgresql://localhost:5432/mydb",
    "connection.user": "user",
    "connection.password": "password",
    "table.whitelist": "orders,customers",
    "mode": "incrementing",
    "incrementing.column.name": "id",
    "topic.prefix": "db-",
    "tasks.max": "2",
    "poll.interval.ms": "5000"
  }
}
```

### JDBC Sink Connector

```json
{
  "name": "jdbc-sink",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "connection.url": "jdbc:postgresql://localhost:5432/warehouse",
    "connection.user": "user",
    "connection.password": "password",
    "topics": "db-orders",
    "insert.mode": "upsert",
    "pk.mode": "record_value",
    "pk.fields": "id",
    "auto.create": "true",
    "auto.evolve": "true",
    "tasks.max": "2"
  }
}
```

### Debezium CDC (MySQL)

```json
{
  "name": "mysql-cdc",
  "config": {
    "connector.class": "io.debezium.connector.mysql.MySqlConnector",
    "database.hostname": "localhost",
    "database.port": "3306",
    "database.user": "debezium",
    "database.password": "password",
    "database.server.id": "1",
    "topic.prefix": "cdc",
    "database.include.list": "mydb",
    "table.include.list": "mydb.orders,mydb.customers",
    "schema.history.internal.kafka.bootstrap.servers": "localhost:9092",
    "schema.history.internal.kafka.topic": "schema-changes",
    "include.schema.changes": "true"
  }
}
```

### Elasticsearch Sink

```json
{
  "name": "es-sink",
  "config": {
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "connection.url": "http://localhost:9200",
    "topics": "orders",
    "type.name": "_doc",
    "key.ignore": "false",
    "schema.ignore": "true",
    "tasks.max": "2"
  }
}
```

### S3 Sink Connector

```json
{
  "name": "s3-sink",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "s3.bucket.name": "my-kafka-bucket",
    "s3.region": "us-east-1",
    "topics": "events",
    "flush.size": "1000",
    "rotate.interval.ms": "600000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd/'hour'=HH",
    "locale": "en-US",
    "timezone": "UTC",
    "partition.duration.ms": "3600000",
    "tasks.max": "4"
  }
}
```

## Single Message Transforms (SMTs)

Apply lightweight transformations inline:

```json
{
  "transforms": "addTimestamp,maskField",
  "transforms.addTimestamp.type": "org.apache.kafka.connect.transforms.InsertField$Value",
  "transforms.addTimestamp.timestamp.field": "processed_at",
  "transforms.maskField.type": "org.apache.kafka.connect.transforms.MaskField$Value",
  "transforms.maskField.fields": "ssn,credit_card"
}
```

### Common SMTs

| Transform | Description |
|-----------|-------------|
| `InsertField` | Add fields (static value, timestamp, topic, partition, offset) |
| `ReplaceField` | Include, exclude, or rename fields |
| `MaskField` | Replace field values with type-valid null |
| `ValueToKey` | Copy fields from value to key |
| `ExtractField` | Extract a single field from struct |
| `TimestampConverter` | Convert between timestamp formats |
| `Flatten` | Flatten nested structs |
| `HoistField` | Wrap data in a struct or map |
| `RegexRouter` | Modify topic name using regex |
| `SetSchemaMetadata` | Set schema name or version |

## Dead Letter Queue

Route failed records instead of stopping the connector:

```json
{
  "errors.tolerance": "all",
  "errors.deadletterqueue.topic.name": "my-connector-dlq",
  "errors.deadletterqueue.topic.replication.factor": "3",
  "errors.deadletterqueue.context.headers.enable": "true",
  "errors.log.enable": "true",
  "errors.log.include.messages": "true"
}
```

## Converters

| Converter | Use Case |
|-----------|----------|
| `JsonConverter` | Simple JSON (with or without schema) |
| `AvroConverter` | Schema Registry + Avro (recommended for production) |
| `ProtobufConverter` | Schema Registry + Protobuf |
| `StringConverter` | Plain string data |
| `ByteArrayConverter` | Raw bytes passthrough |

```properties
# JSON without embedded schema
key.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=false
value.converter=org.apache.kafka.connect.json.JsonConverter
value.converter.schemas.enable=false

# Avro with Schema Registry
key.converter=io.confluent.connect.avro.AvroConverter
key.converter.schema.registry.url=http://localhost:8081
value.converter=io.confluent.connect.avro.AvroConverter
value.converter.schema.registry.url=http://localhost:8081
```

## Docker Compose with Connect

```yaml
services:
  kafka-connect:
    image: confluentinc/cp-kafka-connect:7.6.0
    ports:
      - "8083:8083"
    environment:
      CONNECT_BOOTSTRAP_SERVERS: broker:29092
      CONNECT_REST_PORT: 8083
      CONNECT_GROUP_ID: connect-cluster
      CONNECT_CONFIG_STORAGE_TOPIC: connect-configs
      CONNECT_OFFSET_STORAGE_TOPIC: connect-offsets
      CONNECT_STATUS_STORAGE_TOPIC: connect-status
      CONNECT_KEY_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      CONNECT_CONFIG_STORAGE_REPLICATION_FACTOR: 1
      CONNECT_OFFSET_STORAGE_REPLICATION_FACTOR: 1
      CONNECT_STATUS_STORAGE_REPLICATION_FACTOR: 1
      CONNECT_PLUGIN_PATH: /usr/share/java,/usr/share/confluent-hub-components
    command:
      - bash
      - -c
      - |
        confluent-hub install --no-prompt debezium/debezium-connector-mysql:latest
        confluent-hub install --no-prompt confluentinc/kafka-connect-jdbc:latest
        /etc/confluent/docker/run
```

## Strimzi: KafkaConnect and KafkaConnector CRDs

On Kubernetes with Strimzi, you manage Connect clusters and individual connectors declaratively via CRDs instead of the REST API.

### KafkaConnect CR (Deploy Connect Workers)

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnect
metadata:
  name: my-connect
  namespace: kafka
  annotations:
    strimzi.io/use-connector-resources: "true"  # Enable KafkaConnector CRDs
spec:
  version: 3.9.0
  replicas: 3
  bootstrapServers: prod-cluster-kafka-bootstrap:9093
  tls:
    trustedCertificates:
      - secretName: prod-cluster-cluster-ca-cert
        certificate: ca.crt
  authentication:
    type: scram-sha-512
    username: connect-worker
    passwordSecret:
      secretName: connect-worker
      password: password
  config:
    group.id: connect-cluster
    offset.storage.topic: connect-offsets
    config.storage.topic: connect-configs
    status.storage.topic: connect-status
    config.storage.replication.factor: 3
    offset.storage.replication.factor: 3
    status.storage.replication.factor: 3
    key.converter: org.apache.kafka.connect.json.JsonConverter
    value.converter: io.confluent.connect.avro.AvroConverter
    value.converter.schema.registry.url: http://schema-registry:8081
  build:
    output:
      type: docker
      image: my-registry.io/kafka-connect-custom:latest
      pushSecret: registry-credentials
    plugins:
      - name: debezium-postgres
        artifacts:
          - type: tgz
            url: https://repo1.maven.org/maven2/io/debezium/debezium-connector-postgres/2.5.0.Final/debezium-connector-postgres-2.5.0.Final-plugin.tar.gz
      - name: confluent-s3
        artifacts:
          - type: zip
            url: https://d1i4a15mxbxib1.cloudfront.net/api/plugins/confluentinc/kafka-connect-s3/versions/10.5.7/confluentinc-kafka-connect-s3-10.5.7.zip
  resources:
    requests:
      memory: 2Gi
      cpu: 1000m
    limits:
      memory: 4Gi
      cpu: 2000m
```

The `build` section tells Strimzi to build a custom Connect image with plugins baked in — no runtime `confluent-hub install` needed.

### KafkaConnector CR (Deploy Individual Connectors)

With `strimzi.io/use-connector-resources: "true"` on the KafkaConnect CR, you manage connectors as Kubernetes resources instead of via REST API:

```yaml
# Debezium PostgreSQL CDC Source
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: postgres-cdc-source
  namespace: kafka
  labels:
    strimzi.io/cluster: my-connect  # Must match KafkaConnect name
spec:
  class: io.debezium.connector.postgresql.PostgresConnector
  tasksMax: 1
  config:
    database.hostname: postgres.default.svc
    database.port: 5432
    database.user: debezium
    database.password: ${secrets:kafka/postgres-credentials:password}
    database.dbname: orders_db
    topic.prefix: cdc
    table.include.list: public.orders,public.customers
    plugin.name: pgoutput
    slot.name: debezium_orders
    publication.name: dbz_publication
    schema.history.internal.kafka.bootstrap.servers: prod-cluster-kafka-bootstrap:9093
    schema.history.internal.kafka.topic: schema-changes
    errors.tolerance: all
    errors.deadletterqueue.topic.name: cdc-dlq
    errors.deadletterqueue.topic.replication.factor: 3
---
# S3 Sink for archival
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaConnector
metadata:
  name: s3-archive-sink
  namespace: kafka
  labels:
    strimzi.io/cluster: my-connect
spec:
  class: io.confluent.connect.s3.S3SinkConnector
  tasksMax: 4
  config:
    topics: cdc.public.orders
    s3.bucket.name: orders-archive
    s3.region: us-east-1
    flush.size: 10000
    rotate.interval.ms: 3600000
    storage.class: io.confluent.connect.s3.storage.S3Storage
    format.class: io.confluent.connect.s3.format.parquet.ParquetFormat
    partitioner.class: io.confluent.connect.storage.partitioner.TimeBasedPartitioner
    path.format: "'year'=YYYY/'month'=MM/'day'=dd"
    locale: en-US
    timezone: UTC
```

### KafkaConnector vs REST API

| Aspect | KafkaConnector CRD | REST API |
|--------|-------------------|----------|
| **GitOps** | YAML in git, `kubectl apply` | curl commands or scripts |
| **Lifecycle** | Managed by Strimzi operator | Manual via HTTP calls |
| **Secrets** | Reference Kubernetes Secrets (`${secrets:...}`) | Plaintext in JSON config or external vault |
| **Status** | `kubectl describe kafkaconnector` | `curl .../status` |
| **Scaling** | Edit `tasksMax` in YAML, apply | `PUT` config with new `tasks.max` |
| **Rollback** | `git revert` + `kubectl apply` | Manual reconfiguration |

**Recommendation:** Use KafkaConnector CRDs on Kubernetes for GitOps, auditability, and consistent deployment. Use the REST API for non-Kubernetes deployments or quick ad-hoc debugging.

### Useful Connect Commands (Strimzi)

```bash
# List all connectors
kubectl get kafkaconnectors -n kafka

# Check connector status
kubectl describe kafkaconnector postgres-cdc-source -n kafka

# View Connect worker logs
kubectl logs deployment/my-connect-connect -n kafka

# Restart a connector (delete and re-create)
kubectl annotate kafkaconnector postgres-cdc-source \
  strimzi.io/restart=true -n kafka

# Restart a specific task
kubectl annotate kafkaconnector postgres-cdc-source \
  strimzi.io/restart-task=0 -n kafka

# Pause a connector
kubectl annotate kafkaconnector postgres-cdc-source \
  strimzi.io/pause-reconciliation=true -n kafka
```

## Common Connect Patterns

### CDC → Stream Processing → Sink

```
PostgreSQL ──Debezium──→ [cdc.orders] ──Kafka Streams──→ [enriched-orders] ──S3 Sink──→ Data Lake
                                        (join with customers,
                                         compute metrics)
```

Use Connect for the data movement (source + sink), Kafka Streams for the transformation logic.

### Multi-Sink Fan-Out

```
[order-events] ──→ Elasticsearch Sink  (search index)
               ──→ JDBC Sink           (reporting DB)
               ──→ S3 Sink             (long-term archive)
```

One topic, three independent sink connectors. Each tracks its own offsets. Adding a new sink requires zero changes to the producer or other sinks.

### Hybrid: Connect Source + Custom Consumer

```
PostgreSQL ──Debezium──→ [cdc.orders] ──→ Custom consumer
                                          (send email, call API,
                                           complex business logic)
```

Use Connect for reliable CDC (it handles WAL reading, offset tracking, schema history). Use a custom consumer for the business logic that Connect can't express.
