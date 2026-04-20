# Tracing

Deep reference for tracing and observability in the OpenAI Agents SDK.

---

## Overview

The SDK includes built-in tracing that records agent runs, LLM calls, tool executions, and handoffs. Traces are sent to the OpenAI backend by default and can be viewed in the OpenAI dashboard.

---

## Trace Management

### Context Manager

```python
from agents import trace, Runner

with trace(
    workflow_name="customer_support",
    trace_id="trace_abc123def456",    # Optional custom ID
    group_id="group_xyz",              # Optional grouping
    metadata={"customer_id": "123"},   # Optional metadata
    disabled=False,                    # Disable this trace
):
    result = await Runner.run(agent, "Hello")
```

### Manual Lifecycle

```python
from agents import trace

t = trace("my_workflow")
t.start()
try:
    result = await Runner.run(agent, "Hello")
finally:
    t.finish()
```

### Trace ID Format

`trace_<32_alphanumeric_characters>` (e.g., `trace_abc123def456ghi789jkl012mno345`)

---

## Span Functions

Spans represent individual operations within a trace:

| Function | Purpose |
|----------|---------|
| `agent_span()` | Wraps agent execution |
| `generation_span()` | Wraps LLM generations |
| `function_span()` | Wraps function tool calls |
| `guardrail_span()` | Wraps guardrail operations |
| `handoff_span()` | Wraps agent handoffs |
| `transcription_span()` | Wraps speech-to-text |
| `speech_span()` | Wraps text-to-speech |
| `speech_group_span()` | Parent container for related audio spans |
| `custom_span()` | Custom span tracking |

### Custom Span Example

```python
from agents import custom_span

with custom_span(name="data_processing"):
    # Your custom code
    processed = process_data(raw_data)
```

---

## Configuration

### Via RunConfig

```python
from agents import RunConfig

config = RunConfig(
    tracing_disabled=False,
    trace_include_sensitive_data=False,   # Exclude PII
    workflow_name="my_workflow",
    trace_id="trace_custom_id",
    group_id="group_abc",
    trace_metadata={"env": "production"},
    tracing={"api_key": "sk-separate-key"},  # Separate tracing key
)
```

### Via Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_AGENTS_DISABLE_TRACING=1` | Disable tracing entirely |
| `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0` | Exclude sensitive data (default) |

### Programmatic Configuration

```python
from agents import (
    set_tracing_export_api_key,
    set_tracing_disabled,
    add_trace_processor,
    set_trace_processors,
)

# Separate key for tracing (useful for non-OpenAI model providers)
set_tracing_export_api_key("sk-tracing-key")

# Disable tracing globally
set_tracing_disabled(True)

# Add a supplementary trace processor
add_trace_processor(my_custom_processor)

# Replace all default processors
set_trace_processors([my_processor])
```

---

## Default Architecture

```
TraceProvider
  └─ BatchTraceProcessor (batches every few seconds)
       └─ BackendSpanExporter (sends to OpenAI backend)
```

---

## Flushing Traces

**Critical for long-running workers** (Celery, background jobs):

```python
from agents import flush_traces

# Celery example
@celery_app.task
def run_agent_task(prompt: str):
    try:
        with trace("celery_task"):
            result = Runner.run_sync(agent, prompt)
        return result.final_output
    finally:
        flush_traces()  # Blocks until buffered traces are exported
```

**Always call `flush_traces()` before process exit in worker environments.**

---

## External Integrations

The SDK supports 25+ external trace processors:

| Integration | Package |
|-------------|---------|
| Weights & Biases | `weave` |
| Arize Phoenix | `arize-phoenix` |
| MLflow | `mlflow` |
| Braintrust | `braintrust` |
| Pydantic Logfire | `logfire` |
| LangSmith | `langsmith` |
| Langfuse | `langfuse` |
| PostHog | `posthog` |

### Using External Processors

```python
from agents import add_trace_processor
# Import the specific processor from the integration package
# Example pattern:
add_trace_processor(external_processor)
```

---

## Visualization

Install the viz extra and generate agent topology graphs:

```bash
pip install "openai-agents[viz]"
```

```python
from agents.extensions.visualization import draw_graph

# Generate and display graph
draw_graph(triage_agent)

# Save to file
draw_graph(triage_agent, filename="agent_graph")

# Display in window
draw_graph(triage_agent).view()
```

### Visual Elements

| Element | Shape | Color |
|---------|-------|-------|
| Agents | Rectangle | Yellow |
| Tools | Ellipse | Green |
| MCP servers | Rectangle | Grey |
| Handoffs | Solid arrow | - |
| Tool connections | Dotted arrow | - |
| MCP connections | Dashed arrow | - |

---

## Warnings

- Tracing is **unavailable** for Zero Data Retention (ZDR) organizations
- Sensitive data is **included by default** - disable for PII protection with `trace_include_sensitive_data=False`
- Tracing 401 errors with non-OpenAI providers: disable tracing or set a separate export key
- Always call `flush_traces()` in worker processes before exit
