# Agent Event Tracing: Correlation, Causation & Distributed Observability

## The Problem: Tracing Events Across Agents

In agent-based workflows, a single user request spawns a tree of events across multiple agents. Without tracing metadata, you cannot answer:

- **Which events belong to the same workflow?** (correlation)
- **Which event triggered which?** (causation)
- **What was the full execution path?** (reconstruction)
- **Where did it fail?** (debugging)

```
User: "Implement login page"

  Orchestrator ──→ Planner ──→ Coder ──→ Reviewer
                           ├──→ Researcher
                           └──→ Tester

Without tracing: 14 events in agent-events topic with no way to connect them
With tracing:    14 events all sharing correlation_id, linked by causation_id
```

---

## Core Concepts: correlation_id vs causation_id

Two IDs serve different purposes — both are required for full observability.

| Field | Purpose | Value | Same across workflow? |
|-------|---------|-------|-----------------------|
| `event_id` | Unique identity of this event | New UUID per event | No — always unique |
| `correlation_id` | "Which workflow is this part of?" | Copied from root event | **Yes — same for all events in the chain** |
| `causation_id` | "Which event directly triggered this one?" | `event_id` of the parent event | No — points to immediate parent |

### Visual Model

```
User Request (event_id=A)
  │
  ├─ correlation_id: A       ← workflow root
  ├─ causation_id:   null    ← no parent (this IS the trigger)
  │
  └──→ Planner (event_id=B)
         correlation_id: A    ← same workflow
         causation_id:   A    ← caused by user request
         │
         ├──→ Coder (event_id=C)
         │      correlation_id: A    ← same workflow
         │      causation_id:   B    ← caused by planner
         │      │
         │      └──→ Reviewer (event_id=E)
         │             correlation_id: A    ← same workflow
         │             causation_id:   C    ← caused by coder
         │
         └──→ Researcher (event_id=D)
                correlation_id: A    ← same workflow
                causation_id:   B    ← caused by planner

correlation_id forms a FLAT grouping   (all = A)
causation_id forms a TREE structure    (A → B → C → E, B → D)
```

### Rules

1. **Root event**: `correlation_id = event_id`, `causation_id = null`
2. **Child event**: `correlation_id` = parent's `correlation_id` (always propagate), `causation_id` = parent's `event_id`
3. **correlation_id never changes** as it flows through the chain
4. **causation_id always changes** to the immediate parent's `event_id`

---

## Event Envelope Schema

### Avro Schema

```json
{
  "type": "record",
  "name": "AgentEvent",
  "namespace": "com.example.agents.events",
  "doc": "Standard envelope for all agent workflow events with distributed tracing.",
  "fields": [
    {
      "name": "event_id",
      "type": {"type": "string", "logicalType": "uuid"},
      "doc": "Unique ID for this event"
    },
    {
      "name": "correlation_id",
      "type": {"type": "string", "logicalType": "uuid"},
      "doc": "Root event ID — identical for all events in one workflow"
    },
    {
      "name": "causation_id",
      "type": ["null", {"type": "string", "logicalType": "uuid"}],
      "default": null,
      "doc": "event_id of the direct parent. Null only for root events."
    },
    {
      "name": "event_type",
      "type": "string",
      "doc": "Dot-notation type: agent.task.assigned, agent.task.completed, etc."
    },
    {
      "name": "agent_id",
      "type": "string",
      "doc": "Instance identifier of the agent that produced this event"
    },
    {
      "name": "agent_type",
      "type": {
        "type": "enum",
        "name": "AgentType",
        "symbols": ["ORCHESTRATOR", "PLANNER", "CODER", "RESEARCHER", "REVIEWER", "TESTER", "CUSTOM"]
      },
      "doc": "Role of the producing agent"
    },
    {
      "name": "workflow_id",
      "type": {"type": "string", "logicalType": "uuid"},
      "doc": "Business-level workflow grouping (e.g., user session, project)"
    },
    {
      "name": "timestamp",
      "type": {"type": "long", "logicalType": "timestamp-millis"}
    },
    {
      "name": "parent_agents",
      "type": {"type": "array", "items": "string"},
      "default": [],
      "doc": "Ordered list of agent_ids in the causal chain — breadcrumb trail for debugging"
    },
    {
      "name": "depth",
      "type": "int",
      "default": 0,
      "doc": "Hop count from root event (0 = root). Use to detect runaway chains."
    },
    {
      "name": "payload",
      "type": {"type": "map", "values": "string"},
      "default": {},
      "doc": "Event-specific business data"
    }
  ]
}
```

