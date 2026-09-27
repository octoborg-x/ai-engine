# Week 4, Day 1 — AI Evaluation Dataset + Baseline Runner

This directory establishes the evaluation contract for the agent/RAG system before adding judges or dashboards.

## What is here

- `dataset.jsonl` — 20 labeled evaluation cases (JSON Lines)
- `run_eval.ts` — deterministic TypeScript runner that calls the real system
- `results/` — output directory with raw results per run

## Why this order matters

The curriculum separates evaluation concerns explicitly:

- correctness
- relevance
- faithfulness / hallucination
- retrieval quality
- latency
- token usage
- cost
- regression testing
- LLM-as-judge (added later)

This step captures the first six. No judge, no dashboard.

## Dataset categories (20 cases)

| Category | Count | Tags |
|---|---|---|
| Straightforward factual | 5 | `correctness`, `factual` |
| Retrieval from specific documents | 5 | `correctness`, `retrieval`, `relevance` |
| Hallucination exposure | 5 | `faithfulness`, `hallucination` |
| Multi-step reasoning | 5 | `correctness`, `retrieval`, `multi-step` |

Every case has:
- `id`
- `question`
- `expected_answer`
- `expected_sources` (specified for retrieval and multi-step cases)
- `tags`

## Running the runner

Requires the Python backend to be available at the default endpoint (`http://127.0.0.1:8000` by default, override with `EVAL_BASE_URL`).

```bash
npx tsx eval/run_eval.ts
```

The runner:
1. Reads `eval/dataset.jsonl`
2. Calls `/ask` for each case against the real system
3. Records: `answer`, `retrieved_sources`, `latency_ms`, `input_tokens`, `output_tokens`, `cost_usd`
4. Writes two output files to `eval/results/`: full results JSON + flat meta summary

No mocked responses. No evaluator. The same dataset produces the same records; runtime metrics (latency, tokens, cost) naturally vary per call.

## Expanding later

To reach the curriculum target of ~100 questions, duplicate the pattern: add records to `dataset.jsonl` without changing the contract in `run_eval.ts`. When judges and regression dashboards are added, the raw results from this runner become the ground-truth input.
