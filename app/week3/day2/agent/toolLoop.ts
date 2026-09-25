import {
  ToolExecutionError,
  ToolNotFoundError,
  ToolValidationError,
} from "../tools/errors.ts";
import type { ToolRegistry } from "../tools/registry.ts";
import type { ToolDefinition } from "../tools/types.ts";
import type { CallLLM, ChatMessage } from "./llm.ts";

export type AgentResult = {
  /** The model's final natural-language answer. */
  text: string;
  /** Full transcript, including assistant tool requests and tool results. */
  messages: ChatMessage[];
  /** One entry per executed tool call. */
  steps: ToolStep[];
  iterations: number;
};

export type ToolStep = {
  name: string;
  arguments: unknown;
  result?: unknown;
  error?: string;
};

export type RunAgentOptions = {
  llm: CallLLM;
  registry: ToolRegistry;
  messages: ChatMessage[];
  /** Hard stop so a model that keeps requesting tools cannot loop forever. */
  maxIterations?: number;
  onEvent?: (event: LoopEvent) => void;
};

export type LoopEvent =
  | { type: "llm_response"; hasToolCall: boolean }
  | { type: "tool_call"; name: string; arguments: unknown }
  | { type: "tool_result"; name: string; result: unknown }
  | { type: "tool_error"; name: string; error: string };

/**
 * The agent loop: observe -> decide -> act -> observe, until the model answers.
 *
 * Deliberately a plain async function. No framework, no hidden scheduler - the
 * whole control flow is the loop below.
 */
export async function runAgent(options: RunAgentOptions): Promise<AgentResult> {
  const {
    llm,
    registry,
    messages,
    maxIterations = 5,
    onEvent = () => {},
  } = options;

  const toolDefinitions: ToolDefinition[] = registry.definitions();
  const steps: ToolStep[] = [];
  let iterations = 0;

  while (true) {
    if (iterations >= maxIterations) {
      throw new Error(
        `Agent exceeded maxIterations (${maxIterations}) without a final answer`,
      );
    }

    // 1. Ask the model. It sees the transcript and the available tools.
    const response = await llm(messages, toolDefinitions);
    iterations += 1;
    onEvent({ type: "llm_response", hasToolCall: Boolean(response.toolCall) });

    // 2. No tool requested -> the model is done.
    if (!response.toolCall) {
      messages.push(response.message);
      return { text: response.text, messages, steps, iterations };
    }

    const { name, arguments: args } = response.toolCall;
    onEvent({ type: "tool_call", name, arguments: args });

    // 3. Act. Errors are observations, not crashes: they go back to the model.
    const step: ToolStep = { name, arguments: args };
    let content: string;

    try {
      const result = await registry.executeTool(name, args);
      step.result = result;
      content = JSON.stringify(result);
      onEvent({ type: "tool_result", name, result });
    } catch (error) {
      const message = describe(error);
      step.error = message;
      content = JSON.stringify({ error: message, tool: name });
      onEvent({ type: "tool_error", name, error: message });
    }

    steps.push(step);

    // 4. Feed the request and its result back so the model can continue.
    messages.push(response.message);
    messages.push({
      role: "tool",
      name,
      content,
    });
  }
}

function describe(error: unknown): string {
  if (
    error instanceof ToolNotFoundError ||
    error instanceof ToolValidationError ||
    error instanceof ToolExecutionError
  ) {
    return error.message;
  }
  return error instanceof Error ? error.message : String(error);
}
