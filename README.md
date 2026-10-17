Demo

- Backend (FastAPI): https://ai-engine-octo-back.fastapicloud.dev/
- Frontend (Vercel): https://ai-engine-console.vercel.app/

Preview

"AI Engine Preview" (./bg.jpg)


# AI API Project

A production-style FastAPI backend for LLM integration — chat, streaming,
structured extraction, retry handling, cost tracking, and a Next.js AI Engineering Console.

## Monolith layout

The backend and frontend intentionally live in the same repository and are developed as one application boundary:

- `app/` — FastAPI backend and domain/infrastructure adapters
- `web/` — Next.js/React frontend
- `evals/` — evaluation datasets and runners
- `tests/` — backend tests

## Development Setup

To enable automatic linting and formatting on every commit:

```bash
pip install pre-commit
pre-commit install
```

In development, run FastAPI on port 8000 and Next.js on port 3000. Next.js proxies `/api/backend/*` to `BACKEND_URL`, keeping browser calls same-origin while preserving the backend boundary.

## Frontend

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000.

The Week 1 console exposes:

- streaming playground
- five selectable models (main + three routed tiers + an OpenAI-compatible slot)
- custom OpenAI-compatible provider UX boundary
- model comparison indices
- test suite indices
- evaluation dataset indices
- bearer-token auth UI
- rate-limit status
- structured observability/log readiness
- environment/configuration view

The console is a thin control layer over backend APIs: every panel reads live
backend state. It does not calculate domain metrics or invent benchmark values.

The console surfaces:

- streaming playground with a five-model selector (enforced by the backend router)
- live model list from `GET /models`
- tier comparison benchmarks from `GET /compare`
- packaged evaluation suites and runs from `GET /evals/suites` / `POST /evals/run`
- retrieval transparency (recall candidates + rerank scores) from `POST /rag/retrieve`
- grounded Knowledge Assistant answers with validated citations from `POST /ask`
- recruitment screening from `POST /recruitment/screen`
- auth and rate-limit policy from `GET /security/policy`
- request and LLM-call telemetry from `GET /observability/requests`
- a retrieval-quality dashboard at `/dashboard` backed by the retrieval suite
- saved results for Compare / Evals / dashboard / Recruitment, replayed by a
  fake-run button (progress bar + action trace, no provider calls) or measured
  live with a real-run button

Compare, eval, retrieval, and recruitment tabs render from saved result files
by default so opening them never exhausts the provider. A **Fake run** replays
those files with a progress animation and a per-tab action trace (rotating
example slots); a **Real run** executes the live pipeline and persists the
measured result back into the file store.

## Backend

Existing Python setup and `app/main.py` endpoints:

- `GET /health`
- `POST /chat` — single-turn chat (accepts optional `tier`)
- `POST /chat/stream` — streaming chat (accepts optional `tier`)
- `POST /ask` — Knowledge Assistant: hybrid retrieve -> rerank -> grounded, cited answer
- `POST /extract-ticket` — structured JSON extraction
- `GET /metrics` — aggregated HTTP/LLM counters and latency
- `GET /models` — routing tiers and the model each resolves to
- `POST /rag/retrieve` — retrieval only: candidates, rerank scores, citations
- `GET /compare` — measured per-tier benchmark across labeled chat cases
- `GET /evals/suites` — packaged evaluation suites and case counts
- `POST /evals/run` — run model-quality and retrieval suites
- `POST /recruitment/screen` — JD + resume screening with an auditable rubric
- `GET /security/policy` — non-secret auth and rate-limit policy
- `GET /observability/requests` — recent request and LLM-call records

## Existing backend capabilities

- Single-turn chat with token/cost tracking
- Streaming responses
- Structured JSON extraction
- Retry logic with exponential backoff
- Differentiated 429/504/502/500 errors
- Deterministic cheap/balanced/powerful routing with request-level model override
- Per-call model/token/latency/cost/success telemetry
- In-process request and LLM-call records for observability
- Bearer-token authentication on every LLM-invoking route
- Process-local rate limiting and `Retry-After`

## Knowledge Assistant (`/ask`)

`POST /ask` runs the Week 2 Day 5 RAG pipeline and returns a grounded answer with
sources. Request body:

```json
{"query": "what is the refund policy?", "recall_k": 10, "final_k": 3}
```

`recall_k` and `final_k` are optional. `recall_k` controls candidate recall per
channel (vector + BM25); `final_k` controls how many reranked chunks are sent as
context. The response includes `answer`, the citation-tagged `context`, `sources`,
`retrieved_ids`, model/route/token/cost metadata, and a `citations` report that
flags any hallucinated `[SN]` tags.

The retrieval/grounding layer lives in `app/rag/` and is shared with the standalone
Day 5 demo (`app/week2/day5/api.py`), which serves the same shapes without calling
a provider.

## Model routing

Routing is deterministic and adds no extra LLM call.

| Request | Tier |
|---|---|
| Explicit `tier` on the request (`main`/`cheap`/`balanced`/`powerful`/`openai-compatible`) | that tier, pinned |
| Classification / extraction | `cheap` |
| Normal chat | `balanced` |
| Complex reasoning, architecture, debugging, long prompts | `powerful` |

Configure:

```env
MODEL_NAME=your_existing_free_model
MODEL_CHEAP=your_free_cheap_model
MODEL_BALANCED=your_free_balanced_model
MODEL_POWERFUL=your_free_powerful_model
```

`MODEL_NAME` is exposed as the `main` model and is the default selection in the
streaming playground; the other three are the router's tiers. The
`openai-compatible` tier always resolves via `OPENAI_API_KEY` +
`OPENAI_BASE_URL` + `OPENAI_MODEL` — independent of the active provider — so
an OpenAI-compatible endpoint (Gemini, Groq, Together, …) can be used side by
side with OpenRouter. The Knowledge Assistant (`/ask`) shares the same model
selector via its optional `tier` field.

RAG retrieval embeddings follow the same provider: when `OPENAI_API_KEY` is
set, `OPENAI_EMBEDDING_MODEL` (default `gemini-embedding-001` for Gemini
endpoints, `text-embedding-3-small` for OpenAI) powers corpus indexing and
query retrieval. This matters because OpenRouter free tiers cannot call
`/embeddings`; with a Gemini/OpenAI key configured, retrieval works without
OpenRouter embedding access.
