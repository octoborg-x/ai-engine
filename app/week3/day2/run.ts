import { fileURLToPath } from "node:url";
import path from "node:path";

import { runAgent } from "./agent/toolLoop.ts";
import type { ChatMessage } from "./agent/llm.ts";
import { createScriptedLLM, type ScriptStep } from "./agent/scriptedLlm.ts";
import { createOpenAILLM, configFromEnv } from "./agent/openaiLlm.ts";
import { createDefaultRegistry } from "./tools/registry.ts";

/**
 * Runnable demo for the tool loop.
 *
 *   node run.ts            offline scripted run (default, no key needed)
 *   node run.ts --live "..."   real OpenAI-compatible call
 *
 * Offline mode scripts a model that first searches documents, then looks up a
 * customer, then answers using both results - exercising every step of the
 * loop: definitions sent, tool call detected, arguments validated, tool
 * executed, result fed back, final answer produced.
 */

const SYSTEM_PROMPT =
  "You are a support agent. Use the available tools to look up facts before " +
  "answering. Never invent customer or policy details.";

const SCRIPT: ScriptStep[] = [
  { toolCall: { name: "searchDocuments", arguments: { query: "refund policy" } } },
  { toolCall: { name: "getCustomer", arguments: { customerId: "C-1002" } } },
  {
    text:
      "Grace Hopper (C-1002, pro plan) is covered by the refund policy: " +
      "refunds are allowed within 30 days of purchase [refund-001].",
  },
];

async function main(): Promise<void> {
  const liveIndex = process.argv.indexOf("--live");
  const registry = createDefaultRegistry();
  const messages: ChatMessage[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: "Can customer C-1002 still get a refund?" },
  ];

  console.log("Tool definitions sent to the LLM:");
  for (const definition of registry.definitions()) {
    console.log(`  - ${definition.name}: ${definition.description}`);
  }
  console.log();

  const llm =
    liveIndex !== -1
      ? createOpenAILLM(configFromEnv(loadEnv()))
      : createScriptedLLM(SCRIPT).callLLM;

  const result = await runAgent({
    llm,
    registry,
    messages,
    onEvent: (event) => {
      if (event.type === "tool_call") {
        console.log(`-> tool call: ${event.name}(${formatArgs(event.arguments)})`);
      }
      if (event.type === "tool_result") {
        console.log(`<- tool result: ${JSON.stringify(event.result)}`);
      }
      if (event.type === "tool_error") {
        console.log(`!! tool error: ${event.error}`);
      }
    },
  });

  console.log();
  console.log(`iterations: ${result.iterations}`);
  console.log(`final answer: ${result.text}`);
}

/** Render arguments that may arrive as an object or a JSON string. */
function formatArgs(args: unknown): string {
  if (typeof args === "string") {
    try {
      return JSON.stringify(JSON.parse(args));
    } catch {
      return args;
    }
  }
  return JSON.stringify(args);
}

/** Load the repository-root .env if present, matching the Python backend. */
function loadEnv(): NodeJS.ProcessEnv {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../..");
  try {
    process.loadEnvFile(path.join(root, ".env"));
  } catch {
    // No .env file: fall back to the ambient environment.
  }
  return process.env;
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
