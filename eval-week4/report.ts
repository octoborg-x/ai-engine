import { readFileSync, writeFileSync } from "fs";
import { resolve } from "path";

const results = JSON.parse(readFileSync("eval/results/summary.json", "utf-8"));
const baseline = JSON.parse(readFileSync("eval/baseline.json", "utf-8"));

let report = `# AI Evaluation Report — Week 4 Day 5

## Quality
- answer_accuracy: ${results.answer_accuracy}
- average_correctness: ${results.average_correctness}
- judge_correctness: ${results.judge_correctness}
- judge_relevance: ${results.judge_relevance}
- judge_faithfulness: ${results.judge_faithfulness}

## Retrieval
- retrieval_precision: ${results.retrieval_precision}
- retrieval_recall: ${results.retrieval_recall}
- retrieval_hit_rate: ${results.retrieval_hit_rate}
- average_faithfulness: ${results.average_faithfulness}

## Hallucination / Faithfulness
- hallucination_rate: ${results.hallucination_rate}

## Performance
- average_latency_ms: ${results.average_latency_ms}
- p50_latency_ms: ${results.p50_latency_ms}
- p95_latency_ms: ${results.p95_latency_ms}

## Token Usage
- total_input_tokens: ${results.total_input_tokens}
- total_output_tokens: ${results.total_output_tokens}
- average_input_tokens: ${results.average_input_tokens}
- average_output_tokens: ${results.average_output_tokens}

## Cost
- total_cost_usd: ${results.total_cost_usd}
- average_cost_per_request_usd: ${results.average_cost_per_request_usd}

## Regression Baseline
- answer_accuracy baseline: ${baseline.answer_accuracy} (measured: ${results.answer_accuracy})
- hallucination_rate baseline: ${baseline.hallucination_rate} (measured: ${results.hallucination_rate})
- average_latency_ms baseline: ${baseline.average_latency_ms} (measured: ${results.average_latency_ms})
- average_cost_per_request_usd baseline: ${baseline.average_cost_per_request_usd} (measured: ${results.average_cost_per_request_usd})

## Comparison
`;

for (const [k,v] of Object.entries(results.baseline_comparison || {})) {
  let line = `- ${k}: ${v.value} ${v.op} ${v.threshold} -> ${v.status}`;
  report += line + "\n";
}

writeFileSync("eval/results/report.md", report, "utf-8");
console.log("Wrote eval/results/report.md");
