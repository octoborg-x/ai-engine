## How to confirm the production boundary

These are the checks I would use to validate it:

- **Rate limiting:** Send 11 authenticated requests from the same client within 60 seconds using the default settings. Expect a `429` response once the limit is exceeded. Repeat against two separate application instances to demonstrate why the counters are not globally shared.
- **Job durability:** Submit a job, then restart the application before retrieving its result. The in-memory implementation cannot guarantee recovery of that job.
- **Multi-instance consistency:** Submit a job to instance A, then retrieve its ID through instance B. There is no shared job store, so instance B may return `404`.
- **Real processing:** Inspect `process_prompt()` in `app/jobs.py`. Replace the placeholder with the actual LLM service and add tests for success, provider failure, retries, and job recovery before production use.

## Recommendations

Before production deployment, prioritize:

1. Redis or another shared store for rate limiting.
2. A durable queue and shared job-result storage.
3. Actual LLM-backed job processing.
4. User-level identity and authorization if multiple users or tenants will access the API.

> **Note:** The current shared bearer token is a useful baseline, but it is not fine-grained user authorization.
