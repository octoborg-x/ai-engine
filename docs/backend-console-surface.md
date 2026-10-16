# Backend Console Surface

The console is a thin control layer. Every panel reads live backend state; the
UI does not compute domain metrics or invent benchmark values.

## Architecture

```
browser  ──►  Next.js server route  ──►  FastAPI backend
              /api/backend/*            BACKEND_URL
              injects Authorization
```

The browser only ever calls same-origin `/api/backend/*`. The Next.js route
handler attaches the shared bearer token server-side and forwards the request
upstream. The token lives in the frontend server environment, so any user of the
console can use the backend without the token ever reaching the browser.

Streaming responses are passed through untouched, so `/chat/stream` still
renders tokens incrementally.

## Endpoints the console uses

| Endpoint | Purpose | Auth |
|---|---|---|
| `GET /health` | liveness | public |
| `GET /metrics` | aggregated HTTP/LLM counters | public |
| `GET /models` | selectable models (main + tiers) and resolved model | protected |
| `GET /security/policy` | non-secret auth + rate-limit policy | protected |
| `POST /chat`, `POST /chat/stream` | chat, optional `tier` | protected |
| `POST /ask` | grounded answer with citations | protected |
| `POST /rag/retrieve` | retrieval only: candidates + rerank scores | protected |
| `GET /compare` | measured per-tier benchmark | protected |
| `GET /evals/suites`, `POST /evals/run` | packaged evaluation suites | protected |
| `POST /recruitment/screen` | JD + resume screening | protected |
| `GET /observability/requests` | recent request and LLM-call records | protected |

`GET /models` and `GET /security/policy` expose configuration, not secrets: tier
names, model ids, env var names, and the enforced policy. Neither returns the
token value.

## Security boundaries

- **Token**: injected by the server-side proxy; never sent to the browser and
  never present in the client bundle.
- **Auth**: bearer authentication enforced by middleware on every
  LLM-invoking route. Public routes are `GET /health` and `GET /metrics`.
- **Rate limit**: process-local fixed window keyed on the direct peer address.
  Forwarding headers are ignored so the limit cannot be bypassed with a spoofed
  `X-Forwarded-For`.
- **Telemetry**: request and LLM-call records store metadata only — route,
  status, latency, tokens, cost, and correlation IDs. Prompt and response
  contents are excluded.

## Evaluation methodology

Two kinds of measurement are kept deliberately separate.

**Model-quality suites** (`chat`, `extraction`, `classification`, `adversarial`)
call the live model against labeled cases and report accuracy, structured-output
validity, API-error rate, latency, tokens, and cost. Accuracy excludes provider
errors so an outage is not scored as a model failure.

**Retrieval suite** (`retrieval`) is deterministic and offline. It runs the
hybrid recall + rerank pipeline against labeled relevant chunk ids and reports
precision@k, recall@k, hit rate@k, and MRR. It makes no provider call, so it
costs nothing and runs anywhere. The `/dashboard` page renders this suite.

`GET /compare` runs the same labeled chat cases through all three tiers and
reports measured pass rate, latency percentiles, tokens, and cost per tier.

Engineering targets live in `evals/expected_metrics.json`. They are thresholds,
not measurements; the dashboard shows the real measurement beside them so a
regression is visible.

## Limitations

- Metrics and request records are in-process. They reset on restart and are not
  shared across workers; a multi-worker deployment would need an external store.
- The rate limiter is process-local. Behind multiple replicas the effective
  limit is per-replica.
- Benchmark and eval runs execute synchronously within one request and are
  bounded by `limit`, so they are unsuitable for large suites in production.
- Retrieval quality is measured against a small hand-labeled corpus. The numbers
  describe this corpus, not general retrieval quality.
