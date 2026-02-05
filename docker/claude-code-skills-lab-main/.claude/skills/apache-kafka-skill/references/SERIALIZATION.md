# Serialization & Schema Evolution Reference

## When to Use Avro vs JSON vs Protobuf

| Format | Use When | Avoid When |
|--------|----------|------------|
| **Avro** | Schema evolution is critical, Confluent ecosystem, many consumers that evolve independently | Prototyping, simple internal tools |
| **JSON (Schema)** | Human readability matters, rapid prototyping, small teams | High throughput (5-10x larger than Avro), strict contract enforcement |
| **Protobuf** | gRPC ecosystem, strong typing across many languages, very high throughput | Small teams already using Confluent stack |
| **Plain JSON (no schema)** | Throwaway scripts, dev/test only | Production — no contract, no evolution safety |

### Size & Performance Comparison

```
Same event serialized:

JSON (pretty):    412 bytes
JSON (compact):   198 bytes
Avro (binary):     67 bytes  ← 3x smaller than compact JSON
Protobuf:          72 bytes

At 100K events/sec:
  JSON:     ~19 MB/s
  Avro:     ~6.4 MB/s   ← 3x less network, disk, replication
  Protobuf: ~6.9 MB/s
```

Avro and Protobuf include a schema ID (5 bytes) in each message. The consumer fetches the schema from the registry to deserialize.

## Schema Registry

The Schema Registry is a service that stores and validates schemas. Every schema gets a unique **ID** and a **subject** (namespace for versioning).

```
Producer                    Schema Registry              Consumer
   │                             │                          │
   ├── register schema ────────→ │                          │
   │   (or get cached ID)        │ stores version 1         │
   │                             │                          │
   ├── serialize(data, schema) → │                          │
   │   message = [magic][ID][binary data]                   │
   │                             │                          │
   │                             │ ←── fetch schema by ID ──┤
   │                             │                          │
   │                             │     deserialize(msg) ────┤
```

### Subject Naming Strategies

A **subject** is the namespace under which schema versions are tracked. The strategy determines how subjects map to topics.

| Strategy | Subject Name | Use When |
|----------|-------------|----------|
| **TopicNameStrategy** (default) | `{topic}-value` | One event type per topic |
| **RecordNameStrategy** | `{namespace}.{RecordName}` | Same schema shared across topics |
| **TopicRecordNameStrategy** | `{topic}-{namespace}.{RecordName}` | Multiple event types per topic |

```python
# TopicNameStrategy (default) — one schema per topic
# Subject: "task-events-value"

# TopicRecordNameStrategy — multiple schemas per topic
# Subject: "task-events-com.example.task.events.TaskCreated"
# Subject: "task-events-com.example.task.events.TaskCompleted"
```

**Recommendation:** Use `TopicRecordNameStrategy` when a topic carries multiple event types (e.g., all task lifecycle events in one `task-events` topic). Use the default `TopicNameStrategy` when each topic has exactly one schema.

### Compatibility Modes

Set per-subject or globally. Controls what schema changes the registry accepts.

| Mode | Rule | Use When |
|------|------|----------|
| **BACKWARD** (default) | New schema can read old data | Consumers upgrade before producers |
| **FORWARD** | Old schema can read new data | Producers upgrade before consumers |
| **FULL** | Both backward and forward | Independent upgrades, strictest safety |
| **NONE** | No checks | Development only, never production |

**BACKWARD is the default and the recommended starting point.** It means: a consumer with the new schema can still read messages written with the old schema.

```bash
# Set compatibility for a subject
curl -X PUT http://localhost:8081/config/task-events-value \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"compatibility": "BACKWARD"}'

# Test compatibility before registering
curl -X POST http://localhost:8081/compatibility/subjects/task-events-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{...}"}'
# Returns: {"is_compatible": true}
```

## Avro Schema Design

### Primitive Types

| Avro Type | Maps To | Notes |
|-----------|---------|-------|
| `null` | None/null | Used in unions for optional fields |
| `boolean` | bool | |
| `int` | 32-bit signed | |
| `long` | 64-bit signed | Use for timestamps, IDs |
| `float` | 32-bit IEEE 754 | |
| `double` | 64-bit IEEE 754 | |
| `string` | UTF-8 | |
| `bytes` | byte sequence | |

