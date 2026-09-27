# Week 3 — Agents: Days 1–5 Combined Exercise

## Goal

Build **one manual AI Operations Agent core** that combines the Week 3 Days 1–5 skills into a single runnable system:

- Tool/function calling
- Agent loop + state
- Memory + planning + tool selection
- Retries + timeouts + idempotency
- Human approval + MCP concepts

**Important:** Build the underlying agent mechanism yourself. Do not hide the core loop behind LangChain, LangGraph, CrewAI, or another agent framework.

---

# Exercise: Build a Safe AI Operations Agent

## Scenario

You are building an internal operations assistant.

A user can ask the agent to:

- Find customer information
- Search internal documents
- Create a support ticket
- Send an email
- Update a database

The agent must decide which tools are necessary, execute them through explicit tool boundaries, preserve state, retry transient failures safely, prevent duplicate side effects, and require human approval before high-risk actions.

### Target architecture

```text
                    ┌── search_documents()
                    │
User → Agent Loop ──┼── get_customer()
                    │
                    ├── create_ticket()
                    │
                    ├── send_email()
                    │
                    └── update_database()
                              │
                              ↓
                       Approval Gate
                              │
                              ↓
                         Side Effect
```

---

# Part 1 — Tool Calling / Function Calling

## Objective

Implement explicit tool schemas and execution boundaries.

Create at least these tools:

```text
get_customer()
search_documents()
create_ticket()
send_email()
update_database()
```

Start with:

```text
get_customer()
search_documents()
```

and then add the side-effecting tools.

## Tool contract

Each tool should have:

1. A unique name
2. A description
3. A structured argument schema
4. Input validation
5. A deterministic execution function
6. A structured result

Example conceptual contract:

```python
Tool = {
    "name": "get_customer",
    "description": "Retrieve customer information by customer ID",
    "parameters": {
        "customer_id": "string"
    }
}
```

Do **not** let the model directly execute application code.

The flow must be:

```text
LLM decides
   ↓
Tool name + arguments
   ↓
Validate
   ↓
Application executes tool
   ↓
Tool result
   ↓
Back to agent
```

## Required implementation

Implement a tool registry:

```python
tools = {
    "get_customer": get_customer,
    "search_documents": search_documents,
    "create_ticket": create_ticket,
    "send_email": send_email,
    "update_database": update_database,
}
```

The agent should reject:

- Unknown tools
- Invalid arguments
- Missing required arguments
- Arguments outside the tool schema

## Deliverable

A working tool layer where the model's decision and the application's execution are clearly separated.

---

# Part 2 — Agent Loop + State

## Objective

Build the agent loop manually.

Use this mental model:

```text
Observe
   ↓
Decide
   ↓
Act
   ↓
Observe result
   ↓
Decide again
   ↓
...
   ↓
Finish
```

A minimal loop should resemble:

```python
while not finished:
    decision = model(state)

    if decision.type == "tool_call":
        result = execute_tool(decision)
        state = update_state(state, result)

    elif decision.type == "final":
        return decision.answer
```

## State

Create explicit structured state.

At minimum:

```python
state = {
    "messages": [],
    "tool_results": [],
    "memory": [],
    "plan": [],
    "iteration": 0,
}
```

Do not rely only on hidden variables.

## Safety requirement

Add a maximum iteration count:

```text
MAX_ITERATIONS = 8
```

The agent must terminate with a controlled error if the limit is reached.

## Deliverable

A manual agent loop that:

- Preserves state
- Executes multiple tools
- Feeds tool results back to the model
- Stops when the task is complete
- Cannot loop forever

---

# Part 3 — Memory + Planning + Tool Selection

## Objective

Add basic memory and planning.

### Short-term memory

The agent should retain information from the current task:

```text
User request
↓
Customer lookup result
↓
Document search result
↓
Ticket information
```

### Long-term memory concept

You do not need a production vector database for this exercise.

Implement the concept with a simple persistent store such as JSON or SQLite.

Store only information that is useful for future interactions.

Example:

```text
customer_id
preferred_contact_method
previous_ticket_id
```

Avoid storing unnecessary sensitive information.

---

## Planning

Before executing a multi-step request, allow the agent to create a small plan.

Example request:

> Find customer C123, check the refund policy, create a ticket if the request qualifies, and draft an email.

Possible plan:

```text
1. get_customer(C123)
2. search_documents("refund policy")
3. determine eligibility
4. create_ticket(...)
5. draft email
6. request approval
7. send email
```

The agent must be able to re-plan when tool results change the situation.

---

## Tool selection

The agent should choose the **minimum necessary tools**.

For example:

```text
"What is the refund policy?"
```

should not trigger:

```text
get_customer()
create_ticket()
send_email()
update_database()
```

It should only use:

```text
search_documents()
```

## Deliverable

A stateful agent that can:

- Create a plan
- Select appropriate tools
- Avoid unnecessary tools
- Update the plan after tool results
- Maintain short-term state

---

# Part 4 — Reliability Engineering

## Objective

Make tool execution safe enough for a production-style system.

Implement:

