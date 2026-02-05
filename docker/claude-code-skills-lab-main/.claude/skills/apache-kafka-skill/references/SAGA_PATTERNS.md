# Saga Patterns: Distributed Workflows with Compensation

## When to Use Sagas

A **saga** is a sequence of local transactions across services, where each step has a **compensating action** that undoes its effect if a later step fails. Sagas replace distributed transactions (2PC) in event-driven systems.

| Use a Saga When | Don't Use a Saga When |
|-----------------|------------------------|
| Multiple services must coordinate to complete a business operation | A single service owns all the data |
| Each step has a clear undo/compensating action | The operation is naturally atomic (single DB transaction) |
| Steps can tolerate eventual consistency | Strong consistency is required between steps (use 2PC or single DB) |
| Services own their own databases | All data is in one database |
| You need resilience — partial failure must not leave the system inconsistent | The workflow has only 2 steps with simple rollback |

### Saga vs Other Patterns

| Pattern | Consistency | Complexity | Use When |
|---------|-------------|------------|----------|
| **Single DB transaction** | Strong | Low | All data in one database |
| **Kafka transaction** | Atomic across topics | Medium | Atomic read-process-write within Kafka only |
| **Transactional outbox** | Atomic DB + event | Medium | Reliably publishing events from a DB write |
| **Saga** | Eventual | High | Multi-service workflows requiring compensation |
| **2PC (two-phase commit)** | Strong | Very high | Rarely used — poor availability, latency, and scalability |

---

## Two Saga Styles: Orchestration vs Choreography

### Choreography: Event-Driven, No Central Coordinator

Each service listens for events and reacts independently. No service knows the full workflow.

```
Order Service ──→ [order.created] ──→ Payment Service
                                          │
                                   [payment.charged] ──→ Inventory Service
                                                              │
                                                       [inventory.reserved] ──→ Shipping Service
                                                                                    │
                                                                             [shipping.scheduled] ──→ Order Service
                                                                                                      (mark complete)

Compensation:
  [inventory.reserve.failed] ──→ Payment Service (refund)
                             ──→ Order Service (mark failed)
```

**Each service must know:**
- Which events to listen for (trigger)
- What to do on success (forward action + produce next event)
- What to do on failure (compensate + produce compensation event)

```python
# Payment Service — choreography style
class PaymentServiceChoreography:
    def __init__(self, producer, consumer):
        self._producer = producer
        self._consumer = consumer
        self._consumer.subscribe(["order.created", "inventory.reserve.failed"])

    def handle(self, event: dict):
        event_type = event["event_type"]

        if event_type == "order.created":
            # Forward step: charge the customer
            charge_id = self._charge(event["customer_id"], event["amount_cents"])
            self._produce("payment.events", {
                "event_type": "payment.charged",
                "order_id": event["order_id"],
                "charge_id": charge_id,
                "amount_cents": event["amount_cents"],
            })

        elif event_type == "inventory.reserve.failed":
            # Compensation: refund because a later step failed
            self._refund(event["order_id"])
            self._produce("payment.events", {
                "event_type": "payment.refunded",
                "order_id": event["order_id"],
                "reason": "inventory_failed",
            })
```

### Orchestration: Central Coordinator Drives the Workflow

A single **orchestrator** service owns the saga definition, sends commands to participants, and handles replies.

```
                                    ┌─────────────────────┐
  order.create ──→                  │  Order Orchestrator  │
                                    │  (saga state machine)│
                                    └──┬────┬────┬────┬───┘
                                       │    │    │    │
                        payment.charge ─┘    │    │    └─ order.confirmed
                      inventory.reserve ─────┘    │
                       shipping.schedule ─────────┘
                                       │    │    │
                                       ▼    ▼    ▼
                                    [saga.replies]
                                       │
                                       ▼
                                  Orchestrator
                              (next step or compensate)
```

### Decision Matrix