### Logical Types

Logical types add semantic meaning to primitive types.

| Logical Type | Base Type | Meaning |
|-------------|-----------|---------|
| `timestamp-millis` | `long` | UTC milliseconds since epoch |
| `timestamp-micros` | `long` | UTC microseconds since epoch |
| `date` | `int` | Days since Unix epoch |
| `time-millis` | `int` | Milliseconds since midnight |
| `uuid` | `string` | RFC 4122 UUID |
| `decimal` | `bytes` | Arbitrary precision decimal |

```json
{"name": "created_at", "type": {"type": "long", "logicalType": "timestamp-millis"}}
{"name": "event_id", "type": {"type": "string", "logicalType": "uuid"}}
{"name": "price", "type": {"type": "bytes", "logicalType": "decimal", "precision": 10, "scale": 2}}
```

### Optional Fields (Union with null)

Optional fields use a union of `null` and the actual type, with `"default": null`:

```json
{"name": "priority", "type": ["null", "string"], "default": null}
```

**Critical rule:** The `default` value must match the **first type** in the union. If the union is `["null", "string"]`, the default must be `null`. If the union is `["string", "null"]`, the default must be a string.

### Complex Types

```json
// Array with default
{"name": "labels", "type": {"type": "array", "items": "string"}, "default": []}

// Map with default
{"name": "metadata", "type": {"type": "map", "values": "string"}, "default": {}}

// Enum (add symbols only, never remove)
{"name": "status", "type": {
  "type": "enum",
  "name": "TaskStatus",
  "symbols": ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
  "default": "PENDING"
}}
```

## Schema Evolution Rules

### What You CAN Do (Backward Compatible)

| Change | Example | Why It Works |
|--------|---------|-------------|
| **Add optional field with default** | Add `"priority": ["null", "string"], default: null` | Old messages → default value fills the gap |
| **Add new enum symbol at the end** | Add `"CANCELLED"` to TaskStatus | Old consumers ignore unknown symbols (if enum has default) |
| **Add array/map field with empty default** | Add `"labels": [], default: []` | Old messages → empty collection |
| **Widen numeric type** | `int` → `long`, `float` → `double` | Old values fit in larger type |
| **Add `doc` string** | Add documentation to any field | Metadata only, no data change |

### What You CANNOT Do

| Change | Why It Breaks |
|--------|---------------|
| **Remove a field** | Old consumers expect it, get deserialization error |
| **Rename a field** | Avro matches by name — rename = remove + add |
| **Change field type** | `string` → `int` is not compatible |
| **Remove enum symbol** | Old data may contain the removed symbol |
| **Change field from required to optional** | Changes the union type |
| **Add required field (no default)** | Old messages don't have it, deserialization fails |

### Evolution Workflow

```
1. Write new schema version
2. Test compatibility against latest version:
     curl -X POST .../compatibility/subjects/{subject}/versions/latest
3. If compatible → register:
     curl -X POST .../subjects/{subject}/versions
4. Update producer code to populate new fields
5. Deploy producer
6. Update consumer code to read new fields (with fallback to default)
7. Deploy consumer

Order for BACKWARD compatibility:
  Deploy consumers first → then producers
  (Consumers can already handle old AND new data)
```

## Python: Schema Registry Integration

### Producer with Avro Serialization

```python
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
import uuid, time

schema_registry = SchemaRegistryClient({"url": "http://localhost:8081"})

task_created_schema = """{
  "type": "record",
  "name": "TaskCreated",
  "namespace": "com.example.task.events",
  "fields": [
    {"name": "task_id", "type": "string"},
    {"name": "title", "type": "string"},
    {"name": "assignee", "type": "string"},
    {"name": "created_at", "type": {"type": "long", "logicalType": "timestamp-millis"}},
    {"name": "priority", "type": ["null", "string"], "default": null}
  ]
}"""

avro_serializer = AvroSerializer(
    schema_registry,
    task_created_schema,
    conf={"auto.register.schemas": True},
)

producer = SerializingProducer({
    "bootstrap.servers": "localhost:9092",
    "acks": "all",
    "enable.idempotence": True,
    "value.serializer": avro_serializer,
})

event = {
    "task_id": str(uuid.uuid4()),
    "title": "Review PR #42",
    "assignee": "alice",
    "created_at": int(time.time() * 1000),
    "priority": "high",
}

producer.produce(topic="task-events", key=event["task_id"], value=event)
producer.flush()
```