### JSON Alternative (When Avro Is Not Available)

```python
event = {
    "event_id": "uuid-1",
    "correlation_id": "uuid-root",
    "causation_id": "uuid-parent",
    "event_type": "agent.task.completed",
    "agent_id": "coder-1",
    "agent_type": "CODER",
    "workflow_id": "uuid-workflow",
    "timestamp": "2025-01-15T10:30:00Z",
    "parent_agents": ["orchestrator-1", "planner-1"],
    "depth": 2,
    "payload": {"task": "Write login component", "output": "LoginForm.tsx"}
}
```

### Schema Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `correlation_id` in value, not headers | Value | Must survive serialization/deserialization, be queryable in stream processing, and not get lost by connectors that drop headers |
| `causation_id` nullable | Yes | Root events have no parent — using `null` is cleaner than a sentinel value |
| `parent_agents` array | Denormalized | Avoids needing to traverse the full chain to get the breadcrumb trail; O(1) lookup |
| `depth` integer | Explicit | Enables circuit-breaker logic (reject events with depth > N) without tree traversal |
| `agent_type` enum | Closed set | Avro enums enforce valid types at serialization time; add `CUSTOM` for extensibility |
| `workflow_id` separate from `correlation_id` | Yes | `workflow_id` is a business concept (user session); `correlation_id` is technical (event chain). One workflow may have multiple correlation chains (retries) |

---

## Event Context Propagation

The `EventContext` dataclass carries tracing metadata between agents. Every agent receives a context, does its work, and derives child contexts when delegating.

### Python Implementation

```python
from dataclasses import dataclass, field
import uuid


@dataclass(frozen=True)
class EventContext:
    """Immutable tracing context passed between agents."""
    correlation_id: str
    causation_id: str | None
    workflow_id: str
    parent_agents: tuple[str, ...] = field(default_factory=tuple)
    depth: int = 0

    @classmethod
    def new_workflow(cls, workflow_id: str) -> "EventContext":
        """Create context for the root event of a new workflow."""
        root_id = str(uuid.uuid4())
        return cls(
            correlation_id=root_id,
            causation_id=None,
            workflow_id=workflow_id,
            parent_agents=(),
            depth=0,
        )

    def child(self, parent_event_id: str, agent_id: str) -> "EventContext":
        """Derive child context when one agent delegates to another.

        Args:
            parent_event_id: event_id of the event that triggers the child
            agent_id: ID of the agent producing the parent event
        """
        return EventContext(
            correlation_id=self.correlation_id,      # Never changes
            causation_id=parent_event_id,             # Points to immediate parent
            workflow_id=self.workflow_id,
            parent_agents=self.parent_agents + (agent_id,),
            depth=self.depth + 1,
        )

    def to_headers(self) -> dict[str, bytes]:
        """Export as Kafka headers (for systems that use header-based tracing)."""
        headers = {
            "correlation-id": self.correlation_id.encode(),
            "workflow-id": self.workflow_id.encode(),
            "depth": str(self.depth).encode(),
        }
        if self.causation_id:
            headers["causation-id"] = self.causation_id.encode()
        return headers

    @classmethod
    def from_event(cls, event: dict) -> "EventContext":
        """Reconstruct context from a consumed event."""
        return cls(
            correlation_id=event["correlation_id"],
            causation_id=event["event_id"],      # This event becomes the cause
            workflow_id=event["workflow_id"],
            parent_agents=tuple(event.get("parent_agents", [])) + (event["agent_id"],),
            depth=event.get("depth", 0) + 1,
        )
```

