# AI Knowledge Assistant - Day 4 RAG

Modular Retrieval-Augmented Generation subsystem featuring robust context window control.

## Core Features
- **Hybrid Search**: Fuses semantic vector cosine similarity with lexical keyword overlap scores.
- **Metadata Filtering**: Supports hard multi-tenant isolation out-of-the-box via `tenant_id`.
- **Overlapping Chunk Deduplication**: Prevents redundant contexts from saturating token budgets.
- **Deterministic Context Builder**: Packs top-k chunks safely within an upper token limit.

## System Modules
- `vector_store.py`: Implementation of hybrid scorer and localized tenant filtering.
- `retriever.py`: Search orchestrator ensuring text diversity by stripping window overlaps.
- `context_builder.py`: Safe generation of structured context prompts with metadata headers.