| Factor | Choreography | Orchestration |
|--------|-------------|---------------|
| **Number of steps** | 2–3 | 4+ |
| **Workflow visibility** | Scattered across services | Single place |
| **Adding a step** | Modify multiple services | Modify orchestrator only |
| **Compensation logic** | Each service decides | Orchestrator decides |
| **Debugging** | Hard — trace events across services | Easy — check orchestrator state |
| **Service coupling** | Services know about each other's events | Services know only command/reply |
| **Single point of failure** | None | Orchestrator (mitigate with HA) |

**Recommendation:** Use choreography for simple 2-step flows. Use orchestration for anything with 3+ steps, conditional branching, or complex compensation logic.

---

## Saga State Machine

The orchestrator maintains a state machine per saga instance:

```
                     order.created
                          │
                          ▼
                  ┌───────────────┐
                  │   PAYMENT     │──── payment.charge ──→ Payment Service
                  │   PENDING     │
                  └───────┬───────┘
           succeeded      │      failed
           ┌──────────────┼──────────────┐
           ▼                             ▼
   ┌───────────────┐             ┌──────────────┐
   │   INVENTORY   │             │  COMPENSATING │ (nothing to compensate)
   │   PENDING     │             │              │
   └───────┬───────┘             └──────┬───────┘
    succeeded│    failed                 │
   ┌─────────┼─────────┐                ▼
   ▼                    ▼         ┌──────────────┐
┌────────────┐  ┌──────────────┐  │    FAILED    │
│  SHIPPING  │  │ COMPENSATING │  └──────────────┘
│  PENDING   │  │ ← payment    │
└─────┬──────┘  │   .refund    │
 succ │  fail   └──────┬───────┘
  ┌───┼────┐           │
  ▼        ▼           ▼
┌─────┐ ┌──────────┐ ┌──────┐
│DONE │ │COMPENSATE│ │FAILED│
│     │ │←inv,←pay │ │      │
└─────┘ └────┬─────┘ └──────┘
             │
             ▼
          ┌──────┐
          │FAILED│
          └──────┘

Key rule: compensation runs in REVERSE order of completed steps
```

---

## Command/Reply Envelope Schemas

### Saga Command (Orchestrator → Participant)

```json
{
  "type": "record",
  "name": "SagaCommand",
  "namespace": "com.example.saga",
  "fields": [
    {"name": "command_id", "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "saga_id", "type": {"type": "string", "logicalType": "uuid"},
     "doc": "Groups all commands/replies in one saga instance"},
    {"name": "order_id", "type": {"type": "string", "logicalType": "uuid"},
     "doc": "Business entity ID — also the Kafka message key"},
    {"name": "command_type", "type": "string",
     "doc": "e.g. payment.charge, payment.refund, inventory.reserve"},
    {"name": "step_number", "type": "int",
     "doc": "Position in the saga sequence (1-indexed)"},
    {"name": "is_compensation", "type": "boolean", "default": false,
     "doc": "true = this is an undo command"},
    {"name": "payload", "type": {"type": "map", "values": "string"}, "default": {},
     "doc": "Step-specific business data"},
    {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}}
  ]
}
```

### Saga Reply (Participant → Orchestrator)

```json
{
  "type": "record",
  "name": "SagaReply",
  "namespace": "com.example.saga",
  "fields": [
    {"name": "reply_id", "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "saga_id", "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "order_id", "type": {"type": "string", "logicalType": "uuid"}},
    {"name": "command_id", "type": {"type": "string", "logicalType": "uuid"},
     "doc": "Which command this replies to"},
    {"name": "step_number", "type": "int"},
    {"name": "status", "type": {"type": "enum", "name": "ReplyStatus",
     "symbols": ["SUCCEEDED", "FAILED", "COMPENSATED"]}},
    {"name": "failure_reason", "type": ["null", "string"], "default": null},
    {"name": "payload", "type": {"type": "map", "values": "string"}, "default": {},
     "doc": "Result data — passed back to orchestrator for compensation enrichment"},
    {"name": "timestamp", "type": {"type": "long", "logicalType": "timestamp-millis"}}
  ]
}
```

### Per-Step Forward + Compensation Pairs

Every saga step has a forward command and a compensating command:

