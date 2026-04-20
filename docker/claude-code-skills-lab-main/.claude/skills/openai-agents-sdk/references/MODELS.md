# Models and Providers

Deep reference for model configuration and provider integration in the OpenAI Agents SDK.

---

## Model Classes

| Class | API | Notes |
|-------|-----|-------|
| `OpenAIResponsesModel` | Responses API | Recommended; supports ToolSearchTool, deferred loading |
| `OpenAIResponsesWSModel` | Responses API (WebSocket) | Persistent connections; requires `websockets` package |
| `OpenAIChatCompletionsModel` | Chat Completions API | Legacy; broader provider compatibility |

---

## Configuration Methods

### Priority Order (highest to lowest)

1. `RunConfig(model=...)` - per-run override
2. `Agent(model=...)` - per-agent setting
3. `OPENAI_DEFAULT_MODEL` env var - global default
4. SDK default

```python
import os
from agents import Agent, Runner, RunConfig

# Environment variable
os.environ["OPENAI_DEFAULT_MODEL"] = "gpt-5.4"

# Agent-level
agent = Agent(name="Agent", model="gpt-4.1")

# RunConfig (overrides agent)
result = await Runner.run(agent, "Hello", run_config=RunConfig(model="gpt-5.4"))
```

---

## Non-OpenAI Providers

### Using Base URL Override

```python
from openai import AsyncOpenAI
from agents import Agent, Runner
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

client = AsyncOpenAI(
    api_key="your-api-key",
    base_url="https://your-provider.com/v1",
)

model = OpenAIChatCompletionsModel(
    model="provider-model-name",
    openai_client=client,
)

agent = Agent(name="Agent", model=model)
result = await Runner.run(agent, "Hello")
```

### Provider Scope Options

| Scope | How |
|-------|-----|
| **Global** | `set_default_openai_client(client)` |
| **Per-run** | `ModelProvider` in RunConfig |
| **Per-agent** | `Agent(model=model_instance)` |

```python
from agents import set_default_openai_client
from openai import AsyncOpenAI

# Global: all agents use this client
client = AsyncOpenAI(api_key="key", base_url="https://provider.com/v1")
set_default_openai_client(client)
```

---

## WebSocket Transport

Persistent connections for lower latency:

```python
from agents import set_default_openai_responses_transport

# Global setting
set_default_openai_responses_transport("websocket")

# Provider-level
from agents.models.openai_provider import OpenAIProvider
provider = OpenAIProvider(
    use_responses_websocket=True,
    websocket_base_url="wss://custom-endpoint.com",
)

# MultiProvider for multi-model setups
from agents.models.multi_provider import MultiProvider
provider = MultiProvider(
    openai_base_url="https://openrouter.ai/api/v1",
    openai_use_responses_websocket=True,
    openai_prefix_mode="model_id",
    unknown_prefix_mode="model_id",
)
```

---

## Retry Configuration

```python
from agents import ModelSettings, ModelRetrySettings
from agents.models import retry_policies

settings = ModelSettings(
    retry=ModelRetrySettings(
        max_retries=4,
        backoff={
            "initial_delay": 0.5,
            "max_delay": 5.0,
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

agent = Agent(name="Resilient Agent", model_settings=settings)
```

### Retry Policy Helpers

| Policy | Description |
|--------|-------------|
| `never()` | Never retry |
| `provider_suggested()` | Retry when provider suggests (Retry-After header) |
| `network_error()` | Retry on network errors |
| `http_status([...])` | Retry on specific HTTP status codes |
| `retry_after()` | Respect Retry-After header timing |
| `any(...)` | Retry if ANY policy matches |
| `all(...)` | Retry if ALL policies match |

**Safety:** Never retries abort errors, unsafe replay requests, or already-streaming output.

---

## Third-Party Adapters

### Any-LLM

```bash
pip install openai-agents[any-llm]
```

```python
agent = Agent(name="Agent", model="any-llm/anthropic/claude-3-opus")
```

### LiteLLM

```bash
pip install openai-agents[litellm]
```

```python
agent = Agent(name="Agent", model="litellm/anthropic/claude-3-opus")
```

---

## ModelSettings.extra_args

Pass provider-specific arguments:

```python
from agents import ModelSettings

settings = ModelSettings(
    temperature=0.1,
    extra_args={
        "service_tier": "flex",
        "user": "user_12345",
    },
)
```

---

## Switching to Chat Completions API

Some providers only support Chat Completions:

```python
from agents import set_default_openai_api

set_default_openai_api("chat_completions")
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tracing 401 errors | Disable tracing or set separate export key |
| Responses API 404s | Switch to `set_default_openai_api("chat_completions")` |
| Structured output failures | Provider may lack `json_schema` support; use Chat Completions |
| WebSocket errors | Install `websockets` package; check `websocket_base_url` |
