# MCP Server Integration

Deep reference for Model Context Protocol (MCP) server integration in the OpenAI Agents SDK.

---

## Overview

MCP allows agents to access external tools from MCP-compatible servers. The SDK supports four transport types.

### Integration Decision Matrix

| Need | Class |
|------|-------|
| OpenAI Responses API calling public MCP servers | `HostedMCPTool` |
| Local/remote Streamable HTTP servers | `MCPServerStreamableHttp` |
| HTTP with Server-Sent Events (deprecated) | `MCPServerSse` |
| Local subprocess communication | `MCPServerStdio` |

---

## HostedMCPTool

Tools hosted by OpenAI's Responses API:

```python
import asyncio
from agents import Agent, HostedMCPTool, Runner

async def main():
    agent = Agent(
        name="Assistant",
        tools=[
            HostedMCPTool(
                tool_config={
                    "type": "mcp",
                    "server_label": "gitmcp",
                    "server_url": "https://gitmcp.io/openai/codex",
                    "require_approval": "never",
                }
            )
        ],
    )
    result = await Runner.run(agent, "What language is this repo written in?")
    print(result.final_output)

asyncio.run(main())
```

### Connector-Backed Hosted Servers

```python
import os

HostedMCPTool(
    tool_config={
        "type": "mcp",
        "server_label": "google_calendar",
        "connector_id": "connector_googlecalendar",
        "authorization": os.environ["GOOGLE_CALENDAR_AUTHORIZATION"],
        "require_approval": "never",
    }
)
```

### Approval Flows for Hosted Tools

```python
from agents import MCPToolApprovalRequest, MCPToolApprovalFunctionResult

SAFE_TOOLS = {"read_project_metadata"}

def approve_tool(request: MCPToolApprovalRequest) -> MCPToolApprovalFunctionResult:
    if request.data.name in SAFE_TOOLS:
        return {"approve": True}
    return {"approve": False, "reason": "Escalate to human reviewer"}

agent = Agent(
    name="Assistant",
    tools=[
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "gitmcp",
                "server_url": "https://gitmcp.io/openai/codex",
                "require_approval": "always",
            },
            on_approval_request=approve_tool,
        )
    ],
)
```

---

## MCPServerStreamableHttp

For Streamable HTTP MCP servers:

```python
import asyncio
import os
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings

async def main():
    token = os.environ["MCP_SERVER_TOKEN"]
    async with MCPServerStreamableHttp(
        name="My MCP Server",
        params={
            "url": "http://localhost:8000/mcp",
            "headers": {"Authorization": f"Bearer {token}"},
            "timeout": 10,
        },
        cache_tools_list=True,
        max_retry_attempts=3,
    ) as server:
        agent = Agent(
            name="Assistant",
            instructions="Use MCP tools to answer questions.",
            mcp_servers=[server],
            model_settings=ModelSettings(tool_choice="required"),
        )
        result = await Runner.run(agent, "Add 7 and 22.")
        print(result.final_output)

asyncio.run(main())
```

### Constructor Options

| Option | Purpose |
|--------|---------|
| `client_session_timeout_seconds` | HTTP read timeouts |
| `use_structured_content` | Prefer structured tool results |
| `max_retry_attempts` | Automatic retry count |
| `retry_backoff_seconds_base` | Retry backoff base |
| `tool_filter` | Expose subset of tools |
| `require_approval` | Human-in-the-loop policies |
| `failure_error_function` | Customize failure messages |
| `tool_meta_resolver` | Inject per-call MCP `_meta` payloads |
| `cache_tools_list` | Cache tool definitions |

### Approval Policies

```python
# String form
require_approval="always"   # or "never"

# Per-tool mapping
require_approval={"delete_file": "always", "read_file": "never"}

# Grouped object
require_approval={
    "always": {"tool_names": ["delete_file"]},
    "never": {"tool_names": ["read_file"]},
}
```

### Per-Call Metadata