### Consumer with Avro Deserialization

```python
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer

schema_registry = SchemaRegistryClient({"url": "http://localhost:8081"})
avro_deserializer = AvroDeserializer(schema_registry)

consumer = DeserializingConsumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "task-processor",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "value.deserializer": avro_deserializer,
})

consumer.subscribe(["task-events"])

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        continue

    event = msg.value()  # Dict — already deserialized by AvroDeserializer
    # Safe to access new fields with .get() — returns default if absent
    print(f"Task: {event['task_id']}, Priority: {event.get('priority', 'normal')}")
    consumer.commit(asynchronous=False)
```

## Java: Schema Registry Integration

### Producer

```java
import io.confluent.kafka.serializers.KafkaAvroSerializer;
import org.apache.avro.generic.GenericData;
import org.apache.avro.generic.GenericRecord;
import org.apache.avro.Schema;
import org.apache.kafka.clients.producer.*;

Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("key.serializer", "org.apache.kafka.common.serialization.StringSerializer");
props.put("value.serializer", KafkaAvroSerializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");
props.put("acks", "all");
props.put("enable.idempotence", true);

Schema schema = new Schema.Parser().parse(schemaString);
GenericRecord record = new GenericData.Record(schema);
record.put("task_id", "abc-123");
record.put("title", "Review PR");
record.put("assignee", "alice");
record.put("created_at", System.currentTimeMillis());
record.put("priority", "high");

KafkaProducer<String, GenericRecord> producer = new KafkaProducer<>(props);
producer.send(new ProducerRecord<>("task-events", "abc-123", record));
producer.flush();
```

### Consumer

```java
import io.confluent.kafka.serializers.KafkaAvroDeserializer;
import org.apache.avro.generic.GenericRecord;

Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "task-processor");
props.put("key.deserializer", "org.apache.kafka.common.serialization.StringDeserializer");
props.put("value.deserializer", KafkaAvroDeserializer.class.getName());
props.put("schema.registry.url", "http://localhost:8081");
props.put("auto.offset.reset", "earliest");
props.put("enable.auto.commit", false);

KafkaConsumer<String, GenericRecord> consumer = new KafkaConsumer<>(props);
consumer.subscribe(List.of("task-events"));

while (true) {
    ConsumerRecords<String, GenericRecord> records = consumer.poll(Duration.ofMillis(1000));
    for (ConsumerRecord<String, GenericRecord> record : records) {
        GenericRecord event = record.value();
        System.out.println("Task: " + event.get("task_id"));
        // New optional fields return null if absent in old messages
        Object priority = event.get("priority");
    }
    consumer.commitSync();
}
```

## Schema Registry Docker Compose

```yaml
services:
  schema-registry:
    image: confluentinc/cp-schema-registry:7.6.0
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: broker:29092
      SCHEMA_REGISTRY_LISTENERS: http://0.0.0.0:8081
```

## Schema Registry REST API

```bash
# List subjects
curl http://localhost:8081/subjects

# Get latest schema for a subject
curl http://localhost:8081/subjects/task-events-value/versions/latest

# Register a new schema
curl -X POST http://localhost:8081/subjects/task-events-value/versions \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{\"type\":\"record\",\"name\":\"TaskCreated\",...}"}'

# Test compatibility
curl -X POST http://localhost:8081/compatibility/subjects/task-events-value/versions/latest \
  -H "Content-Type: application/vnd.schemaregistry.v1+json" \
  -d '{"schema": "{...}"}'

# Get schema by ID (what consumers use)
curl http://localhost:8081/schemas/ids/1

# Delete subject (soft delete)
curl -X DELETE http://localhost:8081/subjects/task-events-value
```
