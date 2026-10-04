                INDEXING TIME
                ──────────────

Documents
    ↓
Parsing
    ↓
Chunking
    ↓
Embedding model
    ↓
Vectors
    ↓
Vector DB


                QUERY TIME
                ───────────

User question
    ↓
Embedding model
    ↓
Query vector
    ↓
Vector search
    ↓
Top-K chunks
    ↓
Reranking
    ↓
Context
    ↓
LLM
    ↓
Answer + citations