| Step | Forward Command | Compensation Command | Compensation Needs |
|------|----------------|---------------------|-------------------|
| 1. Payment | `payment.charge` | `payment.refund` | `charge_id`, `amount_cents` from forward reply |
| 2. Inventory | `inventory.reserve` | `inventory.release` | `reservation_id` from forward reply |
| 3. Shipping | `shipping.schedule` | `shipping.cancel` | `shipment_id` from forward reply |

**Critical:** The orchestrator must store each forward step's reply payload so it can enrich the compensation command with the data needed to undo the action (e.g., the `charge_id` is needed to issue a refund).

---

## Topic Design

### Command/Reply Topology

```
                    ┌──────────────────────┐
 order.commands ──→ │    Orchestrator       │ ←── saga.replies
                    └──┬─────┬─────┬───────┘
                       │     │     │
             payment   │     │     │  shipping
            .commands  │     │     │  .commands
                       ▼     │     ▼
                  Payment    │   Shipping
                  Service    │   Service
                       │     │     │
                       └──→ saga.replies ←──┘
                             │
                    inventory.commands
                             │
                             ▼
                       Inventory
                        Service
                             │
                             └──→ saga.replies
```

```bash
# One command topic per participant, one shared reply topic
bin/kafka-topics.sh --create --topic order.commands     --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic payment.commands   --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic inventory.commands --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic shipping.commands  --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092
bin/kafka-topics.sh --create --topic saga.replies       --partitions 6 --replication-factor 3 --bootstrap-server localhost:9092

# All keyed by order_id — ordering guaranteed per order
```

### Why Topic-Per-Service for Commands

| Approach | Pro | Con |
|----------|-----|-----|
| **Topic per service** (recommended) | Each service subscribes to only its commands; clear ownership | More topics to manage |
| **Single commands topic** | Fewer topics | Every service receives every command; must filter; wastes bandwidth |

### Why Single Reply Topic

The orchestrator consumes all replies. One topic is simpler to manage. Partition by `order_id` ensures all replies for one saga are ordered.

---

## Orchestrator Implementation

### Step Definition

```python
import enum
import uuid
import time
import json
from dataclasses import dataclass, field
from confluent_kafka import Producer, Consumer, KafkaError


class SagaStatus(str, enum.Enum):
    STARTED = "STARTED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    INVENTORY_PENDING = "INVENTORY_PENDING"
    SHIPPING_PENDING = "SHIPPING_PENDING"
    COMPENSATING = "COMPENSATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class SagaStep:
    step_number: int
    forward_command: str        # e.g. "payment.charge"
    forward_topic: str          # e.g. "payment.commands"
    compensate_command: str     # e.g. "payment.refund"
    compensate_topic: str
    pending_status: SagaStatus
    result_payload: dict = field(default_factory=dict)


SAGA_STEPS = [
    SagaStep(1, "payment.charge",    "payment.commands",   "payment.refund",    "payment.commands",   SagaStatus.PAYMENT_PENDING),
    SagaStep(2, "inventory.reserve", "inventory.commands", "inventory.release", "inventory.commands", SagaStatus.INVENTORY_PENDING),
    SagaStep(3, "shipping.schedule", "shipping.commands",  "shipping.cancel",   "shipping.commands",  SagaStatus.SHIPPING_PENDING),
]
```

### Saga State

```python
@dataclass
class SagaState:
    saga_id: str
    order_id: str
    status: SagaStatus
    current_step: int                           # Index into SAGA_STEPS
    order_data: dict                            # Original order payload
    completed_steps: list[dict] = field(default_factory=list)  # Reply payloads per step
    compensation_index: int = -1                # Which step to compensate next
    failure_reason: str | None = None
```

### Orchestrator

