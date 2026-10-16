# RAG retrieval and grounded answering

This package is the single RAG implementation used by the backend's existing
`POST /ask` route. It provides provider-backed embeddings, a file-driven chunk
corpus and models, hybrid vector/BM25 recall, candidate fusion, reranking,
citation-tagged context, and citation validation.

## Architecture

`service.py` is the integration boundary used by `app/main.py`. It builds
and caches one `RAGPipeline`, calls the existing LLM callable, and returns the
existing `AskResponse` schema. `app.rag.api:app` is a retrieval-only standalone
app for local tests; it shares the same retrieval service.

## Knowledge base (local source files)

The corpus is loaded from `corpus/source_docs/` at startup (override with the
`CORPUS_DIR` environment variable). Every `.md`/`.txt` file there becomes part
of the knowledge base — that drop-a-file workflow is the "upload" path, and it
needs no PDF/DOCX parser. Markdown headings become logical sections; each
section is one chunk. Documents without headings are chunked by paragraph
windows. Adding a document requires a service restart so the chunk index is
rebuilt.

Supported formats: `.md`, `.markdown`, `.txt`. `.pdf`/`.docx` files in the
corpus directory are ignored.

## Providers

A single provider drives both the answer LLM and the embeddings. Precedence is
OpenRouter first, OpenAI next, then Gemini. Each provider is fully
self-contained — its API key, base URL, chat model, and embedding model all
come from the same provider:

- `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL` + `OPENROUTER_MODEL` +
  `OPENROUTER_EMBEDDING_MODEL`
- `OPENAI_API_KEY` + `OPENAI_BASE_URL` + `OPENAI_MODEL` +
  `OPENAI_EMBEDDING_MODEL`
- `GEMINI_API_KEY` + `GEMINI_BASE_URL` + `GEMINI_MODEL` +
  `GEMINI_EMBEDDING_MODEL`

A key is never sent to another provider's endpoint. `MODEL_NAME` remains the
fallback chat model for every provider. The legacy `LLM_API_KEY` /
`LLM_BASE_URL` pair is aliased to the Gemini provider.

Embedding defaults: OpenRouter `openai/text-embedding-3-small`, OpenAI
`text-embedding-3-small`, Gemini `text-embedding-004` (each overridable with
`<PROVIDER>_EMBEDDING_MODEL`). Without any key — or with
`EMBEDDINGS_OFFLINE=1` — embedding requests return a zero vector so local
development, tests, and BM25 retrieval remain available.

Run the repository tests with `pytest`. RAG-specific tests cover retrieval,
fusion, reranking, citations, API contracts, and model configuration.
