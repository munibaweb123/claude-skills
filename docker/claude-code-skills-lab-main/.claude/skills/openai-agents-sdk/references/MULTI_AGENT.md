# Multi-Agent Patterns

Deep reference for multi-agent orchestration in the OpenAI Agents SDK.

---

## Two Orchestration Approaches

| Approach | Control | Use Case |
|----------|---------|----------|
| **LLM-Based** | Agent decides autonomously | Dynamic routing, conversational flows |
| **Code-Based** | Developer controls flow | Deterministic pipelines, structured workflows |

---

## LLM-Based Orchestration

### Pattern 1: Handoffs (Specialist Responds Directly)

The active agent changes. The specialist takes over and responds directly to the user.

```python
from agents import Agent

billing_agent = Agent(
    name="Billing",
    handoff_description="Handles billing and payment issues",
    instructions="You handle billing inquiries. Be precise with numbers.",
)

technical_agent = Agent(
    name="Technical Support",
    handoff_description="Handles technical issues and debugging",
    instructions="You help with technical problems. Ask for error messages.",
)

triage_agent = Agent(
    name="Triage",
    instructions="Classify the user's issue and route to the appropriate team.",
    handoffs=[billing_agent, technical_agent],
)

result = await Runner.run(triage_agent, "My payment failed")
print(result.last_agent.name)  # "Billing"
```

### Pattern 2: Agents as Tools (Orchestrator Retains Control)

The orchestrator calls specialists as tools and combines their outputs. Control stays with the orchestrator.

```python
from agents import Agent

researcher = Agent(
    name="Researcher",
    instructions="Research topics thoroughly. Return detailed findings.",
)

writer = Agent(
    name="Writer",
    instructions="Write clear, engaging summaries from provided information.",
)

orchestrator = Agent(
    name="Orchestrator",
    instructions=(
        "For questions: use research tool first, then write tool to summarize. "
        "Combine results into a coherent answer."
    ),
    tools=[
        researcher.as_tool(
            tool_name="research",
            tool_description="Research a topic in depth",
        ),
        writer.as_tool(
            tool_name="write_summary",
            tool_description="Write a clear summary from research",
        ),
    ],
)
```

### When to Use Which

| Scenario | Pattern |
|----------|---------|
| User needs focused expert response | Handoffs |
| Need to combine multiple specialists | Agents as Tools |
| Conversation requires context switching | Handoffs |
| Pipeline with sequential processing | Agents as Tools |
| Dynamic routing based on content | Handoffs |
| Orchestrator needs to aggregate | Agents as Tools |

---

## Code-Based Orchestration

### Pattern 1: Structured Output for Classification

```python
from pydantic import BaseModel
from agents import Agent, Runner

class TicketClassification(BaseModel):
    category: str    # "billing", "technical", "general"
    priority: str    # "low", "medium", "high"
    summary: str

classifier = Agent(
    name="Classifier",
    instructions="Classify the support ticket.",
    output_type=TicketClassification,
)

async def route_ticket(user_input: str):
    result = await Runner.run(classifier, user_input)
    ticket = result.final_output

    if ticket.category == "billing":
        return await Runner.run(billing_agent, user_input)
    elif ticket.category == "technical":
        return await Runner.run(technical_agent, user_input)
    else:
        return await Runner.run(general_agent, user_input)
```

### Pattern 2: Agent Chaining

Output of one agent becomes input of the next:

```python
async def research_and_write(topic: str):
    # Step 1: Research
    research_result = await Runner.run(researcher, f"Research: {topic}")

    # Step 2: Write using research output
    write_input = f"Write a summary based on this research:\n{research_result.final_output}"
    write_result = await Runner.run(writer, write_input)

    # Step 3: Review
    review_input = f"Review this summary for accuracy:\n{write_result.final_output}"
    review_result = await Runner.run(reviewer, review_input)

    return review_result.final_output
```

### Pattern 3: Feedback Loops

Evaluator agent iterates until quality is met:

```python
from pydantic import BaseModel

class Evaluation(BaseModel):
    score: int       # 0-100
    feedback: str
    is_acceptable: bool

evaluator = Agent(
    name="Evaluator",
    instructions="Evaluate the quality of the text. Score 0-100.",
    output_type=Evaluation,
)

async def iterative_improvement(task: str, max_iterations: int = 3):
    result = await Runner.run(writer, task)
    content = result.final_output

    for i in range(max_iterations):
        eval_result = await Runner.run(evaluator, content)
        evaluation = eval_result.final_output

        if evaluation.is_acceptable:
            return content

        # Feed back for improvement
        improve_input = (
            f"Improve this text based on feedback:\n"
            f"Text: {content}\n"
            f"Feedback: {evaluation.feedback}"
        )
        result = await Runner.run(writer, improve_input)
        content = result.final_output

    return content
```

### Pattern 4: Parallel Execution

Run multiple agents concurrently:

```python
import asyncio

async def parallel_research(topics: list[str]):
    tasks = [
        Runner.run(researcher, f"Research: {topic}")
        for topic in topics
    ]
    results = await asyncio.gather(*tasks)
    return [r.final_output for r in results]
```

---

## Best Practices

### Prompting
- Write clear, specific instructions for each agent
- Include detailed tool descriptions
- Use `handoff_description` for routing context

### Architecture
- Use specialized agents (not general-purpose)
- Keep agent responsibilities focused and non-overlapping
- Prefer simple topologies over complex webs

### Monitoring
- Enable tracing to observe agent interactions
- Check `result.last_agent.name` to verify routing
- Monitor `result.new_items` for unexpected behavior

### Iteration
- Start with 2-3 agents, add complexity gradually
- Monitor failure points and adjust prompts
- Enable agent self-critique and error correction
- Implement evaluation frameworks for quality
