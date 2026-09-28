# Week 3 Day 2 — Tools, Registry, and the Agent Loop

A minimum viable agent: an LLM decides, a tool acts, the result goes back, and
the loop repeats until the model answers. No agent framework — the control flow
is one `while` loop you can read top to bottom.

TypeScript, run directly by Node (>=22.18) with no build step and no runtime
dependencies.

## Layout

```
app/week3/day2/
├── package.json
├── tsconfig.json
├── run.ts                     # runnable demo (offline by default)
├── tools/
│   ├── types.ts               # ToolDefinition, Tool, ToolCall
│   ├── errors.ts              # not-found / validation / execution errors
│   ├── validate.ts            # JSON Schema subset validator
│   ├── getCustomer.ts         # tool 1: deterministic customer lookup
│   ├── searchDocuments.ts     # tool 2: deterministic keyword search
│   └── registry.ts            # metadata + execution, kept separate
└── agent/
    ├── llm.ts                 # conversation types + the callLLM seam
    ├── toolLoop.ts            # the agent loop
    ├── scriptedLlm.ts         # deterministic model for offline runs/tests
    └── openaiLlm.ts           # live OpenAI-compatible adapter (plain fetch)
```

## Run it

```bash
cd app/week3/day2

node run.ts                 # offline, scripted, no API key
node run.ts --live "..."    # real OpenAI-compatible call
node --test                 # 30 tests
```

Offline mode scripts a model that searches documents, then looks up a customer,
then answers from both results — exercising every step of the loop.

Live mode reads the same environment variables as the Python backend
(`OPENROUTER_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME`) and loads the
repository-root `.env` if present. There is no SDK dependency; the adapter is a
`fetch` call to `/chat/completions`.

## Metadata is separate from implementation

The registry can advertise tools without handing out the code that runs them:

```ts
type ToolDefinition = {
  name: string;
  description: string;
  inputSchema: object;
};

type Tool = {
  definition: ToolDefinition;
  execute: (args: unknown) => Promise<unknown>;
};
```

- `registry.definitions()` returns only `ToolDefinition` — what goes to the model.
- `registry.openAiTools()` wraps those in the provider's `{type, function}` envelope.
- `registry.executeTool(name, args)` is the only path that runs `execute`.

The model therefore cannot invoke a function reference. It emits a name and JSON
arguments, and the registry decides what that means.

## The loop

`agent/toolLoop.ts` is the shape from the brief:

```ts
while (true) {
  const response = await callLLM(messages, toolDefinitions);

  if (!response.toolCall) {
    return response.text;
  }

  const result = await executeTool(
    response.toolCall.name,
    response.toolCall.arguments,
  );

  messages.push(response.message);
  messages.push({
    role: "tool",
    name: response.toolCall.name,
    content: JSON.stringify(result),
  });
}
```

Two things the production version adds:

1. **`maxIterations`.** A model that keeps requesting tools must not spin
   forever; the loop throws once the budget is spent.
2. **Tool errors are observations.** `ToolValidationError`, `ToolNotFoundError`,
   and `ToolExecutionError` are serialized into the `tool` message instead of
   propagating, so the model can see the failure and choose another action.

## Definition of done

| Requirement | Where it is proven |
|---|---|
| Two tools exist and work independently | `tools.test.ts` — `getCustomer` and `searchDocuments` are called directly, no LLM |
| Tool definitions are sent to the LLM | `toolLoop.test.ts` — every recorded request carries both definitions |
| The application detects a requested tool call | `toolLoop.test.ts` — a scripted `toolCall` is routed and executed |
| Arguments are validated before execution | `registry.test.ts` — a spy tool's `execute` never runs on invalid args; `validate.ts` covers required/type/enum/bounds |
| The correct tool is selected and executed | `toolLoop.test.ts` — `searchDocuments` vs `getCustomer` select by name |
| Tool output goes back into the conversation | `toolLoop.test.ts` — a `role: "tool"` message is the last entry of the next request |
| The LLM produces a final answer using the tool result | `toolLoop.test.ts` — the closing request's transcript contains `refund-001` and `Grace Hopper` |
| No agent framework is used | No dependency beyond Node; the loop is a plain async function |

## Design notes

- **Arguments are untrusted.** `ToolCall.arguments` is typed `unknown` and stays
  that way through validation. Tools accept `unknown` and trust the registry's
  schema check, which is why their public signatures are not `ToolArgs`.
- **Tools return, they do not throw, on expected misses.** `getCustomer` returns
  `{found: false, ...}` and `searchDocuments` returns `{results: []}` so a normal
  "no record" outcome does not get wrapped as an execution failure.
- **The validator is intentionally small.** It covers the subset the tools
  declare — object shape, required keys, `additionalProperties`, types, `enum`,
  and numeric bounds. It is not a general JSON Schema implementation.
- **The offline path is a first-class citizen.** `createScriptedLLM` records each
  request, which is how the tests assert on the outbound contract (definitions
  sent, results appended) without a network call.
