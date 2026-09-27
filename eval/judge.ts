// eval/judge.ts — LLM-as-judge (Groq via OpenAI-compatible endpoint, Week 4 Day 4)
export interface JudgeResult { correctness: number; relevance: number; faithfulness: number; reason: string; }
function buildPrompt(question: string, expected: string, answer: string, sources: string[]): string {
  const ctx = sources.join("\n---\n") || "(no sources retrieved)";
  return "Judge evaluation.\nQUESTION: " + question + "\nEXPECTED: " + expected + "\nANSWER: " + answer + "\nCONTEXT: " + ctx + "\nRespond ONLY JSON: {\"correctness\":0.0,\"relevance\":0.0,\"faithfulness\":0.0,\"reason\":\"...\"}";
}
export async function judge(question: string, expectedAnswer: string, generatedAnswer: string, retrievedSources: string[]): Promise<JudgeResult> {
  const apiKey = process.env.HUGGINGFACE_APIKEY || process.env.GROQ_API_KEY || process.env.OPENROUTER_API_KEY || "";
  const model = process.env.HUGGING_MODEL || process.env.JUDGE_MODEL || "mistralai/Mistral-7B-Instruct-v0.2";
  const prompt = buildPrompt(question, expectedAnswer, generatedAnswer, retrievedSources);
  const url = "https://api-inference.huggingface.co/models/" + model;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: "Bearer " + apiKey },
    body: JSON.stringify({ inputs: prompt, parameters: { temperature: 0, max_new_tokens: 512 } }),
  });
  if (!res.ok) { const t = await res.text(); throw new Error("Judge HuggingFace request failed (" + res.status + "): " + t); }
  const data: any = await res.json();
  const raw = (Array.isArray(data) ? (data[0]?.generated_text || data[0]?.generated_text || "") : (data.generated_text || data[0]?.generated_text || "")) || "";
  let clean = (typeof raw === "string" ? raw : JSON.stringify(raw)).trim();
  if (clean.startsWith("```")) { clean = clean.replace(/^```(json)?\n/, "").replace(/\n```$/, "").trim(); }
  const parsed = JSON.parse(clean);
  if (typeof parsed.correctness !== "number" || parsed.correctness < 0 || parsed.correctness > 1) throw new Error("Invalid correctness: " + parsed.correctness);
  if (typeof parsed.relevance !== "number" || parsed.relevance < 0 || parsed.relevance > 1) throw new Error("Invalid relevance: " + parsed.relevance);
  if (typeof parsed.faithfulness !== "number" || parsed.faithfulness < 0 || parsed.faithfulness > 1) throw new Error("Invalid faithfulness: " + parsed.faithfulness);
  if (typeof parsed.reason !== "string" || parsed.reason.length < 1) throw new Error("Invalid reason: " + parsed.reason);
  return { correctness: Math.round(parsed.correctness * 100) / 100, relevance: Math.round(parsed.relevance * 100) / 100, faithfulness: Math.round(parsed.faithfulness * 100) / 100, reason: parsed.reason };
}
