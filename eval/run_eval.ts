// eval/run_eval.ts — baseline evaluation runner (Week 4, Day 1)
// Runs the 20-case dataset against the real Python RAG/chat system.
// No judge, no dashboard — captures raw system behavior only.

import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { createHash } from "crypto";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DATASET_PATH = resolve(__dirname, "dataset.jsonl");
const RESULTS_DIR = resolve(__dirname, "results");

mkdirSync(RESULTS_DIR, { recursive: true });

interface DatasetRecord {
  id: string;
  question: string;
  expected_answer: string;
  expected_sources: string[];
  tags: string[];
}

interface EvalResult {
  id: string;
  question: string;
  answer: string;
  retrieved_sources: string[];
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  timestamp: string;
}

const BASE_URL = process.env.EVAL_BASE_URL || "http://127.0.0.1:8000";

async function callSystem(query: string): Promise<{
  answer: string;
  sources: string[];
  latency_ms: number;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  estimated_cost_usd: number | null;
}> {
  const url = `${BASE_URL}/ask`;
  const body = JSON.stringify({ query, recall_k: 10, final_k: 3 });
  const start = performance.now();

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const latency_ms = Math.round(performance.now() - start);

    if (!res.ok) {
      const text = await res.text();
      return {
        answer: `API_ERROR (${res.status}): ${text}`,
        sources: [],
        latency_ms,
        prompt_tokens: null,
        completion_tokens: null,
        estimated_cost_usd: null,
      };
    }

    const data: any = await res.json();
    const sources: string[] = (data.sources || []).map((s: any) =>
      typeof s === "string" ? s : s.source || s.source_id || String(s)
    );

    return {
      answer: data.answer || data.response || "",
      sources,
      latency_ms,
      prompt_tokens: data.prompt_tokens ?? null,
      completion_tokens: data.completion_tokens ?? null,
      estimated_cost_usd: data.estimated_cost_usd ?? null,
    };
  } catch (err: any) {
    const latency_ms = Math.round(performance.now() - start);
    return {
      answer: `FETCH_ERROR: ${err.message || err}`,
      sources: [],
      latency_ms,
      prompt_tokens: null,
      completion_tokens: null,
      estimated_cost_usd: null,
    };
  }
}

async function main() {
  console.log("=== Week 4 Day 1 — Evaluation Dataset + Baseline Runner ===");
  console.log(`Dataset: ${DATASET_PATH}`);
  console.log(`Results dir: ${RESULTS_DIR}`);
  console.log(`System endpoint: ${BASE_URL}/ask\n`);

  if (!DATASET_PATH) {
    console.error("Dataset not found.");
    process.exit(1);
  }

  const raw = readFileSync(DATASET_PATH, "utf-8");
  const lines = raw.split("\n").filter((line) => line.trim().length > 0);
  const records: DatasetRecord[] = lines.map((line) => JSON.parse(line));

  console.log(`Loaded ${records.length} evaluation cases.\n`);

  const results: EvalResult[] = [];

  for (const record of records) {
    console.log(`Running ${record.id}: "${record.question}"`);
    const output = await callSystem(record.question);

    const result: EvalResult = {
      id: record.id,
      question: record.question,
      answer: output.answer,
      retrieved_sources: output.sources,
      latency_ms: output.latency_ms,
      input_tokens: output.prompt_tokens,
      output_tokens: output.completion_tokens,
      cost_usd: output.estimated_cost_usd,
      timestamp: new Date().toISOString(),
    };

    results.push(result);

    console.log(
      `  -> answer length: ${output.answer.length} chars | sources: ${output.sources.length} | latency: ${output.latency_ms}ms | tokens: ${output.prompt_tokens ?? "?"}/${output.completion_tokens ?? "?"} | cost: $${output.estimated_cost_usd ?? "?"}`
    );
  }

  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const outPath = resolve(RESULTS_DIR, `eval-${stamp}.json`);
  const metaPath = resolve(RESULTS_DIR, `eval-meta-${stamp}.json`);

  writeFileSync(
    outPath,
    JSON.stringify({ timestamp: stamp, base_url: BASE_URL, results }, null, 2),
    "utf-8"
  );

  // Also write a flat results file for easy inspection
  writeFileSync(
    metaPath,
    JSON.stringify(
      {
        timestamp: stamp,
        dataset_records: records.length,
        cases_completed: results.length,
        total_latency_ms: results.reduce((s, r) => s + r.latency_ms, 0),
        cases_with_sources: results.filter(
          (r) => r.retrieved_sources.length > 0
        ).length,
        cases_with_errors: results.filter(
          (r) => r.answer.startsWith("API_ERROR") || r.answer.startsWith("FETCH_ERROR")
        ).length,
        results: results.map((r) => ({
          id: r.id,
          tags: records.find((rec) => rec.id === r.id)?.tags || [],
          latency_ms: r.latency_ms,
          sources_count: r.retrieved_sources.length,
          input_tokens: r.input_tokens,
          output_tokens: r.output_tokens,
          cost_usd: r.cost_usd,
          has_error: r.answer.startsWith("API_ERROR") || r.answer.startsWith("FETCH_ERROR"),
        })),
      },
      null,
      2
    ),
    "utf-8"
  );

  console.log(`\nResults saved to:`);
  console.log(`  Detailed: ${outPath}`);
  console.log(`  Summary:  ${metaPath}`);

  // Verify determinism of dataset (same dataset twice = same records)
  const datasetHash = createHash("sha256").update(raw).digest("hex").slice(0, 16);
  console.log(`\nDataset SHA-256 (first 16 chars): ${datasetHash}`);
  console.log(`Dataset records: ${records.length}`);
  console.log(`Every record has expected_answer: ${records.every((r) => !!r.expected_answer)}`);
  console.log(`Retrieval cases have expected_sources: ${records.filter((r) => r.tags.includes("retrieval") || r.tags.includes("multi-step")).every((r) => Array.isArray(r.expected_sources))}`);
  console.log(`No evaluator or judge added.`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