### Context Flow Through an Agent Pipeline

```
                        EventContext
                  ┌──────────────────────┐
User Request ──→ │ correlation_id: ROOT  │
                 │ causation_id:   null  │
                 │ depth: 0              │
                 └────────┬─────────────┘
                          │ .child(event_id_A, "orchestrator-1")
                          ▼
                 ┌──────────────────────┐
  Orchestrator → │ correlation_id: ROOT │
                 │ causation_id:   A    │
                 │ depth: 1             │
                 │ parent_agents: [orch]│
                 └───┬──────────┬──────┘
   .child(B,"planner")│          │.child(B,"planner")
                      ▼          ▼
              ┌────────────┐ ┌────────────┐
   Coder    → │ corr: ROOT │ │ corr: ROOT │ ← Researcher
              │ cause: B   │ │ cause: B   │
              │ depth: 2   │ │ depth: 2   │
              └────────────┘ └────────────┘
```

---

## Producer: Emitting Traced Events

```python
import json, time, uuid
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer


class AgentEventProducer:
    """Produces agent events with full tracing metadata."""

    def __init__(self, bootstrap_servers: str, schema_registry_url: str):
        registry = SchemaRegistryClient({"url": schema_registry_url})
        with open("agent_event.avsc") as f:
            schema_str = f.read()
        self._serializer = AvroSerializer(registry, schema_str)
        self._producer = SerializingProducer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "enable.idempotence": True,
            "linger.ms": 5,
            "value.serializer": self._serializer,
        })

    def emit(
        self,
        ctx: EventContext,
        event_type: str,
        agent_id: str,
        agent_type: str,
        payload: dict[str, str] | None = None,
    ) -> str:
        """Produce an event and return its event_id."""
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "correlation_id": ctx.correlation_id,
            "causation_id": ctx.causation_id,
            "event_type": event_type,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "workflow_id": ctx.workflow_id,
            "timestamp": int(time.time() * 1000),
            "parent_agents": list(ctx.parent_agents),
            "depth": ctx.depth,
            "payload": payload or {},
        }
        # Key by workflow_id — all events for one workflow in the same partition
        self._producer.produce(
            topic="agent-events",
            key=ctx.workflow_id,
            value=event,
        )
        self._producer.poll(0)
        return event_id

    def flush(self):
        self._producer.flush()


# --- JSON variant (no Schema Registry) ---

class AgentEventProducerJSON:
    """Simpler variant for environments without Schema Registry."""

    def __init__(self, bootstrap_servers: str):
        from confluent_kafka import Producer
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "enable.idempotence": True,
        })

    def emit(self, ctx: EventContext, event_type: str,
             agent_id: str, agent_type: str,
             payload: dict | None = None) -> str:
        event_id = str(uuid.uuid4())
        event = {
            "event_id": event_id,
            "correlation_id": ctx.correlation_id,
            "causation_id": ctx.causation_id,
            "event_type": event_type,
            "agent_id": agent_id,
            "agent_type": agent_type,
            "workflow_id": ctx.workflow_id,
            "timestamp": int(time.time() * 1000),
            "parent_agents": list(ctx.parent_agents),
            "depth": ctx.depth,
            "payload": payload or {},
        }
        self._producer.produce(
            topic="agent-events",
            key=ctx.workflow_id,
            value=json.dumps(event).encode("utf-8"),
            headers=ctx.to_headers(),
        )
        self._producer.poll(0)
        return event_id

    def flush(self):
        self._producer.flush()
```

---

## Agent Workflow: End-to-End Example

