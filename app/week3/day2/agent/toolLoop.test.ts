import { test } from "node:test";
import assert from "node:assert/strict";

import type { ChatMessage } from "./llm.ts";
import { createScriptedLLM } from "./scriptedLlm.ts";
import { runAgent } from "./toolLoop.ts";
import { createDefaultRegistry, ToolRegistry } from "../tools/registry.ts";
import { getCustomerTool } from "../tools/getCustomer.ts";
import { createOpenAILLM } from "./openaiLlm.ts";

function baseMessages(): ChatMessage[] {
  return [
    { role: "system", content: "You are a support agent." },
    { role: "user", content: "Can C-1002 get a refund?" },
  ];
}

test("a direct answer needs no tool and terminates after one iteration", async () => {
  const llm = createScriptedLLM([{ text: "Hello!" }]);
  const result = await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(result.text, "Hello!");
  assert.equal(result.iterations, 1);
  assert.equal(result.steps.length, 0);
});

// DoD: tool definitions are sent to the LLM.
test("every LLM request includes the tool definitions", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1001" } } },
    { text: "Ada Lovelace is on the enterprise plan." },
  ]);

  await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(llm.requests.length, 2);
  for (const request of llm.requests) {
    assert.deepEqual(
      request.toolDefinitions.map((definition) => definition.name).sort(),
      ["getCustomer", "searchDocuments"],
    );
    assert.ok(request.toolDefinitions[0]!.inputSchema);
  }
});

// DoD: a requested tool call is detected, selected, and executed.
test("the correct tool is selected and executed for a single call", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "searchDocuments", arguments: { query: "refund policy" } } },
    { text: "Refunds are allowed within 30 days." },
  ]);

  const result = await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(result.steps.length, 1);
  assert.equal(result.steps[0]!.name, "searchDocuments");
  assert.equal(result.text, "Refunds are allowed within 30 days.");
});

// DoD: tool output goes back into the conversation; the model answers from it.
test("tool results are appended to the transcript before the next model call", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1003" } } },
    { text: "That account is suspended." },
  ]);

  const messages = baseMessages();
  const result = await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages,
  });

  const secondRequest = llm.requests[1]!.messages;
  const toolMessage = secondRequest.at(-1);

  assert.equal(toolMessage?.role, "tool");
  assert.equal(toolMessage?.role === "tool" && toolMessage.name, "getCustomer");

  const payload = JSON.parse(toolMessage!.content as string);
  assert.equal(payload.found, true);
  assert.equal(payload.customer.status, "suspended");

  // The assistant turn that requested the tool is preserved too.
  assert.ok(secondRequest.some((message) => message.role === "assistant"));

  // The final transcript is that request plus the model's closing answer.
  assert.equal(result.messages.length, secondRequest.length + 1);
  assert.equal(result.messages.at(-1)!.role, "assistant");
});

test("argument validation runs before execution, so a bad call never reaches the tool", async () => {
  let executed = false;
  const registry = new ToolRegistry().register({
    definition: getCustomerTool.definition,
    execute: async () => {
      executed = true;
      return {};
    },
  });

  const llm = createScriptedLLM([
    { toolCall: { name: "getCustomer", arguments: { wrongField: "C-1001" } } },
    { text: "I could not look that up." },
  ]);

  const result = await runAgent({ llm: llm.callLLM, registry, messages: baseMessages() });

  assert.equal(result.steps[0]!.error !== undefined, true, "expected a validation error");
  assert.match(result.steps[0]!.error!, /customerId is required/);
  assert.equal(executed, false, "a tool executed despite invalid arguments");
});

// DoD: a failed tool call is fed back so the model can recover.
test("a tool error is returned to the model as a tool message, not thrown", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "doesNotExist", arguments: {} } },
    { text: "Let me answer without that tool." },
  ]);

  const result = await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(result.steps[0]!.error !== undefined, true);
  const lastMessage = llm.requests[1]!.messages.at(-1)!;
  assert.match(lastMessage.content as string, /Unknown tool/);
  assert.equal(result.text, "Let me answer without that tool.");
});

