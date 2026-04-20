# Authentication

Deep reference for authentication, domain keys, and tenant isolation in ChatKit.

---

## Two Architecture Modes

### OpenAI-Hosted Backend

- Server creates a `client_secret` via `openai.chatkit.sessions.create()`
- The secret is handed to the frontend -- clients never see the API key
- Refresh tokens before expiration and reconnect the widget
- Pass a unique `user` parameter per end user

```python
from openai import OpenAI

openai = OpenAI()

@app.post("/api/chatkit/session")
def create_session(user_id: str):
    session = openai.chatkit.sessions.create({
        "user": user_id,
    })
    return {"client_secret": session.client_secret}
```

### Self-Hosted Backend

- You control authentication entirely
- Pass a custom `context` object to `server.process(body, context)`
- The context flows through `respond()`, `action()`, and all Store methods
- Use it to enforce permissions and propagate user identity

---

## Production Auth Pattern

```python
from dataclasses import dataclass
from fastapi import FastAPI, Request, HTTPException, Depends

@dataclass
class RequestContext:
    user_id: str
    org_id: str
    plan: str

def get_current_user(request: Request) -> RequestContext:
    # Validate session cookie, bearer token, or JWT
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.replace("Bearer ", "")
    user = validate_token(token)  # Your auth logic
    return RequestContext(
        user_id=user.id,
        org_id=user.org_id,
        plan=user.plan,
    )

@app.post("/chatkit")
async def chatkit(request: Request, ctx: RequestContext = Depends(get_current_user)):
    result = await server.process(await request.body(), ctx)
    if isinstance(result, StreamingResult):
        return StreamingResponse(result, media_type="text/event-stream")
    return Response(content=result.json, media_type="application/json")
```

---

## Tenant Isolation in Store

Always filter queries by user_id/org_id:

```python
class PostgresStore(Store[RequestContext]):
    async def load_thread(self, thread_id, context):
        cur.execute(
            "SELECT data FROM threads WHERE id = %s AND user_id = %s",
            (thread_id, context.user_id),
        )
        row = cur.fetchone()
        if row is None:
            raise NotFoundError(f"Thread {thread_id} not found")
        return ThreadMetadata.model_validate(row[0])

    async def load_threads(self, limit, after, order, context):
        cur.execute(
            "SELECT data FROM threads WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
            (context.user_id, limit),
        )
        # ... paginate
```

---

## Domain Keys

Required for production ChatKit frontends:

1. Register at `https://platform.openai.com/settings/organization/security/domain-allowlist`
2. Configure in frontend:

```javascript
const chatkit = useChatKit({
  api: {
    url: "https://your-domain.com/api/chatkit",
    domainKey: "your-registered-domain-key",
  },
});
```

Missing or invalid domain keys prevent ChatKit from loading.

---

## Security Best Practices

| Practice | Detail |
|----------|--------|
| Never expose API keys | Use env vars or secret management |
| Authenticate every request | Session cookies, bearer tokens, or JWTs |
| Authorize thread access | Filter by user_id in Store queries |
| Validate tool inputs | Treat all user text and action payloads as untrusted |
| Avoid user-derived system prompts | Keep system messages static or config-derived |
| Encrypt data at rest | Use encrypted storage for thread data |
| Implement retention policies | Delete threads older than N days |
| Minimize PII | Reduce PII in thread metadata and tool returns |