```python
producer = AgentEventProducer("localhost:9092", "http://localhost:8081")
workflow_id = str(uuid.uuid4())

# 1. Root: user request arrives
ctx = EventContext.new_workflow(workflow_id)
root_id = producer.emit(
    ctx, "workflow.started", "orchestrator-1", "ORCHESTRATOR",
    payload={"user_request": "Implement login page"},
)

# 2. Orchestrator delegates to Planner
planner_ctx = ctx.child(root_id, "orchestrator-1")
planner_id = producer.emit(
    planner_ctx, "agent.task.assigned", "planner-1", "PLANNER",
    payload={"task": "Break down login page implementation"},
)

# 3. Planner delegates to Coder + Researcher in parallel
coder_ctx = planner_ctx.child(planner_id, "planner-1")
researcher_ctx = planner_ctx.child(planner_id, "planner-1")

coder_id = producer.emit(
    coder_ctx, "agent.task.assigned", "coder-1", "CODER",
    payload={"task": "Write React login component"},
)
researcher_id = producer.emit(
    researcher_ctx, "agent.task.assigned", "researcher-1", "RESEARCHER",
    payload={"task": "Research OAuth2 best practices"},
)

# 4. Coder completes → triggers Reviewer
producer.emit(
    coder_ctx, "agent.task.completed", "coder-1", "CODER",
    payload={"output": "LoginForm.tsx"},
)
review_ctx = coder_ctx.child(coder_id, "coder-1")
producer.emit(
    review_ctx, "agent.task.assigned", "reviewer-1", "REVIEWER",
    payload={"task": "Review LoginForm.tsx"},
)

producer.flush()
```

**Resulting events in topic:**

```
event_id  corr_id  cause_id  type                   agent        depth  parent_agents
────────  ───────  ────────  ─────────────────────   ───────────  ─────  ─────────────
A         A        null      workflow.started        orch-1       0      []
B         A        A         agent.task.assigned     planner-1    1      [orch-1]
C         A        B         agent.task.assigned     coder-1      2      [orch-1, planner-1]
D         A        B         agent.task.assigned     researcher-1 2      [orch-1, planner-1]
E         A        C         agent.task.completed    coder-1      2      [orch-1, planner-1]
F         A        C         agent.task.assigned     reviewer-1   3      [orch-1, planner-1, coder-1]
```

---

## Consumer: Reconstructing Causality Trees

### Indexing and Tree Building

```python
from collections import defaultdict
from confluent_kafka import DeserializingConsumer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroDeserializer


class WorkflowTracer:
    """Consumes agent events and reconstructs causality trees."""

    def __init__(self):
        self.workflows: dict[str, list[dict]] = defaultdict(list)
        self.events_by_id: dict[str, dict] = {}

    def index(self, event: dict):
        """Add an event to the index."""
        self.workflows[event["correlation_id"]].append(event)
        self.events_by_id[event["event_id"]] = event

    def build_tree(self, correlation_id: str) -> dict | None:
        """Build the full causal tree for a workflow."""
        events = self.workflows.get(correlation_id, [])
        if not events:
            return None

        # Find root(s)
        roots = [e for e in events if e["causation_id"] is None]
        if not roots:
            return None

        # Index: parent_event_id → [child_events]
        children = defaultdict(list)
        for e in events:
            if e["causation_id"]:
                children[e["causation_id"]].append(e)

        def to_node(event: dict) -> dict:
            return {
                "event_id": event["event_id"],
                "event_type": event["event_type"],
                "agent_id": event["agent_id"],
                "agent_type": event["agent_type"],
                "timestamp": event["timestamp"],
                "depth": event["depth"],
                "payload": event.get("payload", {}),
                "children": sorted(
                    [to_node(c) for c in children.get(event["event_id"], [])],
                    key=lambda n: n["timestamp"],
                ),
            }

        return to_node(roots[0])

    def get_causal_chain(self, event_id: str) -> list[dict]:
        """Walk UP from an event to the root — answer "how did we get here?" """
        chain = []
        current = self.events_by_id.get(event_id)
        while current:
            chain.append(current)
            current = self.events_by_id.get(current.get("causation_id"))
        chain.reverse()
        return chain

    def get_children(self, event_id: str, correlation_id: str) -> list[dict]:
        """Get all events directly caused by a given event."""
        return [
            e for e in self.workflows.get(correlation_id, [])
            if e["causation_id"] == event_id
        ]

    def print_tree(self, node: dict, indent: int = 0):
        """Print a causality tree as a visual trace."""
        prefix = "  " * indent + ("└─ " if indent > 0 else "")
        status = "✓" if "completed" in node["event_type"] else \
                 "✗" if "failed" in node["event_type"] else "→"
        print(
            f"{prefix}[{status}] {node['agent_type']} ({node['agent_id']}): "
            f"{node['event_type']}  [{node['event_id'][:8]}...]"
        )
        for child in node["children"]:
            self.print_tree(child, indent + 1)
```

