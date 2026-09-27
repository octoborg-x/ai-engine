import type { ToolCall, ToolDefinition } from "../tools/types.ts";

/**
 * Conversation state plus the provider boundary.
 *
 * `callLLM` is the single seam between the loop and any model provider. The
 * loop sends the current messages and the tool definitions and gets back one
 * of two things: a tool call, or a final text answer.
 */

export type ChatMessage =
  | { role: "system"; content: string }
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; toolCalls?: ToolCall[] }
  | { role: "tool"; name: string; content: string; toolCallId?: string };

export type LLMResponse = {
  /** Final natural-language answer. Empty when the model asked for a tool. */
  text: string;
  /** Present when the model wants a tool invoked instead of answering. */
  toolCall?: ToolCall;
  /** The assistant turn to append to the conversation. */
  message: ChatMessage;
};

export type CallLLM = (
  messages: ChatMessage[],
  toolDefinitions: ToolDefinition[],
) => Promise<LLMResponse>;
