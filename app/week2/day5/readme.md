# Week 2 Day 5 — Hybrid Search + Reranking + Citations

Production retrieval is a two-stage pipeline, not a single fused score:

    Query
      ├── Vector recall  (semantic, top-k_v)
      ├── Keyword recall (BM25, top-k_k)
      │        ↓
      │   Candidate fusion (dedup, limit N)
      │        ↓
      │   Reranker  ← Step 2
      │        ↓
      │   Final context (top-k_r)
      │        ↓
      └── LLM → Answer + Citations  ← Step 3

## Why not one fused score like Day 4?
Day 4's alpha-weighted hybrid is fine for small corpora, but in production:
- Vector and keyword search have different failure modes; you want the UNION
  of their recalls, then a stronger model to re-order.
- The reranker (Step 2) sees the query + each candidate together and scores
  relevance directly — far more accurate than either first-stage signal.


# Week 2 day 5 -- canonical corpus

                         canonical corpus
                               │
                               ▼
                       build_corpus()
                               │
                     20 stable Chunk IDs
                               │
                               ▼
                     Day5RAGPipeline
                       │           │
                  vector          BM25
                       │           │
                       └─────┬─────┘
                             ▼
                          fusion
                             ▼
                         reranker
                             ▼
                          sources
                             ▼
                         citations