# Tool-calling agent

A framework-free TypeScript agent runtime that selects tools through an LLM,
validates untrusted arguments, executes registered tools, feeds results back
into the conversation, and terminates under an iteration budget.

## Components

- `agent/toolLoop.ts`: model/tool orchestration and iteration limit.
- `agent/openaiLlm.ts`: OpenAI-compatible HTTP adapter.
- `agent/scriptedLlm.ts`: deterministic offline model for tests and demos.
- `tools/registry.ts`: tool definitions, validation, and execution boundary.
- `tools/getCustomer.ts`, `tools/searchDocuments.ts`: sample tools.
- `agent/*.test.ts`, `tools/*.test.ts`: regression tests.

## Run

Requires Node.js >=22.18.

```bash
cd app/agent
node run.ts
node run.ts --live "How do I return an order?"
node --test
```

Offline mode uses a scripted model and does not require credentials. Live mode
reads `OPENROUTER_API_KEY`, `OPENAI_BASE_URL`, and `MODEL_NAME`.

## Safety and design

Tool arguments are untrusted and validated before execution. The model receives
tool metadata, not executable function references. Expected tool misses are
returned as observations; unexpected failures are normalized. The loop has a
hard iteration limit to prevent unbounded tool calls.