### Running the Tracer

```python
tracer = WorkflowTracer()
registry = SchemaRegistryClient({"url": "http://localhost:8081"})
consumer = DeserializingConsumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "workflow-tracer",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "value.deserializer": AvroDeserializer(registry),
})
consumer.subscribe(["agent-events"])

while True:
    msg = consumer.poll(1.0)
    if msg is None or msg.error():
        continue
    event = msg.value()
    tracer.index(event)
    consumer.commit(asynchronous=False)

    # Print updated tree
    tree = tracer.build_tree(event["correlation_id"])
    if tree:
        print(f"\n── Workflow {event['correlation_id'][:8]}... ──")
        tracer.print_tree(tree)
```

**Output:**

```
── Workflow a1b2c3d4... ──
[→] ORCHESTRATOR (orchestrator-1): workflow.started  [a1b2c3d4...]
  └─ [→] PLANNER (planner-1): agent.task.assigned  [e5f6a7b8...]
    └─ [→] CODER (coder-1): agent.task.assigned  [c9d0e1f2...]
      └─ [✓] CODER (coder-1): agent.task.completed  [11223344...]
        └─ [→] REVIEWER (reviewer-1): agent.task.assigned  [55667788...]
    └─ [→] RESEARCHER (researcher-1): agent.task.assigned  [aabbccdd...]
```

### Upward Chain Query (Debugging)

```python
# "How did reviewer-1 get involved?"
chain = tracer.get_causal_chain("55667788-...")

for e in chain:
    print(f"  {e['agent_id']:20s} {e['event_type']:30s} depth={e['depth']}")

# Output:
#   orchestrator-1       workflow.started               depth=0
#   planner-1            agent.task.assigned            depth=1
#   coder-1              agent.task.assigned            depth=2
#   reviewer-1           agent.task.assigned            depth=3
```

---

## Agent Event Type Taxonomy

Standard event types for agent workflows:

```
agent.task.assigned       — agent received a task
agent.task.accepted       — agent acknowledged the task
agent.task.progress       — intermediate progress update
agent.task.completed      — agent finished successfully
agent.task.failed         — agent failed (include error in payload)
agent.task.delegated      — agent delegated to a sub-agent
agent.task.cancelled      — task was cancelled by orchestrator

workflow.started          — root event: user request arrived
workflow.completed        — orchestrator determined all agents done
workflow.failed           — workflow failed (compensation may follow)
workflow.timeout          — workflow exceeded time budget

agent.tool.invoked        — agent called an external tool
agent.tool.result         — tool returned a result
agent.feedback.requested  — agent needs human input
agent.feedback.received   — human provided input
```

### Event Lifecycle per Agent

