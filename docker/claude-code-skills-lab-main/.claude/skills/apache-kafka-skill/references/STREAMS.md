# Kafka Streams Reference

Kafka Streams is a client library for building stream processing applications on top of Kafka.

## Architecture

```
Input Topics → Topology (Source → Processors → Sink) → Output Topics
                           ↕
                      State Stores (RocksDB)
```

### Key Properties
- **No separate cluster** — runs as part of your application
- **Exactly-once processing** via transactions
- **Fault-tolerant state** backed by changelog topics
- **Elastic** — add/remove instances for scaling

## DSL API (High-Level)

### Streams and Tables

```java
import org.apache.kafka.streams.*;
import org.apache.kafka.streams.kstream.*;

Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "my-streams-app");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.String().getClass());
props.put(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.String().getClass());

StreamsBuilder builder = new StreamsBuilder();

// KStream — unbounded stream of events
KStream<String, String> stream = builder.stream("input-topic");

// KTable — changelog stream (latest value per key)
KTable<String, String> table = builder.table("config-topic");

// GlobalKTable — replicated to all instances
GlobalKTable<String, String> globalTable = builder.globalTable("lookup-topic");
```

### Stateless Operations

```java
// Filter
KStream<String, String> filtered = stream.filter(
    (key, value) -> value.contains("important"));

// Map
KStream<String, Integer> mapped = stream.mapValues(
    value -> value.length());

// FlatMap
KStream<String, String> words = stream.flatMapValues(
    value -> Arrays.asList(value.split("\\s+")));

// Branch
Map<String, KStream<String, String>> branches = stream.split(Named.as("branch-"))
    .branch((key, value) -> value.startsWith("A"), Branched.as("a"))
    .branch((key, value) -> value.startsWith("B"), Branched.as("b"))
    .defaultBranch(Branched.as("other"));

// Merge
KStream<String, String> merged = branches.get("branch-a")
    .merge(branches.get("branch-b"));

// SelectKey (re-key)
KStream<String, String> rekeyed = stream.selectKey(
    (key, value) -> extractNewKey(value));

// Peek (side effects)
stream.peek((key, value) -> logger.info("Processing: {}", key));

// To output topic
stream.to("output-topic");
```

### Stateful Operations

#### Aggregations

```java
// Count by key
KTable<String, Long> counts = stream
    .groupByKey()
    .count(Materialized.as("counts-store"));

// Reduce
KTable<String, String> reduced = stream
    .groupByKey()
    .reduce((aggValue, newValue) -> aggValue + "," + newValue);

// Aggregate with initializer
KTable<String, Long> totals = stream
    .groupByKey()
    .aggregate(
        () -> 0L,  // initializer
        (key, value, aggregate) -> aggregate + Long.parseLong(value),
        Materialized.with(Serdes.String(), Serdes.Long())
    );
```

#### Windowed Aggregations

```java
import org.apache.kafka.streams.kstream.TimeWindows;
import org.apache.kafka.streams.kstream.SessionWindows;
import java.time.Duration;

// Tumbling window (fixed, non-overlapping)
KTable<Windowed<String>, Long> tumblingCounts = stream
    .groupByKey()
    .windowedBy(TimeWindows.ofSizeWithNoGrace(Duration.ofMinutes(5)))
    .count();

// Hopping window (fixed, overlapping)
KTable<Windowed<String>, Long> hoppingCounts = stream
    .groupByKey()
    .windowedBy(TimeWindows.ofSizeAndGrace(
        Duration.ofMinutes(5), Duration.ofMinutes(1))
        .advanceBy(Duration.ofMinutes(1)))
    .count();

// Session window (activity-based)
KTable<Windowed<String>, Long> sessionCounts = stream
    .groupByKey()
    .windowedBy(SessionWindows.ofInactivityGapWithNoGrace(Duration.ofMinutes(30)))
    .count();

// Sliding window
KTable<Windowed<String>, Long> slidingCounts = stream
    .groupByKey()
    .windowedBy(SlidingWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(5)))
    .count();
```

