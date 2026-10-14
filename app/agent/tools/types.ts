/**
 * Shared contracts for the tool layer.
 *
 * Metadata (ToolDefinition) is deliberately separate from behaviour (Tool):
 * the registry can advertise tools to an LLM without the caller ever touching
 * the code that executes them.
 */

export type JsonSchema = Record<string, unknown>;

/** The contract the LLM sees: name, description, and JSON Schema for inputs. */
export type ToolDefinition = {
  name: string;
  description: string;
  inputSchema: object;
};

/** A tool pairs the contract with the implementation. */
export type Tool = {
  definition: ToolDefinition;
  execute: (args: unknown) => Promise<unknown>;
};

/** Arguments after validation, guaranteed to be a JSON object. */
export type ToolArgs = Record<string, unknown>;

/**
 * A tool call requested by the model.
 *
 * `arguments` stays `unknown` on purpose: it is untrusted provider output and
 * must pass validation before any tool sees it.
 */
export type ToolCall = {
  name: string;
  arguments: unknown;
  id?: string;
};