```
agent.task.assigned
  │
  ├─→ agent.task.accepted
  │     │
  │     ├─→ agent.tool.invoked → agent.tool.result   (0..N times)
  │     ├─→ agent.task.progress                       (0..N times)
  │     ├─→ agent.task.delegated → [child agent]      (0..N times)
  │     │
  │     ├─→ agent.task.completed    ← happy path
  │     └─→ agent.task.failed       ← error path
  │
  └─→ agent.task.cancelled          ← external cancellation
```

---

## Depth-Based Circuit Breaker

Prevent runaway agent delegation chains:

```python
MAX_AGENT_DEPTH = 10

def handle_task(ctx: EventContext, task: dict, producer: AgentEventProducer):
    if ctx.depth >= MAX_AGENT_DEPTH:
        producer.emit(
            ctx, "agent.task.failed", MY_AGENT_ID, MY_AGENT_TYPE,
            payload={
                "error": "max_depth_exceeded",
                "message": f"Delegation chain exceeded {MAX_AGENT_DEPTH} hops",
                "chain": ",".join(ctx.parent_agents),
            },
        )
        return

    # Normal processing...
```

---

## Kafka Streams: Real-Time Workflow Aggregation

Use Kafka Streams to maintain a live view of workflow status:

```java
StreamsBuilder builder = new StreamsBuilder();

// Group by correlation_id, aggregate into workflow state
KTable<String, WorkflowState> workflows = builder
    .stream("agent-events", Consumed.with(stringSerde, agentEventSerde))
    .groupBy(
        (key, event) -> event.getCorrelationId(),   // re-key by correlation_id
        Grouped.with(stringSerde, agentEventSerde)
    )
    .aggregate(
        WorkflowState::new,
        (corrId, event, state) -> state.apply(event),
        Materialized.as("workflow-states")           // queryable state store
    );

// Detect failed workflows → produce to alert topic
workflows.toStream()
    .filter((corrId, state) -> state.hasFailure())
    .to("workflow-alerts", Produced.with(stringSerde, workflowStateSerde));
```

```java
public class WorkflowState {
    private String correlationId;
    private Map<String, String> agentStatuses = new HashMap<>();  // agent_id → last status
    private List<String> eventLog = new ArrayList<>();
    private int totalEvents = 0;
    private int failedCount = 0;

    public WorkflowState apply(AgentEvent event) {
        this.correlationId = event.getCorrelationId();
        this.totalEvents++;
        this.agentStatuses.put(event.getAgentId(), event.getEventType());
        this.eventLog.add(event.getEventId());
        if (event.getEventType().contains("failed")) {
            this.failedCount++;
        }
        return this;
    }

    public boolean hasFailure() {
        return failedCount > 0;
    }

    public boolean isComplete() {
        return agentStatuses.values().stream()
            .anyMatch(s -> s.equals("workflow.completed"));
    }
}
```

---

## Topic Design

### Single Topic (Recommended for Most Cases)

```bash
bin/kafka-topics.sh --create \
  --topic agent-events \
  --bootstrap-server localhost:9092 \
  --partitions 12 \
  --replication-factor 3 \
  --config retention.ms=604800000
```

Key by `workflow_id` → all events for one workflow in one partition → ordering guaranteed for the full causal chain.

### Multi-Topic (High-Volume Systems)

```
agent-events.commands     — task assignments (assigned, delegated)
agent-events.status       — progress and completion (accepted, progress, completed, failed)
agent-events.tools        — tool invocations and results
agent-events.workflow     — workflow-level events (started, completed, failed)
```

When to split:
- Different retention needs (tool events expire faster)
- Different consumer groups care about different event categories
- Volume exceeds what a single topic can handle

When to keep single topic:
- Causality reconstruction needs all events in order
- Simpler operations and monitoring
- Fewer than 10,000 events/second

---

## Partitioning Strategy

| Key Choice | Guarantees | Trade-off |
|------------|------------|-----------|
| `workflow_id` (recommended) | All events for one workflow in one partition — full ordering | Hot partitions if one workflow generates many events |
| `agent_id` | All events from one agent in order | Events from the same workflow may span partitions — cross-partition joins needed |
| `correlation_id` | Same as workflow_id for single-chain workflows | Breaks if one workflow has multiple correlation chains (retries) |

