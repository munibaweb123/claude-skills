# Guardrails

Deep reference for input, output, and tool guardrails in the OpenAI Agents SDK.

---

## Overview

Guardrails validate agent input and output to ensure safety and correctness. When a guardrail's `tripwire_triggered` is `True`, the run is halted and an exception is raised.

### Guardrail Types

| Decorator | Scope | Exception |
|-----------|-------|-----------|
| `@input_guardrail` | Validates agent input | `InputGuardrailTripwireTriggered` |
| `@output_guardrail` | Validates agent output | `OutputGuardrailTripwireTriggered` |
| `@tool_input_guardrail` | Validates tool input before execution | N/A (rejects tool call) |
| `@tool_output_guardrail` | Validates tool output after execution | N/A (rejects tool output) |

---

## Input Guardrails

Run before or alongside the agent to validate user input:

```python
from agents import input_guardrail, GuardrailFunctionOutput, Agent, Runner

@input_guardrail
async def block_harmful_content(ctx, agent, input) -> GuardrailFunctionOutput:
    """Check input for harmful content."""
    harmful_keywords = ["hack", "exploit", "attack"]
    input_text = str(input).lower()

    if any(keyword in input_text for keyword in harmful_keywords):
        return GuardrailFunctionOutput(
            output_info="Blocked: harmful content detected",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(
        output_info="Input is safe",
        tripwire_triggered=False,
    )

agent = Agent(
    name="Safe Agent",
    instructions="You are a helpful assistant.",
    input_guardrails=[block_harmful_content],
)

# Usage with exception handling
from agents import InputGuardrailTripwireTriggered

try:
    result = await Runner.run(agent, "How do I hack a server?")
except InputGuardrailTripwireTriggered as e:
    print(f"Input blocked: {e}")
```

### Function Signature

```python
@input_guardrail
async def my_guardrail(
    ctx: RunContextWrapper[ContextType],
    agent: Agent,
    input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    return GuardrailFunctionOutput(
        output_info="any serializable data for logging",
        tripwire_triggered=False,  # True to halt the run
    )
```

---

## Output Guardrails

Validate the agent's final output:

```python
from agents import output_guardrail, GuardrailFunctionOutput, Agent

@output_guardrail
async def check_output_quality(ctx, agent, output) -> GuardrailFunctionOutput:
    """Ensure output meets quality standards."""
    output_text = str(output)

    if len(output_text) < 10:
        return GuardrailFunctionOutput(
            output_info="Output too short",
            tripwire_triggered=True,
        )
    if "I don't know" in output_text:
        return GuardrailFunctionOutput(
            output_info="Agent gave uncertain response",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(
        output_info="Output quality OK",
        tripwire_triggered=False,
    )

agent = Agent(
    name="Quality Agent",
    output_guardrails=[check_output_quality],
)
```

### Function Signature

```python
@output_guardrail
async def my_output_guardrail(
    ctx: RunContextWrapper[ContextType],
    agent: Agent,
    output: OutputType,  # str or typed output if output_type is set
) -> GuardrailFunctionOutput:
    return GuardrailFunctionOutput(
        output_info="details",
        tripwire_triggered=False,
    )
```

---

## Tool Guardrails

Validate tool inputs before execution and tool outputs after execution:

### Tool Input Guardrail

```python
from agents import tool_input_guardrail, ToolGuardrailFunctionOutput

@tool_input_guardrail
def validate_tool_input(data) -> ToolGuardrailFunctionOutput:
    """Validate tool inputs before execution."""
    # Check for dangerous operations
    if "delete" in str(data).lower():
        return ToolGuardrailFunctionOutput.reject_content(
            "Deletion operations are not allowed"
        )
    return ToolGuardrailFunctionOutput.allow()
```

### Tool Output Guardrail

```python
from agents import tool_output_guardrail, ToolGuardrailFunctionOutput

@tool_output_guardrail
def validate_tool_output(data) -> ToolGuardrailFunctionOutput:
    """Validate tool results after execution."""
    if "error" in str(data).lower():
        return ToolGuardrailFunctionOutput.reject_content(
            "Tool returned an error"
        )
    return ToolGuardrailFunctionOutput.allow()
```

### ToolGuardrailFunctionOutput Methods

| Method | Effect |
|--------|--------|
| `.allow()` | Permit the tool call to proceed (or accept output) |
| `.reject_content(message)` | Skip tool execution / reject output, send message to model |

---

## GuardrailFunctionOutput

```python
from agents import GuardrailFunctionOutput

output = GuardrailFunctionOutput(
    output_info="any data",        # Logged for debugging/auditing
    tripwire_triggered=False,      # True = halt the run with exception
)
```

---

## Execution Modes

### Parallel (Default)

Guardrail and agent run concurrently:

```python
agent = Agent(
    name="Agent",
    input_guardrails=[my_guardrail],  # Runs in parallel with agent by default
)
```

**Warning:** The agent may have already consumed tokens and executed tools before the guardrail cancels the run.

### Blocking

Guardrail completes before agent starts:

```python
# Set run_in_parallel=False on the guardrail
@input_guardrail
async def blocking_guardrail(ctx, agent, input) -> GuardrailFunctionOutput:
    # This completes before the agent starts
    return GuardrailFunctionOutput(output_info="OK", tripwire_triggered=False)

blocking_guardrail.run_in_parallel = False
```

Prevents wasted tokens if the guardrail would trigger a tripwire.

---

## Global Guardrails via RunConfig

Apply guardrails across all agents in a run:

```python
from agents import RunConfig

config = RunConfig(
    input_guardrails=[global_input_guard],
    output_guardrails=[global_output_guard],
)

result = await Runner.run(agent, "Hello", run_config=config)
```

---

## Guardrail Boundaries in Multi-Agent Workflows

| Guardrail Type | Applies To |
|----------------|-----------|
| Input guardrails | **First agent only** |
| Output guardrails | **Last agent only** |
| Tool guardrails | **Every function_tool invocation** |

Does NOT apply to: handoffs, hosted tools, built-in execution tools, `Agent.as_tool()`.

---

## Example: LLM-Based Content Moderation

```python
from agents import Agent, Runner, input_guardrail, GuardrailFunctionOutput

moderation_agent = Agent(
    name="Moderator",
    instructions="Classify if input is safe or harmful. Reply with SAFE or HARMFUL.",
    output_type=str,
)

@input_guardrail
async def llm_content_check(ctx, agent, input) -> GuardrailFunctionOutput:
    """Use a separate agent to moderate input."""
    result = await Runner.run(moderation_agent, str(input))
    is_harmful = "HARMFUL" in result.final_output.upper()
    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=is_harmful,
    )

main_agent = Agent(
    name="Assistant",
    instructions="You are a helpful assistant.",
    input_guardrails=[llm_content_check],
)
```
