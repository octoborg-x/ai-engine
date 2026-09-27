import { ToolExecutionError, ToolNotFoundError, ToolValidationError } from "./errors.ts";
import { getCustomerTool } from "./getCustomer.ts";
import { searchDocumentsTool } from "./searchDocuments.ts";
import type { JsonSchema, Tool, ToolCall, ToolDefinition } from "./types.ts";
import { validateArgs } from "./validate.ts";

export class HumanApprovalRequiredError extends Error {
  constructor(toolName: string, args: unknown) {
    super(`Human approval required for tool "${toolName}".`);
    this.toolName = toolName;
    this.args = args;
    this.name = "HumanApprovalRequiredError";
  }
}

export type ToolRisk = "read" | "write";

export type ApprovalStatus =
  | "not_required"
  | "pending"
  | "approved"
  | "rejected";

export interface PendingApproval {
  toolCallId: string;
  toolName: string;
  arguments: unknown;
  status: ApprovalStatus;
}

export type AgentStatus =
  | "running"
  | "waiting_for_approval"
  | "completed"
  | "failed"
  | "max_iterations";

export interface AgentState {
  status: AgentStatus;
  messages: any[];
  tool_results: any[];
  memory: any[];
  plan: string[];
  iteration: number;
  pendingApproval?: PendingApproval;
}

export function approveToolCall(state: AgentState, toolCallId: string, registry: ToolRegistry): void {
  if (state.pendingApproval && state.pendingApproval.toolCallId === toolCallId) {
    state.pendingApproval.status = "approved";
    registry.approveCall(state.pendingApproval.toolName, state.pendingApproval.arguments);
    state.status = "running";
  }
}

export function rejectToolCall(state: AgentState, toolCallId: string): void {
  if (state.pendingApproval && state.pendingApproval.toolCallId === toolCallId) {
    state.pendingApproval.status = "rejected";
    state.status = "running";
  }
}

/**
 * Tool registry.
 *
 * Two views over the same tools:
 *   - definitions()  -> metadata only, safe to serialize into an LLM request
 *   - executeTool()  -> validates then runs the implementation
 *
 * The LLM never receives, and cannot invoke, a function reference: it emits a
 * name plus JSON arguments, and the registry decides what that means.
 */
export class ToolRegistry {
  private readonly tools = new Map<string, Tool>();
  private readonly approvedCalls = new Set<string>();
  private readonly ticketIdempotencyDb = new Map<string, unknown>();
  private readonly executedToolCallIds = new Set<string>();

  approveCall(name: string, args: unknown): void {
    this.approvedCalls.add(JSON.stringify({ name, args }));
  }

  isExecuted(toolCallId: string): boolean {
    return this.executedToolCallIds.has(toolCallId);
  }

  markExecuted(toolCallId: string): void {
    this.executedToolCallIds.add(toolCallId);
  }

  register(tool: Tool): this {
    if (this.tools.has(tool.definition.name)) {
      throw new Error(`Tool "${tool.definition.name}" is already registered`);
    }
    const name = tool.definition.name;
    const risk = (tool.definition as any).risk ||
      (["get_customer", "getcustomer", "search_documents", "searchdocuments"].includes(name.toLowerCase()) ? "read" : "write");
    (tool.definition as any).risk = risk;

    this.tools.set(tool.definition.name, tool);
    return this;
  }

  /** Metadata for the model's `tools` parameter. Implementation is not exposed. */
  definitions(): ToolDefinition[] {
    return [...this.tools.values()].map((tool) => tool.definition);
  }

  /** Provider-shaped tool specs (OpenAI-compatible `tools` array). */
  openAiTools(): {
    type: "function";
    function: { name: string; description: string; parameters: object };
  }[] {
    return this.definitions().map(({ name, description, inputSchema }) => ({
      type: "function" as const,
      function: { name, description, parameters: inputSchema },
    }));
  }

  has(name: string): boolean {
    return this.tools.has(name);
  }

  get(name: string): Tool {
    const tool = this.tools.get(name);
    if (!tool) throw new ToolNotFoundError(name);
    return tool;
  }

  /** Validate the call's arguments without executing anything. */
  validate(call: ToolCall): Record<string, unknown> {
    const tool = this.get(call.name);
    const parsed = decodeArguments(call.name, call.arguments);
    const result = validateArgs(tool.definition.inputSchema as JsonSchema, parsed);

    if (!result.ok) {
      throw new ToolValidationError(call.name, result.issues);
    }
    return result.value;
  }

