import { fileURLToPath } from "node:url";
import path from "node:path";

import { runAgent } from "./agent/toolLoop.ts";
import type { ChatMessage } from "./agent/llm.ts";
import { createScriptedLLM, type ScriptStep } from "./agent/scriptedLlm.ts";
import { createOpenAILLM, configFromEnv } from "./agent/openaiLlm.ts";
import { createDefaultRegistry } from "./tools/registry.ts";
import { approveToolCall, rejectToolCall, type AgentState, type PendingApproval } from "./tools/registry.ts";
import { HumanApprovalRequiredError } from "./tools/registry.ts";

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
  console.log("=== Running Week 3 Agent Exercises & Demos ===\n");

  const registry = createDefaultRegistry();

  // --- DEMO 1: IDEMPOTENCY FOR create_ticket ---
  console.log("--- Demo 1: Idempotency Verification ---");
  const ticketArgs = { customerId: "C-1002", issueType: "refund", description: "Requesting a refund" };
  const res1 = await registry.executeTool("create_ticket", ticketArgs);
  const res2 = await registry.executeTool("create_ticket", ticketArgs);
  console.log(`First call result:`, res1);
  console.log(`Second call result:`, res2);
  console.log(`Idempotency verification passed: ${JSON.stringify(res1) === JSON.stringify(res2) ? "YES" : "NO"}\n`);

  // --- DEMO 2: RETRIES AND EXPONENTIAL BACKOFF ---
  console.log("--- Demo 2: Retry with Exponential Backoff ---");
  try {
    await registry.executeTool("create_ticket", { ...ticketArgs, simulateTransientError: true });
  } catch (err) {
    console.log(`Failed as expected after max attempts with: ${(err as Error).message}\n`);
  }

  // --- DEMO 3: HUMAN APPROVAL GATE ---
  console.log("--- Demo 3: Human Approval Gate ---");
  const emailArgs = { recipient: "grace@hopper.com", subject: "Refund update", body: "Your refund is processed." };
  try {
    await registry.executeTool("send_email", emailArgs);
  } catch (err) {
    if (err instanceof HumanApprovalRequiredError) {
      console.log(`[Gate Intercepted] ${err.message}`);
      console.log(`Approving action...`);
      registry.approveCall("send_email", emailArgs);
      const approvedRes = await registry.executeTool("send_email", emailArgs);
      console.log(`Execution after approval:`, approvedRes);
    }
  }
  console.log();

  // --- DEMO 4: FULL APPROVAL FLOW TEST ---
  console.log("--- Demo 4: Full Human Approval Flow ---");
  await simulateAgentWithApproval(
    registry,
    "Customer 123 has a refund issue. Create a support ticket.",
    "approve"
  );
  console.log();

  // --- DEMO 5: REJECTION FLOW TEST ---
  console.log("--- Demo 5: Human Rejection Flow ---");
  await simulateAgentWithApproval(
    registry,
    "Customer 123 has a refund issue. Create a support ticket.",
    "reject"
  );
  console.log();

  // --- DEMO 6: DUP PROTECTION TEST ---
  console.log("--- Demo 6: Same toolCallId Duplicate Protection ---");
  await simulateAgentWithApproval(
    registry,
    "Customer 123 has a refund issue. Create a support ticket.",
    "duplicate"
  );
  console.log();

  console.log("--- Running Main Agent Loop ---");
  const liveIndex = process.argv.indexOf("--live");
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

async function simulateAgentWithApproval(
  registry: any,
  userQuery: string,
  approvalAction: "approve" | "reject" | "duplicate"
): Promise<void> {
  console.log(`[Simulation] Query: "${userQuery}"`);

  const state: AgentState = {
    status: "running",
    messages: [{ role: "user", content: userQuery }],
    tool_results: [],
    memory: [],
    plan: ["1. Lookup customer", "2. Search policy", "3. Create support ticket if needed"],
    iteration: 0,
  };

  const steps = [
    { name: "get_customer", args: { customerId: "C123" } },
    { name: "search_documents", args: { query: "refund policy" } },
    { name: "create_ticket", args: { customerId: "C123", issueType: "refund", description: "Customer 123 refund issue" } }
  ];

  const toolCallId = "call_abc123";

  for (const step of steps) {
    state.iteration++;
    console.log(`  [Step ${state.iteration}] Agent decides to run: ${step.name}(${JSON.stringify(step.args)})`);

    const tool = registry.get(step.name);
    const risk = (tool.definition as any).risk;
    console.log(`    - Tool risk: "${risk}"`);

    if (risk === "write") {
      state.pendingApproval = {
        toolCallId,
        toolName: step.name,
        arguments: step.args,
        status: "pending",
      };
      state.status = "waiting_for_approval";
      console.log(`    - [Boundary Intercepted] Write tool paused! State status: "${state.status}"`);
      break;
    } else {
      const res = await registry.executeTool(step.name, step.args);
      state.tool_results.push({ name: step.name, result: res });
      console.log(`    - [Auto Execute] Result:`, res);
    }
  }

  if (state.status === "waiting_for_approval" && state.pendingApproval) {
    const pending = state.pendingApproval;
    console.log(`  --- Human Action: status is ${pending.status} ---`);

    if (approvalAction === "approve") {
      approveToolCall(state, pending.toolCallId, registry);
      console.log(`    - State status after approveToolCall: "${state.status}"`);
      console.log(`    - Pending status: "${state.pendingApproval?.status}"`);

      const res = await registry.executeTool(pending.toolName, pending.arguments, pending.toolCallId);
      state.tool_results.push({ name: pending.toolName, result: res });
      state.status = "completed";
      console.log(`    - [Execute Success] Result:`, res);
    } else if (approvalAction === "reject") {
      rejectToolCall(state, pending.toolCallId);
      console.log(`    - State status after rejectToolCall: "${state.status}"`);
      console.log(`    - Pending status: "${state.pendingApproval?.status}"`);

      state.messages.push({
        role: "tool",
        name: pending.toolName,
        content: "Error: Human rejected execution of this action.",
      });
      state.status = "completed";
      console.log(`    - [Execute Prevented] Rejection message sent back to Agent.`);
    } else if (approvalAction === "duplicate") {
      approveToolCall(state, pending.toolCallId, registry);
      const res1 = await registry.executeTool(pending.toolName, pending.arguments, pending.toolCallId);
      console.log(`    - First execution result:`, res1);
      const res2 = await registry.executeTool(pending.toolName, pending.arguments, pending.toolCallId);
      console.log(`    - Second execution with same toolCallId result:`, res2);
    }
  }
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