```python
class OrderSagaOrchestrator:
    def __init__(self, bootstrap_servers: str):
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "enable.idempotence": True,
        })
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": "order-saga-orchestrator",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._consumer.subscribe(["order.commands", "saga.replies"])
        # Production: use PostgreSQL (see persistence section below)
        self._sagas: dict[str, SagaState] = {}

    def _send(self, topic: str, order_id: str, command: dict):
        self._producer.produce(
            topic=topic,
            key=order_id,
            value=json.dumps(command).encode("utf-8"),
        )
        self._producer.poll(0)

    def _build_command(self, saga: SagaState, step: SagaStep,
                       is_compensation: bool, extra_payload: dict = None) -> dict:
        return {
            "command_id": str(uuid.uuid4()),
            "saga_id": saga.saga_id,
            "order_id": saga.order_id,
            "command_type": step.compensate_command if is_compensation else step.forward_command,
            "step_number": step.step_number,
            "is_compensation": is_compensation,
            "payload": {**saga.order_data, **(extra_payload or {})},
            "timestamp": int(time.time() * 1000),
        }

    # --- Forward execution ---

    def start_saga(self, order_id: str, order_data: dict):
        saga_id = str(uuid.uuid4())
        saga = SagaState(
            saga_id=saga_id, order_id=order_id,
            status=SagaStatus.STARTED, current_step=0,
            order_data=order_data,
        )
        self._sagas[saga_id] = saga
        self._execute_next_step(saga)

    def _execute_next_step(self, saga: SagaState):
        if saga.current_step >= len(SAGA_STEPS):
            saga.status = SagaStatus.COMPLETED
            self._send("order.commands", saga.order_id, {
                "command_type": "order.confirmed",
                "saga_id": saga.saga_id,
                "order_id": saga.order_id,
                "timestamp": int(time.time() * 1000),
            })
            return

        step = SAGA_STEPS[saga.current_step]
        saga.status = step.pending_status
        cmd = self._build_command(saga, step, is_compensation=False)
        self._send(step.forward_topic, saga.order_id, cmd)

    # --- Compensation (reverse order) ---

    def _start_compensation(self, saga: SagaState, reason: str):
        saga.status = SagaStatus.COMPENSATING
        saga.failure_reason = reason
        saga.compensation_index = len(saga.completed_steps) - 1
        self._execute_next_compensation(saga)

    def _execute_next_compensation(self, saga: SagaState):
        if saga.compensation_index < 0:
            saga.status = SagaStatus.FAILED
            self._send("order.commands", saga.order_id, {
                "command_type": "order.failed",
                "saga_id": saga.saga_id,
                "order_id": saga.order_id,
                "failure_reason": saga.failure_reason,
                "timestamp": int(time.time() * 1000),
            })
            return

        step = SAGA_STEPS[saga.compensation_index]
        # Enrich with forward reply data (e.g., charge_id for refund)
        extra = saga.completed_steps[saga.compensation_index]
        cmd = self._build_command(saga, step, is_compensation=True,
                                  extra_payload=extra)
        self._send(step.compensate_topic, saga.order_id, cmd)

    # --- Reply handling ---

    def handle_reply(self, reply: dict):
        saga = self._sagas.get(reply["saga_id"])
        if not saga:
            return

        if saga.status == SagaStatus.COMPENSATING:
            if reply["status"] in ("SUCCEEDED", "COMPENSATED"):
                saga.compensation_index -= 1
                self._execute_next_compensation(saga)
            else:
                # Compensation failed — requires manual intervention
                print(f"ALERT: compensation failed saga={saga.saga_id} reply={reply}")
            return

        # Forward step reply
        if reply["status"] == "SUCCEEDED":
            saga.completed_steps.append(reply.get("payload", {}))
            saga.current_step += 1
            self._execute_next_step(saga)
        elif reply["status"] == "FAILED":
            self._start_compensation(saga, reply.get("failure_reason", "unknown"))

    # --- Main loop ---

    def run(self):
        while True:
            msg = self._consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    print(f"Consumer error: {msg.error()}")
                continue

            data = json.loads(msg.value().decode("utf-8"))
            topic = msg.topic()

            if topic == "order.commands" and data.get("command_type") == "order.create":
                self.start_saga(data["order_id"], data.get("payload", {}))
            elif topic == "saga.replies":
                self.handle_reply(data)

            self._consumer.commit(asynchronous=False)
```

---

## Participant Service Pattern

Every participant handles both forward and compensation commands on the same topic:

```python
class PaymentService:
    """Handles payment.charge (forward) and payment.refund (compensation)."""

    def __init__(self, bootstrap_servers: str):
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "acks": "all",
            "enable.idempotence": True,
        })
        self._consumer = Consumer({
            "bootstrap.servers": bootstrap_servers,
            "group.id": "payment-service",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self._consumer.subscribe(["payment.commands"])
        # Production: use a DB table for idempotency (see persistence section)
        self._processed: set[str] = set()

    def _reply(self, saga_id: str, order_id: str, command_id: str,
               step_number: int, status: str, payload: dict = None,
               failure_reason: str = None):
        self._producer.produce(
            topic="saga.replies",
            key=order_id,
            value=json.dumps({
                "reply_id": str(uuid.uuid4()),
                "saga_id": saga_id,
                "order_id": order_id,
                "command_id": command_id,
                "step_number": step_number,
                "status": status,
                "failure_reason": failure_reason,
                "payload": payload or {},
                "timestamp": int(time.time() * 1000),
            }).encode("utf-8"),
        )
        self._producer.poll(0)

    def _handle_charge(self, cmd: dict):
        # Idempotency check
        idempotency_key = cmd["payload"].get("idempotency_key", cmd["command_id"])
        if idempotency_key in self._processed:
            self._reply(cmd["saga_id"], cmd["order_id"], cmd["command_id"],
                        cmd["step_number"], "SUCCEEDED",
                        payload={"charge_id": "already-processed"})
            return

        try:
            charge_id = f"ch_{uuid.uuid4().hex[:12]}"
            amount = cmd["payload"].get("amount_cents", 0)
            # ... actual payment gateway call ...
            self._processed.add(idempotency_key)
            self._reply(cmd["saga_id"], cmd["order_id"], cmd["command_id"],
                        cmd["step_number"], "SUCCEEDED",
                        payload={"charge_id": charge_id, "amount_cents": str(amount)})
        except Exception as e:
            self._reply(cmd["saga_id"], cmd["order_id"], cmd["command_id"],
                        cmd["step_number"], "FAILED", failure_reason=str(e))

    def _handle_refund(self, cmd: dict):
        charge_id = cmd["payload"].get("charge_id", "unknown")
        # ... actual refund call ...
        refund_id = f"rf_{uuid.uuid4().hex[:12]}"
        self._reply(cmd["saga_id"], cmd["order_id"], cmd["command_id"],
                    cmd["step_number"], "COMPENSATED",
                    payload={"refund_id": refund_id})

    def run(self):
        while True:
            msg = self._consumer.poll(1.0)
            if msg is None or msg.error():
                continue
            cmd = json.loads(msg.value().decode("utf-8"))
            if cmd["command_type"] == "payment.charge":
                self._handle_charge(cmd)
            elif cmd["command_type"] == "payment.refund":
                self._handle_refund(cmd)
            self._consumer.commit(asynchronous=False)
```

### Participant Template

All participant services follow the same structure:

```python
class SagaParticipant:
    """Base pattern — subclass and implement forward() and compensate()."""

    def __init__(self, bootstrap_servers: str, group_id: str,
                 command_topic: str, forward_type: str, compensate_type: str):
        self._forward_type = forward_type
        self._compensate_type = compensate_type
        # ... producer, consumer setup (same as PaymentService) ...

    def handle(self, cmd: dict):
        if cmd["command_type"] == self._forward_type:
            self.forward(cmd)
        elif cmd["command_type"] == self._compensate_type:
            self.compensate(cmd)

    def forward(self, cmd: dict):
        """Override: execute forward business logic, call self._reply()."""
        raise NotImplementedError

    def compensate(self, cmd: dict):
        """Override: execute undo business logic, call self._reply()."""
        raise NotImplementedError
```

---

## Saga State Persistence

In-memory state is lost on restart. Use PostgreSQL for production:

### Schema