- Timeouts
- Retries
- Exponential backoff
- Retryable vs non-retryable errors
- Idempotency
- Duplicate-side-effect protection

---

## Timeouts

Every external or potentially slow tool call must have a timeout.

Example:

```text
Tool call
   ↓
5 second timeout
   ↓
success OR timeout error
```

The agent must receive a structured error instead of hanging indefinitely.

---

## Retry policy

Retry transient failures such as:

```text
HTTP 429
HTTP 502
HTTP 503
network timeout
temporary database failure
```

Do not blindly retry:

```text
invalid arguments
authentication failure
permission denied
validation error
business-rule rejection
```

Use exponential backoff:

```text
attempt 1 → 0.5s
attempt 2 → 1s
attempt 3 → 2s
```

Keep the maximum number of retries bounded.

---

# Part 5 — Idempotency for create_ticket()

## Objective

Prevent duplicate tickets when the agent retries.

A naive implementation can produce:

```text
Agent
  ↓
create_ticket()
  ↓
Ticket #123 created
  ↓
Network timeout
  ↓
Agent thinks it failed
  ↓
Retry
  ↓
Ticket #124 created
```

That is a production bug.

Instead, use an idempotency key:

```text
request
   ↓
idempotency_key
   ↓
check existing operation
   ↓
already completed?
   ├── yes → return existing result
   └── no  → create ticket
```

Example:

```python
idempotency_key = hash(
    customer_id +
    issue_type +
    normalized_description
)
```

Store the key with the created ticket.

A repeated request with the same key must return the original result rather than creating another ticket.

## Deliverable

Prove with a test that:

```text
create_ticket()
create_ticket()  # same request
```

creates **one** ticket, not two.

---

# Part 6 — Human Approval

## Objective

Introduce an explicit approval boundary before external side effects.

The agent may reason about an action without executing it.

For example:

```text
Agent decides:
"Send email to customer"

        ↓

Approval Gate

        ↓

Human:
[Approve] [Reject]

        ↓

send_email()
```

## Approval-required tools

Require approval before:

```text
send_email()
update_database()
```

You may also require approval for:

```text
create_ticket()
```

if the ticket creates an externally visible business action.

## Approval state

Represent approval explicitly:

```python
approval = {
    "status": "pending",
    "action": "send_email",
    "arguments": {...}
}
```

Allowed states:

```text
pending
approved
rejected
```

The agent must not bypass the approval gate.

## Deliverable

Demonstrate that:

```text
model → tool decision
```

does **not** automatically mean:

```text
tool → external side effect
```

---

# Part 7 — MCP

## Objective

Understand and demonstrate the MCP boundary conceptually.

Model the system as:

```text
Agent
  ↓
MCP client
  ↓
MCP server
  ↓
Tools / Resources
```

Understand these concepts:

- MCP client
- MCP server
- Tools
- Resources
- Security boundary

For this exercise, you do not need to replace the whole agent with an MCP framework.

Instead, document how your existing tools would map to MCP.

Example:

```text
MCP Server: customer-operations

Tools:
  get_customer()
  create_ticket()
  update_database()

Resources:
  customer://C123
  ticket://T456
```

## Security requirement

Treat an MCP server as a trust boundary.

Document:

- Which tools are exposed
- Which data can be accessed
- Which actions can mutate data
- Which actions require approval
- What credentials the server receives
- What the agent is not allowed to access

---

# Final Integration Scenario

Your completed agent must handle this request:

> "Look up customer C123, find the refund policy, determine whether the issue qualifies, create a support ticket if necessary, and send the customer an email explaining the result."

The system should execute approximately:

```text
User request
    ↓
Agent
    ↓
Plan
    ↓
get_customer()
    ↓
search_documents()
    ↓
Reason over results
    ↓
Decision
    ↓
create_ticket()
    ↓
Approval Gate
    ↓
send_email()
    ↓
Final response
```

The exact sequence may change depending on the tool results.

The important requirement is that the agent can:

1. Select tools
2. Maintain state
3. Plan
4. Re-plan
5. Execute tools
6. Handle failures
7. Retry safe operations
8. Prevent duplicate side effects
9. Pause for human approval
10. Resume after approval
11. Produce a final response

---

# Required Tests

Create tests for at least these cases.

## Test 1 — Simple read-only request

```text
"What is the refund policy?"
```

Expected:

```text
search_documents()
```

No customer lookup.

No side effect.

---

## Test 2 — Customer lookup

```text
"What is customer C123's current ticket?"
```

Expected:

```text
get_customer()
```

---

## Test 3 — Multi-step task

```text
"Check customer C123's issue and the refund policy."
```

Expected:

```text
get_customer()
search_documents()
```

---

## Test 4 — Retry

Force a temporary tool failure.

Expected:

```text
attempt 1 → failure
attempt 2 → retry
attempt 3 → success
```

---

## Test 5 — Idempotency

Call:

```text
create_ticket()
```

twice with the same idempotency key.

Expected:

```text
one ticket
two identical returned results
```

Not two tickets.

---

## Test 6 — Approval

Request:

```text
"Send the customer an email."
```

Expected:

```text
agent proposes send_email()
        ↓
pending approval
        ↓
no email sent
```