#### Joins

```java
// Stream-Stream join (windowed)
KStream<String, String> joined = stream1.join(
    stream2,
    (v1, v2) -> v1 + "+" + v2,
    JoinWindows.ofTimeDifferenceWithNoGrace(Duration.ofMinutes(5))
);

// Stream-Table join (lookup enrichment)
KStream<String, String> enriched = stream.join(
    table,
    (streamValue, tableValue) -> streamValue + " [" + tableValue + "]"
);

// Stream-GlobalKTable join (broadcast join)
KStream<String, String> globalJoined = stream.join(
    globalTable,
    (key, value) -> key,  // key mapper
    (streamValue, globalValue) -> streamValue + " {" + globalValue + "}"
);

// Table-Table join
KTable<String, String> tableJoined = table1.join(
    table2,
    (v1, v2) -> v1 + "|" + v2
);
```

## Processor API (Low-Level)

```java
Topology topology = new Topology();

topology.addSource("source", "input-topic")
    .addProcessor("process", () -> new Processor<String, String, String, String>() {
        private ProcessorContext<String, String> context;
        private KeyValueStore<String, Long> store;

        @Override
        public void init(ProcessorContext<String, String> context) {
            this.context = context;
            this.store = context.getStateStore("my-store");
            // Schedule punctuation
            context.schedule(Duration.ofSeconds(30),
                PunctuationType.WALL_CLOCK_TIME, this::punctuate);
        }

        @Override
        public void process(Record<String, String> record) {
            Long count = store.get(record.key());
            count = (count == null) ? 1L : count + 1;
            store.put(record.key(), count);
            context.forward(record.withValue(count.toString()));
        }

        private void punctuate(long timestamp) {
            // Periodic processing
        }
    }, "source")
    .addStateStore(
        Stores.keyValueStoreBuilder(
            Stores.persistentKeyValueStore("my-store"),
            Serdes.String(), Serdes.Long()),
        "process")
    .addSink("sink", "output-topic", "process");
```

## Interactive Queries

Query state stores from outside the stream processing topology:

```java
KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();

// Query local state store
ReadOnlyKeyValueStore<String, Long> store =
    streams.store(StoreQueryParameters.fromNameAndType(
        "counts-store", QueryableStoreTypes.keyValueStore()));

Long count = store.get("my-key");

// Iterate all entries
try (KeyValueIterator<String, Long> iter = store.all()) {
    while (iter.hasNext()) {
        KeyValue<String, Long> entry = iter.next();
        System.out.printf("%s: %d%n", entry.key, entry.value);
    }
}
```

## Key Configuration

| Property | Default | Description |
|----------|---------|-------------|
| `application.id` | — | Unique identifier (also used as consumer group.id) |
| `bootstrap.servers` | — | Kafka broker addresses |
| `num.stream.threads` | 1 | Processing threads per instance |
| `processing.guarantee` | `at_least_once` | `at_least_once` or `exactly_once_v2` |
| `state.dir` | `/tmp/kafka-streams` | Local state store directory |
| `cache.max.bytes.buffering` | 10485760 | Record cache size |
| `commit.interval.ms` | 30000 | State/offset commit interval |
| `replication.factor` | -1 | Replication for internal topics |

## Testing

```java
import org.apache.kafka.streams.TopologyTestDriver;
import org.apache.kafka.streams.TestInputTopic;
import org.apache.kafka.streams.TestOutputTopic;

TopologyTestDriver driver = new TopologyTestDriver(builder.build(), props);

TestInputTopic<String, String> input = driver.createInputTopic(
    "input-topic", new StringSerializer(), new StringSerializer());

TestOutputTopic<String, String> output = driver.createOutputTopic(
    "output-topic", new StringDeserializer(), new StringDeserializer());

input.pipeInput("key1", "value1");
KeyValue<String, String> result = output.readKeyValue();
assertEquals("key1", result.key);
assertEquals("expected-value", result.value);

driver.close();
```
