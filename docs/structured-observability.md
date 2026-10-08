# Structured Observability

The API emits JSON logs for the request lifecycle and each LLM attempt.

## Request lifecycle

request -> request.start -> LLM call -> llm.retry (when needed) -> LLM call -> request.end

Every HTTP request receives a request_id and trace_id. Existing x-request-id and x-trace-id headers are preserved; otherwise the API generates them and returns them in the response headers.

## LLM telemetry

A successful call contains fields equivalent to:

{"event":"llm.call","request_id":"req_...","trace_id":"trace_...","model":"provider/model","tier":"balanced","latency_ms":1234.0,"input_tokens":500,"output_tokens":200,"total_tokens":700,"cost_usd":0.002,"status":"success"}

Failed attempts emit status: error. Retry scheduling emits a separate llm.retry event with the attempt number and error type.

Prompt contents are intentionally excluded from telemetry.

Streaming calls are also timed, but token counts remain null when the provider does not expose usage through the current streaming path. Missing usage is not reported as zero.

## Metrics endpoint (Day 4)

GET /metrics returns aggregated, machine-readable production metrics.
- http_requests_total: by (method, path, status)
- http_latency_ms_avg: by (method, path) in ms
- llm_calls_total: by (model, status)
- llm_latency_ms_avg: by model in ms
- llm_input/output/total_tokens_total: aggregated
- llm_estimated_cost_usd_total: aggregated USD

Safe: only counts/avg/model names; no prompts/auth/user data.
