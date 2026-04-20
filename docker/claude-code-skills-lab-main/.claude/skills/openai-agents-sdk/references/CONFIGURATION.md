# Global Configuration

Deep reference for global configuration, environment variables, and logging in the OpenAI Agents SDK.

---

## Configuration Functions

| Function | Purpose |
|----------|---------|
| `set_default_openai_key(key)` | Sets API key programmatically |
| `set_default_openai_client(client, use_for_tracing=True)` | Custom AsyncOpenAI instance |
| `set_default_openai_api(api_type)` | `"chat_completions"` or Responses (default) |
| `set_default_openai_responses_transport(transport)` | `"websocket"` for persistent connections |
| `set_tracing_export_api_key(key)` | Separate key for trace exports |
| `set_tracing_disabled(disabled)` | Disables tracing globally |
| `enable_verbose_stdout_logging()` | Verbose logging output |

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | Primary API key | Required |
| `OPENAI_BASE_URL` | Custom API endpoint | OpenAI default |
| `OPENAI_WEBSOCKET_BASE_URL` | WebSocket endpoint | Derived from base URL |
| `OPENAI_ORG_ID` | Organization identifier | None |
| `OPENAI_PROJECT_ID` | Project identifier | None |
| `OPENAI_DEFAULT_MODEL` | Default model for agents | SDK default |
| `OPENAI_AGENTS_DONT_LOG_MODEL_DATA=1` | Suppress model data logging | Logging enabled |
| `OPENAI_AGENTS_DONT_LOG_TOOL_DATA=1` | Suppress tool data logging | Logging enabled |
| `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0` | Exclude sensitive data | Excluded |
| `OPENAI_AGENTS_DISABLE_TRACING=1` | Disable tracing entirely | Tracing enabled |

---

## Logger Names

| Logger | Purpose |
|--------|---------|
| `openai.agents` | Primary SDK logger |
| `openai.agents.tracing` | Tracing-specific logger |

### Custom Logging Configuration

```python
import logging

# Enable verbose SDK logging
logging.getLogger("openai.agents").setLevel(logging.DEBUG)

# Or use the convenience function
from agents import enable_verbose_stdout_logging
enable_verbose_stdout_logging()
```

---

## API Client Configuration

### Programmatic Setup

```python
from openai import AsyncOpenAI
from agents import set_default_openai_client, set_default_openai_key

# Option 1: Set just the key
set_default_openai_key("sk-your-key")

# Option 2: Set a custom client (more control)
client = AsyncOpenAI(
    api_key="sk-your-key",
    base_url="https://custom-endpoint.com/v1",
    timeout=60.0,
    max_retries=3,
)
set_default_openai_client(client, use_for_tracing=True)
```

### Switching API Types

```python
from agents import set_default_openai_api

# Use Chat Completions API (broader provider support)
set_default_openai_api("chat_completions")

# Use Responses API (default, recommended for OpenAI)
set_default_openai_api("responses")
```

---

## RunConfig for Per-Run Settings

```python
from agents import RunConfig, ModelSettings

config = RunConfig(
    # Model
    model="gpt-4.1",
    model_settings=ModelSettings(temperature=0.5),

    # Tracing
    tracing_disabled=False,
    trace_include_sensitive_data=False,
    workflow_name="production_workflow",
    trace_id="trace_custom_123",
    group_id="batch_abc",
    trace_metadata={"environment": "production", "version": "1.2.0"},

    # Separate tracing key
    tracing={"api_key": "sk-tracing-only-key"},
)
```

---

## Import Summary

```python
# Core
from agents import Agent, Runner, RunConfig, ModelSettings, function_tool

# Sessions
from agents import SQLiteSession, OpenAIConversationsSession
from agents.extensions.memory import (
    AsyncSQLiteSession, RedisSession, SQLAlchemySession,
    DaprSession, AdvancedSQLiteSession, EncryptedSession,
)
from agents.memory import OpenAIResponsesCompactionSession

# Guardrails
from agents import (
    input_guardrail, output_guardrail,
    tool_input_guardrail, tool_output_guardrail,
    GuardrailFunctionOutput, ToolGuardrailFunctionOutput,
    InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered,
)

# Handoffs
from agents import handoff

# Tools
from agents import (
    WebSearchTool, FileSearchTool, CodeInterpreterTool,
    ImageGenerationTool, ToolSearchTool,
    HostedMCPTool, ShellTool, ComputerTool, FunctionTool,
)

# MCP
from agents.mcp import (
    MCPServerStdio, MCPServerSse, MCPServerStreamableHttp,
    MCPServerManager, create_static_tool_filter,
    ToolFilterContext, MCPToolMetaContext,
)

# Context
from agents import RunContextWrapper, ToolContext

# HITL
from agents import RunState

# Tracing
from agents import (
    trace, flush_traces, custom_span,
    set_tracing_disabled, set_tracing_export_api_key,
    add_trace_processor, set_trace_processors,
)

# Visualization
from agents.extensions.visualization import draw_graph

# Configuration
from agents import (
    set_default_openai_key, set_default_openai_client,
    set_default_openai_api, set_default_openai_responses_transport,
    enable_verbose_stdout_logging,
)

# Errors
from agents import (
    AgentsException, MaxTurnsExceeded, ModelBehaviorError,
    ToolTimeoutError, UserError,
)

# Realtime
from agents.realtime import RealtimeAgent, RealtimeRunner
```
