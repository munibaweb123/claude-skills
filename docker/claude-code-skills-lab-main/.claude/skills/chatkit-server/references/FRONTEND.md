# Frontend Integration

Deep reference for React/JS frontend integration with ChatKit.

---

## Installation

```bash
# React
npm install @openai/chatkit-react

# Vanilla JS (CDN)
# Add to HTML <head>:
<script src="https://cdn.platform.openai.com/deployments/chatkit/chatkit.js" async></script>
```

---

## React Quick Start

```javascript
import { ChatKit, useChatKit } from "@openai/chatkit-react";

export function App() {
  const chatkit = useChatKit({
    api: {
      url: "http://localhost:8000/chatkit",
      domainKey: "local-dev",
    },
  });
  return <ChatKit control={chatkit.control} />;
}
```

---

## OpenAI-Hosted Mode (Session-Based)

For OpenAI-managed backend via Agent Builder:

```javascript
import { ChatKit, useChatKit } from "@openai/chatkit-react";

export function MyChat() {
  const { control } = useChatKit({
    api: {
      async getClientSecret(existing) {
        if (existing) { /* implement refresh */ }
        const res = await fetch("/api/chatkit/session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
        const { client_secret } = await res.json();
        return client_secret;
      },
    },
  });
  return <ChatKit control={control} className="h-[600px] w-[320px]" />;
}
```

Server-side session creation:

```python
from fastapi import FastAPI
from openai import OpenAI

app = FastAPI()
openai = OpenAI()

@app.post("/api/chatkit/session")
def create_session():
    session = openai.chatkit.sessions.create({})
    return {"client_secret": session.client_secret}
```

---

## Configuration Options

```javascript
const chatkit = useChatKit({
  api: {
    url: "https://your-server.com/chatkit",  // Required for self-hosted
    domainKey: "your-domain-key",             // Required for production
    fetch: customFetch,                        // Override fetch
  },
  theme: "light",          // "light" | "dark" | "auto"
  initialThread: null,     // Thread ID to open on mount

  // Client tools
  onClientTool: async ({ name, params }) => {
    if (name === "my_tool") return { result: "data" };
  },

  // Client effects
  onEffect: async ({ name, data }) => {
    if (name === "highlight") highlightText(data);
  },

  // Telemetry
  onLog: ({ name, data }) => sendToAnalytics({ name, data }),
  onError: ({ error }) => reportError(error),

  // Thread lifecycle
  onThreadChange: ({ threadId }) => updateURL(threadId),
});
```

---

## Header Configuration

```javascript
header: {
  title: "My Assistant",
  showNewThread: true,
}
// Or disable: header: false
```

---

## New Thread View

```javascript
newThreadView: {
  greeting: "Hi! How can I help you today?",
  starterPrompts: [
    { text: "Summarize my recent emails" },
    { text: "Draft a meeting agenda" },
    { text: "Help me debug this code" },
  ],
}
```

---

## Composer Configuration

```javascript
composer: {
  placeholder: "Ask me anything...",
  attachments: { enabled: true },
  dictation: { enabled: true },
  tools: [
    { id: "web_search", icon: "search", label: "Web Search" },
  ],
  models: [
    { id: "gpt-4.1", label: "GPT-4.1", default: true },
    { id: "gpt-4.1-mini", label: "Mini", description: "Faster" },
  ],
}
```

---

## Thread History

```javascript
history: {
  enabled: true,
  showDelete: true,
  showRename: true,
}
```

---

## Message Affordances

```javascript
messages: {
  threadItemActions: {
    feedback: true,    // Thumbs up/down
    copy: true,        // Copy button
  },
}
```

---

## Entity Tags (@-Mentions)

```javascript
entities: {
  onTagSearch: async (query) => [
    {
      id: "article_123",
      title: "The Future of AI",
      group: "Articles",
      icon: "globe",
      interactive: true,
      data: { type: "article" },
    },
  ],
  showComposerMenu: true,
}
```

---

## Imperative Methods

```javascript
const { control } = useChatKit({ ... });

// Send message programmatically
control.sendUserMessage({ text: "Hello!" });

// Focus composer
control.focusComposer();

// Start new thread
control.setThreadId(undefined);

// Set draft text
control.setComposerValue({ text: "Draft..." });
```

Guard with `isBusy = isLoading || isResponding` before imperative calls.

---

## Client-Side Events

```typescript
type Events = {
  "chatkit.error": CustomEvent<{ error: Error }>;
  "chatkit.response.start": CustomEvent<void>;
  "chatkit.response.end": CustomEvent<void>;
  "chatkit.thread.change": CustomEvent<{ threadId: string | null }>;
  "chatkit.log": CustomEvent<{ name: string; data?: Record<string, unknown> }>;
};
```

---

## Starter App

```bash
git clone https://github.com/openai/openai-chatkit-starter-app.git
cd openai-chatkit-starter-app/chatkit
npm install
npm run dev
```
