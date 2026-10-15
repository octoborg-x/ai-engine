# AI system evaluation

This package evaluates the existing backend through its public `POST /ask`
contract, scores generated answers and retrieval quality, supports an optional
LLM-as-judge, and produces JSON summaries and a Markdown report.

## Components

- `dataset.jsonl`: labeled evaluation cases.
- `run_eval.ts`: calls the live backend and stores raw results plus metadata.
- `score_results.ts`: computes correctness, retrieval, faithfulness, and judge
  metrics from the most recent raw run.
- `judge.ts`: optional model-based scoring adapter.
- `baseline.json`: regression thresholds/reference values.
- `dashboard.ts`, `report.ts`: result presentation.
- `results/`: checked-in example outputs; new runs create timestamped files.

## Run

Start the Python backend, then from the repository root:

```bash
npx tsx app/eval/run_eval.ts
npx tsx app/eval/score_results.ts
npx tsx app/eval/report.ts
```

Set `EVAL_BASE_URL` to override the backend URL (default
`http://127.0.0.1:8000`). Judge scoring additionally requires a supported
provider API key. Raw collection and deterministic metrics work independently
of the judge.

## Metrics

The evaluator tracks answer correctness, retrieval precision/recall/hit rate,
faithfulness and unsupported claims, judge scores, latency, token usage, and
estimated cost when the API returns those fields. Treat lexical correctness and
faithfulness scores as practical regression signals, not as substitutes for
human review.
