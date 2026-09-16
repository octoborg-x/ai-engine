# AI API Project — Evaluation Commands

## Setup
Create and activate a virtual environment, then install runtime dependencies and development tools from `pyproject.toml`:

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Create `.env` using the project's existing configuration:

```env
OPENROUTER_API_KEY=your_key
MODEL_NAME=your_model
```

## Start the API

From the repository root:

```bash
uvicorn app.main:app --reload
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

## Run the full evaluation

```bash
python evals/run_eval.py
```

The full suite contains **100 cases**:

- 40 chat cases
- 40 structured extraction cases
- 20 adversarial cases

It measures:

- Accuracy
- Structured-output/schema validity
- Latency: average, P50, P95, P99
- Input/output/total tokens
- Estimated cost
- Model failure rate
- API error rate
- Per-case results

Detailed JSON output is written to `evals/results/`

## Run individual suites

```bash
python evals/run_eval.py --suite chat
python evals/run_eval.py --suite extraction
python evals/run_eval.py --suite classification
python evals/run_eval.py --suite adversarial
```

## Evaluate another local API port

```bash
python evals/run_eval.py --base-url http://127.0.0.1:9000
```

## Regression workflow

Run before changing a model/prompt:

```bash
python evals/run_eval.py
```

Run again after the change and compare:

- Accuracy
- Schema validity
- P95 latency
- Token usage
- Cost/request
- Failure rate

The first baseline target is:

- Accuracy >= 90%
- Structured-output validity >= 95%
- Technical failure rate <= 5%
- P95 latency recorded
- Cost/request recorded

These are **engineering targets**, not current measured results.

## Evaluation limitations

The chat evaluator uses lightweight rubric checks (required concepts and forbidden claims), not an LLM-as-judge.

Extraction checks:

1. HTTP success
2. Required fields
3. Allowed enum values
4. Exact category/urgency/sentiment
5. Summary keyword coverage

This is the Week 1 baseline. Later work can add semantic judging, faithfulness, retrieval quality, and richer regression analysis.
