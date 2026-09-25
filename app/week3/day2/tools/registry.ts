import { ToolExecutionError, ToolNotFoundError, ToolValidationError } from "./errors.ts";
import { getCustomerTool } from "./getCustomer.ts";
import { searchDocumentsTool } from "./searchDocuments.ts";
import type { JsonSchema, Tool, ToolCall, ToolDefinition } from "./types.ts";
import { validateArgs } from "./validate.ts";

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

  register(tool: Tool): this {
    if (this.tools.has(tool.definition.name)) {
      throw new Error(`Tool "${tool.definition.name}" is already registered`);
    }
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
  async executeTool(name: string, rawArguments: unknown): Promise<unknown> {
    const args = this.validate({ name, arguments: rawArguments });
    const tool = this.get(name);

    try {
      return await tool.execute(args);
    } catch (error) {
      if (error instanceof ToolNotFoundError || error instanceof ToolValidationError) {
        throw error;
      }
      throw new ToolExecutionError(name, error);
    }
  }
}

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
  return new ToolRegistry().register(getCustomerTool).register(searchDocumentsTool);
}

export { getCustomerTool, searchDocumentsTool };
