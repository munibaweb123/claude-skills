# Handoffs

Deep reference for agent-to-agent handoffs in the OpenAI Agents SDK.

---

## Overview

Handoffs allow one agent to transfer control to another agent within a single `Runner.run()` call. The active agent changes, and the new agent takes over responding.

### When to Use Handoffs vs Agents-as-Tools

| Pattern | When | Control |
|---------|------|---------|
| **Handoffs** | Specialist should respond directly to user | Specialist becomes active agent |
| **Agents as Tools** | Orchestrator needs to combine results | Orchestrator retains control |

---

## Basic Handoff

Add agents to the `handoffs` list:

```python
from agents import Agent

billing_agent = Agent(
    name="Billing Agent",
    handoff_description="Handles billing and payment questions",
    instructions="You handle billing inquiries.",
)

support_agent = Agent(
    name="Support Agent",
    handoff_description="Handles general support questions",
    instructions="You handle general support inquiries.",
)

triage_agent = Agent(
    name="Triage",
    instructions="Route questions to the appropriate specialist.",
    handoffs=[billing_agent, support_agent],
)
```

The LLM sees each handoff as a tool named `transfer_to_<agent_name>` with the `handoff_description` as the tool description.

---

## Advanced Handoff Configuration

### handoff() Function

```python
from agents import handoff, Agent
from pydantic import BaseModel

class HandoffMetadata(BaseModel):
    reason: str
    priority: str

def on_handoff_callback(ctx):
    print(f"Handing off with context: {ctx}")

h = handoff(
    agent=billing_agent,
    tool_name_override="route_to_billing",         # Custom tool name
    tool_description_override="Transfer to billing for payment issues",
    on_handoff=on_handoff_callback,                 # Callback on handoff
    input_type=HandoffMetadata,                     # Structured metadata from model
    input_filter=filter_function,                   # Filter input sent to next agent
    is_enabled=True,                                # Boolean or callable
    nest_handoff_history=True,                      # Per-handoff override
)

triage = Agent(name="Triage", handoffs=[h])
```

### input_type

`input_type` is for model-generated metadata (reason, language, priority), NOT for selecting destination agents. Use separate handoff registrations for multiple destinations.

```python
from pydantic import BaseModel

class EscalationInfo(BaseModel):
    reason: str
    urgency: str  # "low", "medium", "high"

h = handoff(
    agent=escalation_agent,
    input_type=EscalationInfo,
)
```

---

## HandoffInputData

Data available in input filters and callbacks:

```python
from dataclasses import dataclass

@dataclass
class HandoffInputData:
    input_history: list      # Full conversation history
    pre_handoff_items: list  # Items before this handoff
    new_items: list          # Items generated in this run
    input_items: list        # Combined input items
    run_context: RunContextWrapper
```

---

## Input Filters

Control what history is sent to the next agent after a handoff:

### Per-Handoff Filter

```python
def filter_sensitive_data(data: HandoffInputData) -> list:
    """Remove tool calls from history before sending to next agent."""
    return [item for item in data.input_history if item.get("type") != "tool_call"]

h = handoff(
    agent=target_agent,
    input_filter=filter_sensitive_data,
)
```

### Global Filter via RunConfig

```python
from agents import RunConfig

config = RunConfig(handoff_input_filter=global_filter_fn)
```

Per-handoff `input_filter` takes precedence over global `handoff_input_filter`.

### Built-in Filters

```python
from agents.extensions.handoff_filters import remove_all_tools

h = handoff(
    agent=target_agent,
    input_filter=remove_all_tools,  # Removes all tool calls from history
)
```

---

## History Management

### nest_handoff_history (Beta)

Collapses the conversation transcript into a single `<CONVERSATION HISTORY>` block when handing off:

```python
from agents import RunConfig

# Global setting
config = RunConfig(nest_handoff_history=True)

# Per-handoff override
h = handoff(agent=target_agent, nest_handoff_history=True)
```

### Custom History Mapper

Replace the built-in summary with a custom mapping function:

```python
from agents import RunConfig

def custom_mapper(history: list) -> list:
    """Custom history transformation."""
    # Return transformed history
    return history[-5:]  # Keep only last 5 items

config = RunConfig(handoff_history_mapper=custom_mapper)
```

### Conversation History Wrappers

Customize the wrapper text around nested history:

```python
from agents import set_conversation_history_wrappers, reset_conversation_history_wrappers

set_conversation_history_wrappers(
    start="<PREVIOUS_CONTEXT>",
    end="</PREVIOUS_CONTEXT>"
)

# Reset to defaults
reset_conversation_history_wrappers()
```

---

## Handoff Prompt Utilities

```python
from agents.extensions.handoff_prompt import (
    RECOMMENDED_PROMPT_PREFIX,
    prompt_with_handoff_instructions,
)

# Get recommended prompt prefix for agents with handoffs
agent = Agent(
    name="Triage",
    instructions=prompt_with_handoff_instructions(
        "Route questions to the right specialist."
    ),
    handoffs=[billing_agent, support_agent],
)
```

---

## Important Boundaries

| Rule | Detail |
|------|--------|
| **Same run** | Handoffs remain within a single `Runner.run()` call |
| **Input guardrails** | Apply only to the **first** agent |
| **Output guardrails** | Apply only to the **final** agent |
| **Tool guardrails** | Apply to function-tool calls within the workflow |
| **input_type** | For metadata only, not for routing decisions |
| **Separate handoffs** | Create separate handoff registrations for multiple destinations |

---

## Example: Multi-Tier Support

```python
from agents import Agent, handoff

# Tier 1: General support
general_agent = Agent(
    name="General Support",
    handoff_description="Handles general inquiries and FAQ",
    instructions="Answer general questions. Escalate complex issues.",
)

# Tier 2: Technical support
technical_agent = Agent(
    name="Technical Support",
    handoff_description="Handles technical issues and debugging",
    instructions="Help with technical problems. Escalate billing to billing agent.",
)

# Tier 3: Billing
billing_agent = Agent(
    name="Billing",
    handoff_description="Handles billing, payments, and refunds",
    instructions="Handle billing inquiries and process refund requests.",
)

# Triage routes to appropriate tier
triage = Agent(
    name="Triage",
    instructions="Classify the user's issue and route to the appropriate team.",
    handoffs=[general_agent, technical_agent, billing_agent],
)

# Agents can also hand off to each other
general_agent.handoffs = [technical_agent, billing_agent]
technical_agent.handoffs = [billing_agent]
```
