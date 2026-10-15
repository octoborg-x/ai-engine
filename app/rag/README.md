# RAG retrieval and grounded answering

This package is the single RAG implementation used by the backend's existing
`POST /ask` route. It provides provider-backed embeddings, a canonical chunk
corpus and models, hybrid vector/BM25 recall, candidate fusion, reranking,
citation-tagged context, and citation validation.

## Architecture

`service.py` is the integration boundary used by `app/main.py`. It builds
and caches one `RAGPipeline`, calls the existing LLM callable, and returns the
existing `AskResponse` schema. `app.rag.api:app` is a retrieval-only standalone
app for local tests; it shares the same retrieval service.

## Configuration

Set `OPENROUTER_API_KEY` (primary) or `OPENAI_API_KEY` (fallback) to enable
remote embeddings. `OPENAI_MODEL` selects the embedding model (default:
`text-embedding-3-small`). Without a key — or with `EMBEDDINGS_OFFLINE=1` —
embedding requests return a zero vector so local development, tests, and BM25
retrieval remain available.

Run the repository tests with `pytest`. RAG-specific tests cover retrieval,
fusion, reranking, citations, API contracts, and model configuration.
