import type { CallLLM, ChatMessage, LLMResponse } from "./llm.ts";
import type { ToolCall, ToolDefinition } from "../tools/types.ts";

/** One scripted model turn: either call a tool, or answer. */
export type ScriptStep =
  | { toolCall: { name: string; arguments: unknown } }
  | { text: string };

export type ScriptedLLM = {
  callLLM: CallLLM;
  /** Every request the loop made, for asserting on the outbound contract. */
  requests: { messages: ChatMessage[]; toolDefinitions: ToolDefinition[] }[];
};

export function toToolCall(call: ToolCall): ToolCall {
  return { name: call.name, arguments: call.arguments, id: call.id ?? "call_1" };
}

/**
 * Deterministic stand-in for a model provider.
 *
 * Plays a fixed list of turns back to the loop, so the agent mechanics can be
 * tested end to end with no network and no API key. It records each request so
 * tests can prove the tool definitions were actually sent to the model.
 */
export function createScriptedLLM(steps: ScriptStep[]): ScriptedLLM {
  const requests: ScriptedLLM["requests"] = [];
  let index = 0;

  const callLLM: CallLLM = async (messages, toolDefinitions): Promise<LLMResponse> => {
    requests.push({
      messages: structuredClone(messages),
      toolDefinitions: structuredClone(toolDefinitions),
    });

    const step = steps[index];
    index += 1;

    if (!step) {
      throw new Error("ScriptedLLM ran out of steps: the loop did not terminate");
    }

    if ("toolCall" in step) {
      const toolCall = toToolCall(step.toolCall as ToolCall);
      return {
        text: "",
        toolCall,
        message: {
          role: "assistant",
          content: "",
          toolCalls: [toolCall],
        },
      };
    }

    return {
      text: step.text,
      message: { role: "assistant", content: step.text },
    };
  };

  return { callLLM, requests };
}
