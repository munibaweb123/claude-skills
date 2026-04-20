# Production Deployment

Deep reference for deploying OpenAI Agents SDK applications in production.

---

## Production Checklist

### Required

- [ ] Set `max_turns` on all `Runner.run()` calls to prevent infinite loops
- [ ] Handle `MaxTurnsExceeded` and `AgentsException` exceptions
- [ ] Set `trace_include_sensitive_data=False` for PII protection
- [ ] Use guardrails on all user-facing agents
- [ ] Call `flush_traces()` in worker processes before exit
- [ ] Use structured outputs (`output_type`) for downstream processing
- [ ] Set `OPENAI_API_KEY` via environment variable (not hardcoded)

### Recommended

- [ ] Use sessions for multi-turn conversations
- [ ] Implement HITL for destructive operations
- [ ] Configure retry settings for resilience
- [ ] Enable tracing for debugging and monitoring
- [ ] Use `RunConfig` for consistent configuration
- [ ] Cache MCP tool lists with `cache_tools_list=True`
- [ ] Set up external trace processor (Langfuse, Braintrust, etc.)
- [ ] Use `call_model_input_filter` for context window management

---

## Error Handling Patterns

### Comprehensive Error Handling

```python
from agents import (
    Agent, Runner, RunConfig, AgentsException, MaxTurnsExceeded,
    ModelBehaviorError, ToolTimeoutError, UserError,
    InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered,
)

async def run_agent_safely(agent, user_input, session=None):
    try:
        result = await Runner.run(
            agent,
            user_input,
            session=session,
            max_turns=10,
            run_config=RunConfig(
                trace_include_sensitive_data=False,
                workflow_name="production",
            ),
        )
        return {"status": "success", "output": result.final_output}

    except MaxTurnsExceeded:
        return {"status": "error", "message": "Request too complex. Please simplify."}

    except InputGuardrailTripwireTriggered as e:
        return {"status": "blocked", "message": "Input did not pass safety checks."}

    except OutputGuardrailTripwireTriggered as e:
        return {"status": "blocked", "message": "Response did not pass safety checks."}

    except ToolTimeoutError as e:
        return {"status": "error", "message": "A tool operation timed out."}

    except ModelBehaviorError as e:
        return {"status": "error", "message": "Model produced invalid output. Retrying."}

    except AgentsException as e:
        return {"status": "error", "message": f"Agent error: {e}"}
```

### Max Turns Error Handler

```python
from agents import RunConfig, RunErrorHandlerInput, RunErrorHandlerResult

def handle_max_turns(data: RunErrorHandlerInput) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output="I couldn't complete this within the allowed steps. "
                     "Please try a simpler request.",
        include_in_history=False,
    )

config = RunConfig(error_handlers={"max_turns": handle_max_turns})
```

---

## Worker Process Patterns

### Celery

```python
from agents import Agent, Runner, trace, flush_traces

agent = Agent(name="Worker", instructions="Process tasks.")

@celery_app.task
def process_task(prompt: str) -> str:
    try:
        with trace("celery_task"):
            result = Runner.run_sync(agent, prompt, max_turns=10)
        return result.final_output
    except Exception as e:
        return f"Error: {e}"
    finally:
        flush_traces()  # Critical: flush before worker exits
```

### FastAPI

```python
from fastapi import FastAPI, HTTPException
from agents import Agent, Runner, RunConfig, SQLiteSession

app = FastAPI()
agent = Agent(name="API Agent", instructions="Help users.")

@app.post("/chat")
async def chat(user_id: str, message: str):
    session = SQLiteSession(user_id, "conversations.db")
    try:
        result = await Runner.run(
            agent,
            message,
            session=session,
            max_turns=10,
            run_config=RunConfig(trace_include_sensitive_data=False),
        )
        return {"response": result.final_output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Context Window Management

For long conversations, trim input before each LLM call:

```python
from agents import RunConfig, CallModelData, ModelInputData

def trim_context(data: CallModelData) -> ModelInputData:
    """Keep only recent messages to avoid context overflow."""
    messages = data.model_data.input
    if len(messages) > 20:
        # Keep system + last 15 messages
        messages = messages[:1] + messages[-15:]
    return ModelInputData(
        input=messages,
        instructions=data.model_data.instructions,
    )