After approval:

```text
send_email()
```

executes exactly once.

---

## Test 7 — Rejection

Reject the approval.

Expected:

```text
send_email()
```

is never executed.

The agent returns a controlled result.

---

## Test 8 — Infinite-loop protection

Force the model to repeatedly request a tool.

Expected:

```text
MAX_ITERATIONS reached
        ↓
controlled termination
```

No infinite loop.

---

# Definition of Done

You are done only when all of the following are true:

- [ ] Tool schemas are explicit and validated.
- [ ] Model decisions are separated from tool execution.
- [ ] A manual agent loop exists without an agent framework.
- [ ] State is explicit and structured.
- [ ] Maximum agent iterations are enforced.
- [ ] Short-term memory is implemented.
- [ ] Long-term memory is understood and represented.
- [ ] The agent can create and revise a plan.
- [ ] Tool selection avoids unnecessary tools.
- [ ] Tool calls have timeouts.
- [ ] Retryable and non-retryable errors are distinguished.
- [ ] Exponential backoff is implemented.
- [ ] `create_ticket()` is idempotent.
- [ ] Duplicate side effects are prevented.
- [ ] Human approval exists before high-risk actions.
- [ ] Approval can be rejected safely.
- [ ] MCP client/server/tool/resource concepts are understood.
- [ ] MCP security boundaries are documented.
- [ ] All required tests pass.
- [ ] The complete system is runnable locally.
- [ ] The implementation is understandable enough to explain in a technical interview.

---

# Mini-Test

Answer these before looking at the answers.

### 1. What is the difference between tool calling and normal LLM generation?

### 2. Why should the model not directly execute application functions?

### 3. What is the purpose of the agent loop?

### 4. Why is explicit state important?

### 5. What problem does `MAX_ITERATIONS` solve?

### 6. What is the difference between short-term and long-term memory?

### 7. Why should an agent prefer the minimum necessary tools?

### 8. Which failures are normally safe to retry?

### 9. Why can retries create duplicate business operations?

### 10. What does idempotency mean in `create_ticket()`?

### 11. Which actions should normally cross a human-approval boundary?

### 12. What is MCP providing conceptually?

---

# Mini-Test Answers

### 1.

Tool calling lets the model produce a structured request for an external capability instead of pretending it performed the operation itself.

### 2.

The application must control validation, authorization, credentials, side effects, retries, logging, and security.

### 3.

It lets the agent iteratively observe state, choose an action, execute it, observe the result, and continue until the task is complete.

### 4.

Explicit state makes the workflow inspectable, testable, resumable, and bounded.

### 5.

It prevents infinite agent loops and uncontrolled token/API usage.

### 6.

Short-term memory belongs to the current task/conversation. Long-term memory persists information across tasks or sessions.

### 7.

Unnecessary tools increase latency, cost, complexity, and the opportunity for incorrect or unsafe actions.

### 8.

Transient failures such as rate limits, temporary network failures, and some 5xx responses.

### 9.

The first operation may succeed even when the response is lost, causing the retry to perform the same side effect again.

### 10.

Repeating the same logical request produces the same effective result rather than creating another side effect.

### 11.

Actions that are externally visible, irreversible, high-impact, privileged, or capable of changing business/customer data.

### 12.

MCP provides a standardized way for AI applications to interact with external tools and resources through defined client/server boundaries.

---

# Interview Questions

Be able to answer these without notes:

1. How would you design an agent loop from scratch?
2. How do you prevent an agent from entering an infinite loop?
3. Where should authorization happen: inside the prompt, inside the tool, or both?
4. How would you make an agent tool idempotent?
5. How do you distinguish retryable from non-retryable errors?
6. How would you resume an agent after human approval?
7. What are the tradeoffs between a single-agent and multi-agent architecture?
8. What information belongs in agent state?
9. How would you audit an agent's tool usage?
10. How would you secure an MCP server?
11. What happens if a tool succeeds but the agent never receives the result?
12. How would you prevent an LLM from selecting a privileged tool it should not use?
13. Where would you put timeouts and retry policies?
14. How would you test an agent deterministically?
15. When would you choose a workflow/state machine instead of a free-form agent loop?

---

# Production Notes

For a production implementation, pay particular attention to:

- Authorization at the tool boundary, not only in prompts.
- Explicit schemas for tool arguments.
- Timeouts on external operations.
- Bounded retries.
- Idempotency for side-effecting operations.
- Audit logs for tool calls.
- Approval gates for high-risk actions.
- Secrets kept outside model-visible context.
- Least-privilege credentials.
- Maximum iteration/token budgets.
- Structured error handling.
- Observability for latency, failures, tool usage, and cost.
- Clear separation between model reasoning and application execution.

The Week 3 project target is an **AI Operations Agent**, with tools such as:

```text
search_web()
search_documents()
get_customer()
create_ticket()
send_email()
update_database()
```

and the target architecture:

```text
User
  ↓
Agent
  ├── Web Search
  ├── Database
  ├── RAG
  └── External APIs
```

This combined exercise covers the Week 3 Days 1–5 progression before the Day 6 AI Operations Agent integration.
