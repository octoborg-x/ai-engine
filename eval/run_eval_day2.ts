
// eval/run_eval_day2.ts — Week 4 Day 2: deterministic correctness + retrieval scoring
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { judge, JudgeResult } from "./judge";

const DATASET_PATH = resolve(__dirname, "dataset.jsonl");
const RESULTS_DIR = resolve(__dirname, "results");
mkdirSync(RESULTS_DIR, { recursive: true });

type DatasetRecord = {
  id: string; question: string; expected_answer: string; expected_sources: string[]; tags: string[];
};

function normalizeText(text: string): string {
  return text.toLowerCase().trim().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ");
}

function tokenOverlapScore(answer: string, expected: string): number {
  const a = normalizeText(answer).split(" ").filter(Boolean);
  const e = normalizeText(expected).split(" ").filter(Boolean);
  if (e.length === 0) return a.length === 0 ? 1 : 0;
  const overlap = a.filter((t) => e.includes(t)).length;
  const union = new Set([...a, ...e]).size;
  return union === 0 ? 0 : overlap / union;
}

function computeCorrectnessScore(answer: string, expected: string): number {
  const normAnswer = normalizeText(answer);
  const normExpected = normalizeText(expected);
  if (normAnswer === normExpected) return 1.0;
  if (normAnswer.includes(normExpected) || normExpected.includes(normAnswer)) return 0.85;
  return Math.round(tokenOverlapScore(answer, expected) * 100) / 100;
}

function computeRetrievalMetrics(retrieved: string[], expected: string[]): {precision:number; recall:number; hit:boolean} {
  if (expected.length === 0) return {precision: retrieved.length === 0 ? 1.0 : 0.0, recall: 1.0, hit: retrieved.length === 0};
  const relevant = retrieved.filter((s) => expected.some((e) => s === e || s.includes(e) || e.includes(s))).length;
  return {precision: Math.round((retrieved.length ? relevant/retrieved.length : 0) * 100) / 100, recall: Math.round((relevant/expected.length) * 100) / 100, hit: relevant > 0};
}

function loadMostRecentResults(): any[] | null {
  try {
    const {execSync} = require("child_process");
    const filesStr = execSync("ls " + RESULTS_DIR).toString().trim();
    const files = filesStr ? filesStr.split("\n") : [];
    const evalFiles = files.filter((f: string) => f.startsWith("eval-") && f.endsWith(".json") && !f.includes("meta"));
    if (evalFiles.length === 0) return null;
    return JSON.parse(readFileSync(resolve(RESULTS_DIR, evalFiles.sort().pop()!), "utf-8")).results || null;
  } catch { return null; }
}



function splitClaims(text: string): string[] {
  return text.split(/[.!?]/).map(s => s.trim()).filter(s => s.length > 3);
}

function extractKeyTerms(text: string): string[] {
  const words = normalizeText(text).split(" ").filter(w => w.length > 3);
  return Array.from(new Set(words));
}

function computeFaithfulnessScore(answer: string, sources: string[]): { score: number; unsupported_claims: string[]; detected: boolean } {
  const claims = splitClaims(answer);
  if (claims.length === 0) return { score: 1.0, unsupported_claims: [], detected: false };
  
  const sourceText = sources.join(" ").toLowerCase();
  const unsupported: string[] = [];
  
  for (const claim of claims) {
    const terms = extractKeyTerms(claim);
    if (terms.length === 0) continue;
    const supportedTerms = terms.filter(t => sourceText.includes(t)).length;
    const ratio = terms.length ? supportedTerms / terms.length : 1;
    if (ratio < 0.5) {
      unsupported.push(claim);
    }
  }
  
  const score = claims.length > 0 ? Math.round((1 - unsupported.length / claims.length) * 100) / 100 : 1.0;
  return { score, unsupported_claims: unsupported, detected: score < 0.7 };
}

