(condensed reference — expand only when we reach it)

**W1 — Python + LLM APIs.** Python/async/Pydantic/FastAPI/REST/env vars/OpenAI-Anthropic-Gemini APIs/streaming/structured JSON. Build: React→FastAPI→LLM→structured response, with chat, streaming, error handling, token/cost tracking. Claim: "I can integrate an LLM into a production app."

**W2 — RAG.** Embeddings/vector DBs/chunking/metadata/hybrid search/reranking/context construction/citations/eval. Build: multi-format (PDF/DOCX/TXT/web) knowledge assistant — Documents→Parsing→Chunking→Embeddings→VectorDB(pgvector/Qdrant)→Retriever→LLM→Answer+Sources. Must understand internals, not just call a library.

**W3 — Agents.** Tool/function calling/agent loops/state/memory/planning/multi vs single-agent/human approval/retries/timeouts/idempotency/MCP. Build: ops agent with `search_web()`, `search_documents()`, `get_customer()`, `create_ticket()`, `send_email()`, `update_database()` — enterprise-grade, not a toy.

**W4 — Evaluation (do not skip).** Hallucination/correctness/relevance/faithfulness/retrieval quality/latency/cost/regression testing/LLM-as-judge. Build: eval pipeline over 100 Qs against my own RAG system → dashboard of accuracy, retrieval quality, hallucination rate, latency, cost/request — real measured numbers.

**W5 — ML + PyTorch.** Classical: regression/classification/clustering/train-val-test/overfitting/regularization/precision-recall-F1/ROC-AUC. DL flow: Tensor→NN→Loss→Backprop→Optimizer→Training. PyTorch: tensors/datasets/dataloaders/training loops/inference. Engineering intuition > theorem-proving.

**W6 — Production/MLOps.** Docker/CI-CD/cloud deploy/model serving/logging/monitoring/tracing/queues/caching/rate limiting/retries/circuit breakers/secrets/auth. Build: React→Gateway→AI Service→Agent(RAG+Tools+LLM)→Postgres, plus Queue→Worker. Containerized and deployed.

**W7 — Advanced.** Architecture: transformers/attention/context windows/tokenization/temperature/sampling/quantization/fine-tuning vs RAG/LoRA-QLoRA. Security: prompt injection/data leakage/malicious docs/excess permissions/tool abuse/PII/access control. Build: User→Router→Agent(RAG+Tools+Memory+Sub-agents)→Validator→Human approval→Action.

**W8 — Portfolio (no new tech).** Package 3 flagship projects:
1. RAG Enterprise Assistant — ingestion, embeddings, vector search, citations, eval, auth, monitoring.
2. Autonomous Business Agent — request→knowledge search→customer lookup→issue determination→ticket→draft→human approval→send.
3. AI Production Platform (flagship) — React/TS/Node/Python/FastAPI/Postgres/Redis/Queue/Docker/LLM/RAG/Agent/Eval/CI-CD/Cloud/Observability.
