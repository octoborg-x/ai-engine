import type { CallLLM, ChatMessage, LLMResponse } from "./llm.ts";
import type { ToolDefinition } from "../tools/types.ts";

/**
 * Live provider adapter: an OpenAI-compatible /chat/completions call using
 * plain `fetch`. No SDK, no agent framework - just the wire format.
 *
 * Reads the same environment variables the Python backend uses, so a single
 * .env at the repository root configures both.
 */

export type OpenAIClientConfig = {
  apiKey: string;
  baseUrl: string;
  model: string;
  temperature?: number;
  fetchImpl?: typeof fetch;
};

export function configFromEnv(env: NodeJS.ProcessEnv = process.env): OpenAIClientConfig {
  const apiKey = env.OPENROUTER_API_KEY ?? env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error("Set OPENROUTER_API_KEY (or OPENAI_API_KEY) to run live");
  }

  const baseUrl =
    env.OPENROUTER_BASE_URL ??
    env.OPENAI_BASE_URL ??
    "https://openrouter.ai/api/v1";

  const model = env.MODEL_NAME;
  if (!model) {
    throw new Error("Set MODEL_NAME to run live");
  }

  return { apiKey, baseUrl: baseUrl.replace(/\/$/, ""), model };
}

type WireMessage = Record<string, unknown>;
type WireToolCall = {
  id?: string;
  function?: { name?: string; arguments?: string };
};

export function createOpenAILLM(config: OpenAIClientConfig): CallLLM {
  const doFetch = config.fetchImpl ?? fetch;

  return async (messages, toolDefinitions): Promise<LLMResponse> => {
    const body = {
      model: config.model,
      temperature: config.temperature ?? 0,
      messages: messages.map(toWireMessage),
      tools: toolDefinitions.map((definition) => ({
        type: "function",
        function: {
          name: definition.name,
          description: definition.description,
          parameters: definition.inputSchema,
        },
      })),
      tool_choice: "auto",
    };

    const response = await doFetch(`${config.baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`LLM request failed (${response.status}): ${detail}`);
    }

    const payload = (await response.json()) as {
      choices?: { message?: { content?: string | null; tool_calls?: WireToolCall[] } }[];
    };

    const message = payload.choices?.[0]?.message;
    if (!message) throw new Error("LLM response had no choices[0].message");

    const call = message.tool_calls?.[0];

    if (call?.function?.name) {
      return {
        text: "",
        toolCall: {
          name: call.function.name,
          arguments: call.function.arguments ?? "{}",
          id: call.id,
        },
        message: {
          role: "assistant",
          content: message.content ?? "",
          toolCalls: [
            {
              name: call.function.name,
              arguments: call.function.arguments ?? "{}",
              id: call.id,
            },
          ],
        },
      };
    }

    const text = message.content ?? "";
    return { text, message: { role: "assistant", content: text } };
  };
}

function toWireMessage(message: ChatMessage): WireMessage {
  if (message.role === "assistant" && message.toolCalls?.length) {
    return {
      role: "assistant",
      content: message.content || null,
      tool_calls: message.toolCalls.map((call) => ({
        id: call.id ?? "call_1",
        type: "function",
        function: {
          name: call.name,
          arguments:
            typeof call.arguments === "string"
              ? call.arguments
              : JSON.stringify(call.arguments ?? {}),
        },
      })),
    };
  }

  if (message.role === "tool") {
    return {
      role: "tool",
      tool_call_id: message.toolCallId ?? "call_1",
      name: message.name,
      content: message.content,
    };
  }

  return { role: message.role, content: message.content };
}