**Recommendation:** Use `workflow_id` as the partition key. One workflow's events stay together, making causality reconstruction a single-partition read.

---

## OpenTelemetry Integration

Bridge Kafka tracing with OpenTelemetry for end-to-end observability:

```python
from opentelemetry import trace
from opentelemetry.context import propagation

tracer = trace.get_tracer("agent-events")


def emit_with_otel(
    producer: AgentEventProducer,
    ctx: EventContext,
    event_type: str,
    agent_id: str,
    agent_type: str,
    payload: dict | None = None,
) -> str:
    """Emit an agent event with OpenTelemetry span correlation."""
    with tracer.start_as_current_span(
        f"{agent_type}.{event_type}",
        attributes={
            "agent.id": agent_id,
            "agent.type": agent_type,
            "workflow.id": ctx.workflow_id,
            "event.correlation_id": ctx.correlation_id,
            "event.depth": ctx.depth,
        },
    ) as span:
        event_id = producer.emit(ctx, event_type, agent_id, agent_type, payload)
        span.set_attribute("event.id", event_id)
        return event_id
```

### Mapping: Kafka Tracing → OpenTelemetry Concepts

| Kafka Agent Tracing | OpenTelemetry Equivalent |
|---------------------|--------------------------|
| `correlation_id` | Trace ID |
| `causation_id` | Parent Span ID |
| `event_id` | Span ID |
| `parent_agents` | Span ancestry |
| `depth` | Span depth in trace tree |

---

## Querying Workflow History

### PostgreSQL Materialized View (Sink via Kafka Connect)

```sql
-- Sink agent-events to PostgreSQL via JDBC Sink Connector
-- Then query with SQL:

-- All events in a workflow, ordered causally
SELECT event_id, causation_id, event_type, agent_id, depth, timestamp
FROM agent_events
WHERE correlation_id = 'a1b2c3d4-...'
ORDER BY depth, timestamp;

-- Find the causal chain for a specific event (recursive CTE)
WITH RECURSIVE chain AS (
    SELECT event_id, causation_id, event_type, agent_id, depth
    FROM agent_events
    WHERE event_id = '55667788-...'

    UNION ALL

    SELECT e.event_id, e.causation_id, e.event_type, e.agent_id, e.depth
    FROM agent_events e
    JOIN chain c ON e.event_id = c.causation_id
)
SELECT * FROM chain ORDER BY depth;

-- Workflows with failures
SELECT correlation_id, COUNT(*) AS total_events,
       SUM(CASE WHEN event_type LIKE '%.failed' THEN 1 ELSE 0 END) AS failures
FROM agent_events
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY correlation_id
HAVING SUM(CASE WHEN event_type LIKE '%.failed' THEN 1 ELSE 0 END) > 0;

-- Average workflow depth (detect runaway chains)
SELECT AVG(max_depth) AS avg_depth, MAX(max_depth) AS max_depth
FROM (
    SELECT correlation_id, MAX(depth) AS max_depth
    FROM agent_events
    GROUP BY correlation_id
) sub;
```

---

## Summary: When to Use Each Pattern

| Pattern | Use When |
|---------|----------|
| `correlation_id` only | Simple request-response tracing, no branching |
| `correlation_id` + `causation_id` | Multi-agent workflows with delegation trees |
| `parent_agents` breadcrumb | Need to debug "who called whom" without traversing the tree |
| `depth` field | Need circuit breakers to prevent infinite delegation |
| Kafka Streams aggregation | Real-time workflow monitoring dashboards |
| PostgreSQL recursive CTE | Post-hoc analysis and debugging of completed workflows |
| OpenTelemetry bridge | Connecting Kafka event traces to HTTP/gRPC traces in existing observability stack |
