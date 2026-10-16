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

The answer LLM and the embedding provider share one resolution order:

1. `OPENROUTER_API_KEY` — primary (OpenRouter chat + embeddings).
2. `OPENAI_API_KEY` — fallback (or any OpenAI-compatible endpoint via
   `OPENAI_BASE_URL`).
3. `LLM_API_KEY` — generic fallback for OpenAI-compatible endpoints (Gemini,
   Groq, Hugging Face, ...) with `LLM_BASE_URL`.

`OPENAI_MODEL` selects the embedding model (default: `text-embedding-3-small`;
OpenRouter uses `openai/text-embedding-3-small` unless
`OPENROUTER_EMBEDDING_MODEL` is set). Without any key — or with
`EMBEDDINGS_OFFLINE=1` — embedding requests return a zero vector so local
development, tests, and BM25 retrieval remain available.

Run the repository tests with `pytest`. RAG-specific tests cover retrieval,
fusion, reranking, citations, API contracts, and model configuration.
