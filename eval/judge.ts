// eval/judge.ts — LLM-as-judge (Groq via OpenAI-compatible endpoint, Week 4 Day 4)
export interface JudgeResult { correctness: number; relevance: number; faithfulness: number; reason: string; }
function buildPrompt(question: string, expected: string, answer: string, sources: string[]): string {
  const ctx = sources.join("\n---\n") || "(no sources retrieved)";
  return "Judge evaluation.\nQUESTION: " + question + "\nEXPECTED: " + expected + "\nANSWER: " + answer + "\nCONTEXT: " + ctx + "\nRespond ONLY JSON: {\"correctness\":0.0,\"relevance\":0.0,\"faithfulness\":0.0,\"reason\":\"...\"}";
}
export async function judge(question: string, expectedAnswer: string, generatedAnswer: string, retrievedSources: string[]): Promise<JudgeResult> {
  const apiKey = process.env.GROQ_API_KEY || process.env.OPENROUTER_API_KEY || "";
  const model = process.env.JUDGE_MODEL || "mixtral-8x7b-32768";
  const prompt = buildPrompt(question, expectedAnswer, generatedAnswer, retrievedSources);
  const url = (process.env.GROQ_BASE_URL || "https://api.groq.com/openai/v1") + "/chat/completions";
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: model, messages: [{ role: "user", content: prompt }], temperature: 0.0, max_tokens: 512 }),
  });
  if (!res.ok) { const t = await res.text(); throw new Error("Judge Groq request failed (" + res.status + "): " + t); }
  const data: any = await res.json();
  const raw = data.choices?.[0]?.message?.content || "";
  let clean = (typeof raw === "string" ? raw : JSON.stringify(raw)).trim();
  if (clean.startsWith("```")) { clean = clean.replace(/^```(json)?\n/, "").replace(/\n```$/, "").trim(); }
  const parsed = JSON.parse(clean);
  if (typeof parsed.correctness !== "number" || parsed.correctness < 0 || parsed.correctness > 1) throw new Error("Invalid correctness: " + parsed.correctness);
  if (typeof parsed.relevance !== "number" || parsed.relevance < 0 || parsed.relevance > 1) throw new Error("Invalid relevance: " + parsed.relevance);
  if (typeof parsed.faithfulness !== "number" || parsed.faithfulness < 0 || parsed.faithfulness > 1) throw new Error("Invalid faithfulness: " + parsed.faithfulness);
  if (typeof parsed.reason !== "string" || parsed.reason.length < 1) throw new Error("Invalid reason: " + parsed.reason);
  return { correctness: Math.round(parsed.correctness * 100) / 100, relevance: Math.round(parsed.relevance * 100) / 100, faithfulness: Math.round(parsed.faithfulness * 100) / 100, reason: parsed.reason };
}