config = RunConfig(call_model_input_filter=trim_context)
```

### Session-Level Limiting

```python
from agents import RunConfig, SessionSettings

config = RunConfig(
    session_settings=SessionSettings(limit=50),  # Last 50 items only
)
```

---

## Resilience Patterns

### Retry Configuration

```python
from agents import ModelSettings, ModelRetrySettings
from agents.models import retry_policies

production_settings = ModelSettings(
    retry=ModelRetrySettings(
        max_retries=4,
        backoff={
            "initial_delay": 0.5,
            "max_delay": 10.0,
            "multiplier": 2.0,
            "jitter": True,
        },
        policy=retry_policies.any(
            retry_policies.provider_suggested(),
            retry_policies.network_error(),
            retry_policies.http_status([408, 429, 500, 502, 503, 504]),
        ),
    ),
)
```

### Timeout on Tools

```python
@function_tool(timeout=10.0, timeout_behavior="error_as_result")
async def external_api_call(query: str) -> str:
    """Call external API with timeout protection."""
    response = await httpx.get(f"https://api.example.com/search?q={query}")
    return response.text
```

---

## Security Best Practices

### Input Validation

```python
from agents import input_guardrail, GuardrailFunctionOutput

@input_guardrail
async def validate_input(ctx, agent, input) -> GuardrailFunctionOutput:
    input_text = str(input)

    # Length check
    if len(input_text) > 10000:
        return GuardrailFunctionOutput(
            output_info="Input too long",
            tripwire_triggered=True,
        )

    # Prompt injection detection (use your preferred method)
    if suspicious_patterns(input_text):
        return GuardrailFunctionOutput(
            output_info="Suspicious input detected",
            tripwire_triggered=True,
        )

    return GuardrailFunctionOutput(output_info="OK", tripwire_triggered=False)
```

### Sensitive Data Protection

```python
from agents import RunConfig

config = RunConfig(
    trace_include_sensitive_data=False,  # No PII in traces
)

# Or globally via environment
# OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0
```

### Context Object Safety

```python
from dataclasses import dataclass

@dataclass
class SafeContext:
    user_id: str
    session_id: str
    # Do NOT put API keys, tokens, or passwords here
    # They will be serialized with RunState in HITL flows
```

---

## Monitoring and Observability

### Tracing Configuration

```python
from agents import RunConfig

config = RunConfig(
    workflow_name="production_chatbot",
    trace_metadata={
        "environment": "production",
        "version": "2.1.0",
        "region": "us-east-1",
    },
    group_id="batch_processing_20260421",
)
```

### External Trace Processors

```python
from agents import add_trace_processor

# Add your preferred external processor
# (Langfuse, Braintrust, Weights & Biases, etc.)
add_trace_processor(my_external_processor)
```

### Usage Tracking

```python
result = await Runner.run(agent, "Hello", context=ctx)

usage = result.context_wrapper.usage
log_metrics({
    "total_tokens": usage.total_tokens,
    "prompt_tokens": usage.prompt_tokens,
    "completion_tokens": usage.completion_tokens,
    "requests": usage.requests,
})
```

---

## Durable Execution

For long-running workflows, human-in-the-loop, and failure recovery:

| Framework | Use Case |
|-----------|----------|
| **Temporal** | Complex workflows with retries and timers |
| **Restate** | Durable execution with state management |
| **DBOS** | Database-backed durable execution |

These frameworks integrate with the Agents SDK for production-grade workflow orchestration.

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why | Fix |
|--------------|-----|-----|
| No `max_turns` | Agent can loop forever | Always set `max_turns` |
| Hardcoded API keys | Security risk | Use environment variables |
| No error handling | Crashes on model errors | Catch `AgentsException` |
| Secrets in context | Leaked via RunState serialization | Keep secrets in env vars |
| Missing `flush_traces()` | Lost traces in workers | Always flush in `finally` |
| Mixed session strategies | Runtime error | Use one: session OR conversation_id |
| No guardrails on user-facing agents | Safety risk | Always add input guardrails |
| Ignoring `reset_tool_choice` | Infinite tool loops | Keep default `True` |