```python
from agents.mcp import MCPToolMetaContext

def resolve_meta(context: MCPToolMetaContext) -> dict | None:
    tenant_id = context.run_context.context.get("tenant_id")
    if tenant_id is None:
        return None
    return {"tenant_id": str(tenant_id), "source": "agents-sdk"}

server = MCPServerStreamableHttp(
    name="Metadata-aware MCP",
    params={"url": "http://localhost:8000/mcp"},
    tool_meta_resolver=resolve_meta,
)
```

---

## MCPServerSse

**Warning:** The MCP project deprecated SSE transport. Prefer Streamable HTTP or stdio for new integrations.

```python
from agents.mcp import MCPServerSse

async with MCPServerSse(
    name="SSE Server",
    params={
        "url": "http://localhost:8000/sse",
        "headers": {"X-Workspace": "demo"},
    },
    cache_tools_list=True,
) as server:
    agent = Agent(name="Assistant", mcp_servers=[server])
    result = await Runner.run(agent, "What's the weather?")
```

---

## MCPServerStdio

For local subprocess MCP servers:

```python
from pathlib import Path
from agents.mcp import MCPServerStdio

samples_dir = Path(__file__).parent / "sample_files"

async with MCPServerStdio(
    name="Filesystem Server",
    params={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", str(samples_dir)],
    },
) as server:
    agent = Agent(
        name="Assistant",
        instructions="Use files in the sample directory.",
        mcp_servers=[server],
    )
    result = await Runner.run(agent, "List available files.")
    print(result.final_output)
```

---

## MCPServerManager

Manage multiple MCP servers with graceful failure handling:

```python
from agents.mcp import MCPServerManager, MCPServerStreamableHttp

servers = [
    MCPServerStreamableHttp(name="calendar", params={"url": "http://localhost:8000/mcp"}),
    MCPServerStreamableHttp(name="docs", params={"url": "http://localhost:8001/mcp"}),
]

async with MCPServerManager(servers) as manager:
    agent = Agent(
        name="Assistant",
        mcp_servers=manager.active_servers,  # Only successfully connected servers
    )
    result = await Runner.run(agent, "What tools are available?")
```

### Manager Properties

| Property/Method | Description |
|-----------------|-------------|
| `active_servers` | Successfully connected servers |
| `failed_servers` | Servers that failed to connect |
| `errors` | Connection error details |
| `strict=True` | Raise on first failure |
| `reconnect(failed_only=True)` | Retry failed servers |
| `reconnect(failed_only=False)` | Restart all servers |
| `connect_timeout_seconds` | Connection timeout |
| `connect_in_parallel` | Parallel connection attempts |

---

## Tool Filtering

### Static Filter

```python
from agents.mcp import MCPServerStdio, create_static_tool_filter

server = MCPServerStdio(
    params={"command": "npx", "args": [...]},
    tool_filter=create_static_tool_filter(
        allowed_tool_names=["read_file", "write_file"],
    ),
)
```

### Dynamic Filter

```python
from agents.mcp import ToolFilterContext

async def context_aware_filter(context: ToolFilterContext, tool) -> bool:
    if context.agent.name == "Read-Only" and tool.name.startswith("write_"):
        return False
    return True

server = MCPServerStdio(
    params={"command": "npx", "args": [...]},
    tool_filter=context_aware_filter,
)
```

Filter context exposes: `run_context`, `agent`, `server_name`.

---

## MCP Prompts

```python
# List available prompts
prompts = await server.list_prompts()

# Get a specific prompt with parameters
prompt_result = await server.get_prompt(
    "generate_code_review_instructions",
    {"focus": "security vulnerabilities", "language": "python"},
)
instructions = prompt_result.messages[0].content.text

agent = Agent(name="Reviewer", instructions=instructions, mcp_servers=[server])
```

---

## Agent-Level MCP Configuration

```python
agent = Agent(
    name="Assistant",
    mcp_servers=[server1, server2],
    mcp_config={
        "convert_schemas_to_strict": True,
        "failure_error_function": None,  # None raises exceptions
    },
)
```

---

## Caching

Every agent run calls `list_tools()` on each MCP server. Enable caching for stable tool sets:

```python
server = MCPServerStreamableHttp(
    name="My Server",
    params={"url": "http://localhost:8000/mcp"},
    cache_tools_list=True,
)

# Force refresh if tools changed
server.invalidate_tools_cache()
```