```sql
CREATE TABLE saga_state (
    saga_id            UUID PRIMARY KEY,
    order_id           UUID NOT NULL,
    status             VARCHAR(30) NOT NULL,
    current_step       INT NOT NULL DEFAULT 0,
    order_data         JSONB NOT NULL,
    completed_steps    JSONB NOT NULL DEFAULT '[]'::jsonb,
    compensation_index INT DEFAULT -1,
    failure_reason     TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_saga_order_id ON saga_state(order_id);
CREATE INDEX idx_saga_status ON saga_state(status)
    WHERE status NOT IN ('COMPLETED', 'FAILED');  -- Only index active sagas

-- Per-service command deduplication
CREATE TABLE processed_commands (
    command_id   UUID PRIMARY KEY,
    service_name VARCHAR(50) NOT NULL,
    result       JSONB,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Atomic State Update Pattern

```python
async def handle_reply_persistent(self, reply: dict, db_pool):
    """Update saga state and commit offset atomically (effectively)."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            # Load current state
            row = await conn.fetchrow(
                "SELECT * FROM saga_state WHERE saga_id = $1 FOR UPDATE",
                reply["saga_id"],
            )
            if not row:
                return

            saga = SagaState(**row)

            # Apply state transition (same logic as in-memory version)
            if reply["status"] == "SUCCEEDED":
                saga.completed_steps.append(reply.get("payload", {}))
                saga.current_step += 1
            elif reply["status"] == "FAILED":
                saga.status = SagaStatus.COMPENSATING
                saga.failure_reason = reply.get("failure_reason")
                saga.compensation_index = len(saga.completed_steps) - 1

            # Persist new state
            await conn.execute(
                """UPDATE saga_state
                   SET status=$2, current_step=$3, completed_steps=$4,
                       compensation_index=$5, failure_reason=$6, updated_at=NOW()
                   WHERE saga_id=$1""",
                saga.saga_id, saga.status, saga.current_step,
                json.dumps(saga.completed_steps),
                saga.compensation_index, saga.failure_reason,
            )

    # State is persisted — now send the next command outside the transaction
    # If we crash here, on restart we reload state and re-send (idempotent participants handle duplicates)
    self._execute_from_state(saga)
```

---

## Timeout Handling

Detect stuck steps and trigger compensation:

```python
import threading

STEP_TIMEOUT_SECONDS = 30


class SagaTimeoutManager:
    """Starts a timer per saga step. On timeout, triggers compensation."""

    def __init__(self, orchestrator: OrderSagaOrchestrator):
        self._orchestrator = orchestrator
        self._timers: dict[str, threading.Timer] = {}

    def start_timer(self, saga: SagaState):
        self.cancel_timer(saga.saga_id)
        timer = threading.Timer(
            STEP_TIMEOUT_SECONDS,
            self._on_timeout,
            args=[saga.saga_id],
        )
        timer.daemon = True
        timer.start()
        self._timers[saga.saga_id] = timer

    def cancel_timer(self, saga_id: str):
        timer = self._timers.pop(saga_id, None)
        if timer:
            timer.cancel()

    def _on_timeout(self, saga_id: str):
        saga = self._orchestrator._sagas.get(saga_id)
        if saga and saga.status not in (
            SagaStatus.COMPLETED, SagaStatus.FAILED, SagaStatus.COMPENSATING
        ):
            step = SAGA_STEPS[saga.current_step]
            self._orchestrator._start_compensation(
                saga, f"timeout_at_{step.forward_command}"
            )
```

### Production: Database-Based Timeout (Cron/Scheduler)

```sql
-- Find timed-out sagas (no update in 30 seconds, still active)
SELECT saga_id, order_id, status, current_step
FROM saga_state
WHERE status NOT IN ('COMPLETED', 'FAILED')
  AND updated_at < NOW() - INTERVAL '30 seconds';
```

```python
# Scheduler job (runs every 10 seconds)
async def check_timeouts(db_pool, orchestrator):
    rows = await db_pool.fetch("""
        UPDATE saga_state
        SET status = 'COMPENSATING',
            failure_reason = 'timeout',
            updated_at = NOW()
        WHERE status NOT IN ('COMPLETED', 'FAILED', 'COMPENSATING')
          AND updated_at < NOW() - INTERVAL '30 seconds'
        RETURNING saga_id, order_id, current_step, completed_steps, order_data
    """)
    for row in rows:
        saga = SagaState(**row)
        saga.compensation_index = len(saga.completed_steps) - 1
        orchestrator._execute_next_compensation(saga)
```

---

## Idempotency Requirements

Saga commands may be retried (orchestrator crash + restart, Kafka redelivery). Every participant **must** be idempotent.

| Technique | How | Best For |
|-----------|-----|----------|
| **Idempotency key in command** | `idempotency_key: "order-456-payment"` — check before processing | Payment gateways, external APIs |
| **Command ID dedup table** | Store `command_id` in `processed_commands` table | General purpose |
| **Upsert/PUT semantics** | `INSERT ... ON CONFLICT DO UPDATE` | Database writes |
| **Conditional update** | `UPDATE ... WHERE status = 'pending'` | State transitions |

```python
# Idempotent participant using command_id dedup
async def handle_command_idempotent(self, cmd: dict, db_pool):
    async with db_pool.acquire() as conn:
        # Check if already processed
        existing = await conn.fetchrow(
            "SELECT result FROM processed_commands WHERE command_id = $1",
            cmd["command_id"],
        )
        if existing:
            # Already processed — re-send the same reply
            self._reply_from_stored(cmd, existing["result"])
            return

        async with conn.transaction():
            # Process the command
            result = self._execute_business_logic(cmd)

            # Record as processed (atomically with business logic)
            await conn.execute(
                """INSERT INTO processed_commands (command_id, service_name, result)
                   VALUES ($1, $2, $3)""",
                cmd["command_id"], "payment-service", json.dumps(result),
            )

    # Send reply
    self._reply(cmd, "SUCCEEDED", payload=result)
```

---

## Compensation Design Rules

### What Makes a Good Compensating Action

| Rule | Example |
|------|---------|
| **Semantic undo, not technical rollback** | Refund the charge (new transaction), don't DELETE the charge record |
| **Must be idempotent** | Calling `payment.refund` twice for the same charge_id should refund once |
| **Must always succeed eventually** | Compensations should retry until they work — they cannot "fail" permanently |
| **May leave evidence** | The charge + refund both appear in history (unlike a rollback that erases) |
| **Order matters** | Compensate in reverse order: undo shipping before inventory before payment |

### Compensation Failure Handling

If a compensation itself fails:

```
Strategy 1: Retry with backoff (preferred)
  compensation.failed → wait → retry → retry → ... → succeeded

Strategy 2: Dead letter + manual intervention
  compensation.failed after N retries → produce to saga.dlq
  → Ops team resolves manually

Strategy 3: Compensation saga (avoid if possible)
  compensation.failed → start a new sub-saga to undo the undo
  → Complexity explosion — only for critical financial flows
```

```python
MAX_COMPENSATION_RETRIES = 5

def _handle_compensation_failure(self, saga: SagaState, reply: dict):
    retry_count = saga.order_data.get("_compensation_retries", 0)
    if retry_count < MAX_COMPENSATION_RETRIES:
        saga.order_data["_compensation_retries"] = retry_count + 1
        # Retry the same compensation step
        step = SAGA_STEPS[saga.compensation_index]
        cmd = self._build_command(saga, step, is_compensation=True,
                                  extra_payload=saga.completed_steps[saga.compensation_index])
        self._send(step.compensate_topic, saga.order_id, cmd)
    else:
        # Dead letter — manual intervention required
        self._send("saga.dlq", saga.order_id, {
            "saga_id": saga.saga_id,
            "order_id": saga.order_id,
            "stuck_at_compensation_step": saga.compensation_index,
            "failure_reason": reply.get("failure_reason"),
            "timestamp": int(time.time() * 1000),
        })
```

---

## Complete Scenario Traces

### Happy Path

```
Topic              Key        Event
──────             ───        ─────
order.commands     ord-456    order.create {items: [...], amount: 9999}
payment.commands   ord-456    payment.charge {amount: 9999, idempotency_key: "ord-456-pay"}
saga.replies       ord-456    {step: 1, status: SUCCEEDED, charge_id: "ch_abc"}
inventory.commands ord-456    inventory.reserve {items: [{sku: "W1", qty: 2}]}
saga.replies       ord-456    {step: 2, status: SUCCEEDED, reservation_id: "res-789"}
shipping.commands  ord-456    shipping.schedule {address: {...}}
saga.replies       ord-456    {step: 3, status: SUCCEEDED, shipment_id: "ship-012"}
order.commands     ord-456    order.confirmed
```

### Failure at Step 2 → Compensate Step 1

```
Topic              Key        Event
──────             ───        ─────
order.commands     ord-789    order.create {items: [{sku: "W2", qty: 100}], amount: 4999}
payment.commands   ord-789    payment.charge {amount: 4999}
saga.replies       ord-789    {step: 1, status: SUCCEEDED, charge_id: "ch_def"}
inventory.commands ord-789    inventory.reserve {items: [{sku: "W2", qty: 100}]}
saga.replies       ord-789    {step: 2, status: FAILED, reason: "insufficient_stock"}
── COMPENSATION (reverse order) ──
payment.commands   ord-789    payment.refund {charge_id: "ch_def", amount: 4999}
saga.replies       ord-789    {step: 1, status: COMPENSATED, refund_id: "rf_ghi"}
order.commands     ord-789    order.failed {reason: "insufficient_stock"}
```

### Failure at Step 3 → Compensate Steps 2, 1

```
Topic              Key        Event
──────             ───        ─────
order.commands     ord-321    order.create {items: [...], amount: 2999, address: {...}}
payment.commands   ord-321    payment.charge {amount: 2999}
saga.replies       ord-321    {step: 1, status: SUCCEEDED, charge_id: "ch_xyz"}
inventory.commands ord-321    inventory.reserve {items: [...]}
saga.replies       ord-321    {step: 2, status: SUCCEEDED, reservation_id: "res-456"}
shipping.commands  ord-321    shipping.schedule {address: {...}}
saga.replies       ord-321    {step: 3, status: FAILED, reason: "address_undeliverable"}
── COMPENSATION (reverse: step 2, then step 1) ──
inventory.commands ord-321    inventory.release {reservation_id: "res-456"}
saga.replies       ord-321    {step: 2, status: COMPENSATED}
payment.commands   ord-321    payment.refund {charge_id: "ch_xyz", amount: 2999}
saga.replies       ord-321    {step: 1, status: COMPENSATED, refund_id: "rf_abc"}
order.commands     ord-321    order.failed {reason: "address_undeliverable"}
```

---

## Monitoring

### Key Metrics

| Metric | Source | Alert When |
|--------|--------|------------|
| Active sagas count | `SELECT COUNT(*) FROM saga_state WHERE status NOT IN ('COMPLETED','FAILED')` | > threshold (sagas piling up) |
| Saga completion rate | `COMPLETED / (COMPLETED + FAILED)` over time | Drops below 95% |
| Average saga duration | `AVG(updated_at - created_at) WHERE status = 'COMPLETED'` | Exceeds SLA |
| Stuck sagas | `WHERE updated_at < NOW() - INTERVAL '5 minutes' AND status NOT IN (...)` | Any exist |
| Dead letter queue depth | Consumer lag on `saga.dlq` topic | > 0 |
| Compensation rate | `FAILED / total` over time | Spikes |

### Consumer Group Lag

```bash
# Orchestrator lag — if growing, orchestrator can't keep up with replies
bin/kafka-consumer-groups.sh --describe --group order-saga-orchestrator \
  --bootstrap-server localhost:9092

# Participant lag — if growing, a service is slow
bin/kafka-consumer-groups.sh --describe --group payment-service \
  --bootstrap-server localhost:9092
```

---

## Summary: Decision Framework

```
Do you need multi-service coordination?
  │
  ├─ No → Single DB transaction or transactional outbox
  │
  └─ Yes → Is strong consistency required?
            │
            ├─ Yes → Consider redesigning to single-service ownership
            │        (sagas provide eventual, not strong consistency)
            │
            └─ No → How many steps?
                     │
                     ├─ 2 steps → Choreography (simpler)
                     │
                     └─ 3+ steps → Orchestration (recommended)
                                    │
                                    ├─ Define steps + compensation pairs
                                    ├─ Build state machine
                                    ├─ Persist state in PostgreSQL
                                    ├─ Make all participants idempotent
                                    └─ Add timeout → compensation trigger
```