async function main() {
  console.log("=== Week 4 Day 2 — Deterministic Correctness + Retrieval Scoring ===");
  if (!existsSync(DATASET_PATH)) { console.error("Dataset not found"); process.exit(1); }
  const raw = readFileSync(DATASET_PATH, "utf-8");
  const records: DatasetRecord[] = raw.split("\n").filter(l => l.trim()).map((l) => JSON.parse(l));
  console.log(`Loaded ${records.length} records\n`);

  const resultsSource: any[] = loadMostRecentResults() || [];
  if (!resultsSource.length) { console.error("Run Day 1 first."); process.exit(1); }
  console.log(`Scoring ${resultsSource.length} results...`);

  const retrievalTags = ["retrieval", "multi-step"];
  const scored = resultsSource.map((r: any) => {
    const rec = records.find((re) => re.id === r.id);
    return {...r, tags: rec?.tags || [], correctness_score: computeCorrectnessScore(r.answer || "", rec?.expected_answer || ""), ...computeRetrievalMetrics(r.retrieved_sources || [], rec?.expected_sources || []), retrieval_precision: computeRetrievalMetrics(r.retrieved_sources || [], rec?.expected_sources || []).precision, retrieval_recall: computeRetrievalMetrics(r.retrieved_sources || [], rec?.expected_sources || []).recall, retrieval_hit: computeRetrievalMetrics(r.retrieved_sources || [], rec?.expected_sources || []).hit};
  });
  // Recompute cleanly
  const judgePromises = resultsSource.map(async (r: any) => {
    const rec = records.find((re) => re.id === r.id);
    try {
      const j: JudgeResult = await judge(r.question || "", rec?.expected_answer || "", r.answer || "", r.retrieved_sources || []);
      return { ...r, judge: j };
    } catch (err) {
      console.error(`Judge failed for ${r.id}:`, err);
      return { ...r, judge: { correctness: 0, relevance: 0, faithfulness: 0, reason: `Judge error: ${err}` } };
    }
  });
  const judgedResults = await Promise.all(judgePromises);
  const finalScored = judgedResults.map((r: any) => {
    const rec = records.find((re) => re.id === r.id);
    const ret = computeRetrievalMetrics(r.retrieved_sources || [], rec?.expected_sources || []);
    const faith = computeFaithfulnessScore(r.answer || "", r.retrieved_sources || []); return { ...r, tags: rec?.tags || [], correctness_score: computeCorrectnessScore(r.answer || "", rec?.expected_answer || ""), retrieval_precision: ret.precision, retrieval_recall: ret.recall, retrieval_hit: ret.hit, faithfulness_score: faith.score, unsupported_claims: faith.unsupported_claims, hallucination_detected: faith.detected };
  });

  const total = finalScored.length;
  const accuracy = finalScored.filter((r) => r.correctness_score >= 1.0).length / total;
  const avgCorrectness = finalScored.reduce((s, r) => s + r.correctness_score, 0) / total;
  const retrievalResults = finalScored.filter((r) => r.tags.some((t: string) => retrievalTags.includes(t)));
  const avgPrecision = retrievalResults.length ? retrievalResults.reduce((s, r) => s + r.retrieval_precision, 0) / retrievalResults.length : 0;
  const avgRecall = retrievalResults.length ? retrievalResults.reduce((s, r) => s + r.retrieval_recall, 0) / retrievalResults.length : 0;
  const hitRate = finalScored.filter((r) => r.retrieval_hit).length / total;

  const summaryPath = resolve(RESULTS_DIR, "summary.json");
  writeFileSync(summaryPath, JSON.stringify({
    timestamp: new Date().toISOString(), dataset_path: DATASET_PATH, total_cases: total,
    retrieval_cases: retrievalResults.length, answer_accuracy: Math.round(accuracy*100)/100,
    average_correctness: Math.round(avgCorrectness*100)/100, retrieval_precision: Math.round(avgPrecision*100)/100,
    retrieval_recall: Math.round(avgRecall*100)/100, retrieval_hit_rate: Math.round(hitRate*100)/100, average_faithfulness: Math.round(finalScored.reduce((s, r) => s + (r.faithfulness_score || 0), 0) / total * 100) / 100, hallucination_rate: Math.round(finalScored.filter((r) => r.hallucination_detected).length / total * 100) / 100, judge_correctness: Math.round(finalScored.reduce((s, r) => s + ((r.judge?.correctness ?? 0) as number), 0) / total * 100) / 100, judge_relevance: Math.round(finalScored.reduce((s, r) => s + ((r.judge?.relevance ?? 0) as number), 0) / total * 100) / 100, judge_faithfulness: Math.round(finalScored.reduce((s, r) => s + ((r.judge?.faithfulness ?? 0) as number), 0) / total * 100) / 100,
    per_case: finalScored.map((r) => ({id: r.id, tags: r.tags, correctness_score: r.correctness_score, retrieval_precision: r.retrieval_precision, retrieval_recall: r.retrieval_recall, retrieval_hit: r.retrieval_hit, answer_length: (r.answer||"").length, sources_count: (r.retrieved_sources||[]).length, faithfulness_score: r.faithfulness_score || 0, unsupported_claims: r.unsupported_claims || [], hallucination_detected: !!r.hallucination_detected, judge_correctness: r.judge?.correctness ?? 0, judge_relevance: r.judge?.relevance ?? 0, judge_faithfulness: r.judge?.faithfulness ?? 0, judge_reason: r.judge?.reason ?? ""}))
  }, null, 2), "utf-8");
  console.log(`\nSummary written to ${summaryPath}`);
  console.log(`  answer_accuracy: ${Math.round(accuracy*100)/100}`);
  console.log(`  average_correctness: ${Math.round(avgCorrectness*100)/100}`);
  console.log(`  retrieval_precision: ${Math.round(avgPrecision*100)/100}`);
  console.log(`  retrieval_recall: ${Math.round(avgRecall*100)/100}`);
  console.log(`  retrieval_hit_rate: ${Math.round(hitRate*100)/100}`);
  console.log("LLM-as-judge integrated alongside deterministic metrics. Structured JSON validated loudly.");
}
main().catch((err) => { console.error(err); process.exit(1); });