  /** Validate, then execute. The only path that runs tool code. */
  async executeTool(name: string, rawArguments: unknown, toolCallId?: string): Promise<unknown> {
    const args = this.validate({ name, arguments: rawArguments });
    const tool = this.get(name);

    if (toolCallId) {
      if (this.isExecuted(toolCallId)) {
        console.log(`[Idempotency] toolCallId ${toolCallId} has already been executed. Skipping execution.`);
        return { success: true, duplicateSkip: true, toolCallId };
      }
    }

    if ((tool.definition as any).risk === "write" || ["send_email", "update_database", "create_ticket"].includes(name)) {
      const approvalKey = JSON.stringify({ name, args });
      if (!this.approvedCalls.has(approvalKey)) {
        throw new HumanApprovalRequiredError(name, args);
      }
    }

    if (name === "create_ticket") {
      const idempotencyKey = JSON.stringify(args);
      if (this.ticketIdempotencyDb.has(idempotencyKey)) {
        console.log(`[Idempotency] Returning existing ticket result for key: ${idempotencyKey}`);
        if (toolCallId) this.markExecuted(toolCallId);
        return this.ticketIdempotencyDb.get(idempotencyKey);
      }
    }

    try {
      const action = async () => {
        if ((args as any)?.simulateTransientError) {
          throw new Error("Temporary DB failure 503");
        }
        return await tool.execute(args);
      };

      const result = await executeWithRetry(
        () => withTimeout(action(), 5000, name),
        name
      );

      if (name === "create_ticket") {
        this.ticketIdempotencyDb.set(JSON.stringify(args), result);
      }

      if (toolCallId) {
        this.markExecuted(toolCallId);
      }

      return result;
    } catch (error) {
      if (
        error instanceof ToolNotFoundError ||
        error instanceof ToolValidationError ||
        error instanceof HumanApprovalRequiredError
      ) {
        throw error;
      }
      throw new ToolExecutionError(name, error);
    }
  }
}

function isTransientError(error: unknown): boolean {
  const msg = String(error instanceof Error ? error.message : error).toLowerCase();
  return (
    msg.includes("timeout") ||
    msg.includes("429") ||
    msg.includes("502") ||
    msg.includes("503") ||
    msg.includes("temporary") ||
    msg.includes("transient")
  );
}

async function executeWithRetry<T>(
  fn: () => Promise<T>,
  toolName: string,
  maxAttempts = 3,
  baseDelayMs = 200
): Promise<T> {
  let attempt = 0;
  while (true) {
    attempt++;
    try {
      return await fn();
    } catch (error) {
      if (attempt >= maxAttempts || !isTransientError(error)) {
        throw error;
      }
      const delay = baseDelayMs * Math.pow(2, attempt - 1);
      console.log(`[Retry] Tool "${toolName}" failed (attempt ${attempt}). Retrying in ${delay}ms...`);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}

function withTimeout<T>(promise: Promise<T>, ms: number, toolName: string): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(`Tool "${toolName}" timed out after ${ms}ms`));
    }, ms);
    promise.then(
      (res) => {
        clearTimeout(timer);
        resolve(res);
      },
      (err) => {
        clearTimeout(timer);
        reject(err);
      }
    );
  });
}

export const createTicketTool: Tool = {
  definition: {
    name: "create_ticket",
    description: "Create a support ticket for a customer issue.",
    inputSchema: {
      type: "object",
      properties: {
        customerId: { type: "string" },
        issueType: { type: "string" },
        description: { type: "string" },
      },
      required: ["customerId", "issueType", "description"],
      additionalProperties: false,
    },
    risk: "write",
  } as any,
  execute: async (args: any) => {
    return { success: true, ticketId: `TKT-${Math.floor(Math.random() * 9000) + 1000}` };
  },
};

export const sendEmailTool: Tool = {
  definition: {
    name: "send_email",
    description: "Send an email to a customer. Requires human approval.",
    inputSchema: {
      type: "object",
      properties: {
        recipient: { type: "string" },
        subject: { type: "string" },
        body: { type: "string" },
      },
      required: ["recipient", "subject", "body"],
      additionalProperties: false,
    },
    risk: "write",
  } as any,
  execute: async (args: any) => {
    return { success: true, sentTo: args.recipient };
  },
};

export const updateDatabaseTool: Tool = {
  definition: {
    name: "update_database",
    description: "Update database records. Requires human approval.",
    inputSchema: {
      type: "object",
      properties: {
        customerId: { type: "string" },
        key: { type: "string" },
        value: { type: "string" },
      },
      required: ["customerId", "key", "value"],
      additionalProperties: false,
    },
    risk: "write",
  } as any,
  execute: async (args: any) => {
    return { success: true, updated: `${args.key} = ${args.value}` };
  },
};

/**
 * Models return tool arguments as a JSON string. Accept both the string and an
 * already-decoded object. Malformed JSON is surfaced as a validation error so
 * the caller sees a normal, structured failure rather than a SyntaxError.
 */
function decodeArguments(toolName: string, raw: unknown): unknown {
  if (typeof raw !== "string") return raw;

  try {
    return JSON.parse(raw);
  } catch {
    throw new ToolValidationError(toolName, [
      { path: "$", message: "arguments must be valid JSON" },
    ]);
  }
}

export function createDefaultRegistry(): ToolRegistry {
  return new ToolRegistry()
    .register(getCustomerTool)
    .register(searchDocumentsTool)
    .register(createTicketTool)
    .register(sendEmailTool)
    .register(updateDatabaseTool);
}

export { getCustomerTool, searchDocumentsTool };