// DoD: the model produces a final answer using results from both tools.
test("a multi-tool run returns a final answer built from both results", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "searchDocuments", arguments: { query: "refund policy" } } },
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1002" } } },
    { text: "Grace Hopper is covered within 30 days." },
  ]);

  const result = await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(result.iterations, 3);
  assert.deepEqual(
    result.steps.map((step) => step.name),
    ["searchDocuments", "getCustomer"],
  );
  assert.equal(result.text, "Grace Hopper is covered within 30 days.");

  // Both tool results are visible in the final request the model saw.
  const transcript = JSON.stringify(llm.requests.at(-1)!.messages);
  assert.match(transcript, /refund-001/);
  assert.match(transcript, /Grace Hopper/);
});

test("termination is enforced when the model never stops calling tools", async () => {
  const llm = createScriptedLLM([
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1001" } } },
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1001" } } },
  ]);

  await assert.rejects(
    () =>
      runAgent({
        llm: llm.callLLM,
        registry: createDefaultRegistry(),
        messages: baseMessages(),
        maxIterations: 2,
      }),
    /exceeded maxIterations/,
  );
});

test("events expose each step of the observe-decide-act cycle", async () => {
  const events: string[] = [];
  const llm = createScriptedLLM([
    { toolCall: { name: "getCustomer", arguments: { customerId: "C-1001" } } },
    { text: "done" },
  ]);

  await runAgent({
    llm: llm.callLLM,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
    onEvent: (event) => events.push(event.type),
  });

  assert.deepEqual(events, [
    "llm_response",
    "tool_call",
    "tool_result",
    "llm_response",
  ]);
});

// The live adapter is exercised with a stubbed fetch: no network, real parsing.
test("the OpenAI adapter parses a tool call and a final answer", async () => {
  const responses = [
    {
      choices: [
        {
          message: {
            content: null,
            tool_calls: [
              {
                id: "call_abc",
                function: { name: "getCustomer", arguments: '{"customerId":"C-1001"}' },
              },
            ],
          },
        },
      ],
    },
    { choices: [{ message: { content: "Ada is on the enterprise plan." } }] },
  ];

  const seen: { url: string; body: Record<string, unknown> }[] = [];
  const fetchImpl = (async (url: string, init: { body: string }) => {
    seen.push({ url, body: JSON.parse(init.body) });
    const payload = responses.shift();
    return { ok: true, status: 200, json: async () => payload, text: async () => "" };
  }) as unknown as typeof fetch;

  const llm = createOpenAILLM({
    apiKey: "test",
    baseUrl: "https://example.test/v1",
    model: "test-model",
    fetchImpl,
  });

  const result = await runAgent({
    llm,
    registry: createDefaultRegistry(),
    messages: baseMessages(),
  });

  assert.equal(result.text, "Ada is on the enterprise plan.");
  assert.equal(result.steps[0]!.name, "getCustomer");

  // The outbound body advertised the tools and replayed the tool result.
  const first = seen[0]!.body as { tools?: { function: { name: string } }[] };
  assert.deepEqual(
    first.tools?.map((tool) => tool.function.name).sort(),
    ["getCustomer", "searchDocuments"],
  );

  const secondMessages = (seen[1]!.body as { messages: ChatMessage[] }).messages;
  assert.equal(secondMessages.at(-1)!.role, "tool");
  assert.equal(seen[0]!.url, "https://example.test/v1/chat/completions");
});

test("the OpenAI adapter surfaces provider errors with status and body", async () => {
  const fetchImpl = (async () => ({
    ok: false,
    status: 429,
    text: async () => "rate limited",
  })) as unknown as typeof fetch;

  const llm = createOpenAILLM({
    apiKey: "test",
    baseUrl: "https://example.test/v1",
    model: "test-model",
    fetchImpl,
  });

  await assert.rejects(
    () => runAgent({ llm, registry: createDefaultRegistry(), messages: baseMessages() }),
    /429.*rate limited/,
  );
});
