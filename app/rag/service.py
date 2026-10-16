"""Knowledge Assistant RAG service: hybrid retrieve -> rerank -> grounded answer."""

from collections.abc import Awaitable, Callable
from functools import lru_cache

from app.rag.corpus import build_corpus
from app.rag.embeddings import EmbeddingModel
from app.rag.pipeline import RAGPipeline
from app.rag.schemas import AskResponse, RetrievalResponse, SourceOut

LlmCall = Callable[[str], Awaitable[dict]]
SYSTEM_PROMPT = (
    "You are a support assistant. Answer using only the provided context. "
    "Cite the sources you use as [S1], [S2], and so on. If the context does "
    "not contain the answer, say you do not know."
)


@lru_cache(maxsize=1)
def get_pipeline() -> RAGPipeline:
    """Build the RAG pipeline over the canonical corpus, once per process."""
    embedder = EmbeddingModel()
    return RAGPipeline(build_corpus(embedder), embedder)


def rebuild_pipeline() -> RAGPipeline:
    """Rebuild the corpus after a knowledge file was added or removed."""
    get_pipeline.cache_clear()
    return get_pipeline()


def build_prompt(query: str, context: str) -> str:
    """Combine system instructions, retrieved context, and the question."""
    return f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}"


def sources_out(result: dict) -> list[SourceOut]:
    """Convert pipeline sources plus reranker scores into API source records."""
    return [
        SourceOut(
            source_id=s.source_id,
            chunk_id=s.chunk_id,
            source=s.source,
            page=s.page,
            section=s.section,
            score=score,
        )
        for s, score in zip(result["sources"], result["source_scores"], strict=False)
    ]


def retrieve(query: str, recall_k: int = 10, final_k: int = 3):
    """Run hybrid recall, rerank, and citation-tagged context building."""
    return get_pipeline().ask(query, recall_k=recall_k, final_k=final_k)


def retrieval_response(
    query: str, recall_k: int = 10, final_k: int = 3
) -> RetrievalResponse:
    """Retrieval-only response: candidates, rerank scores, and citations."""
    result = retrieve(query, recall_k=recall_k, final_k=final_k)
    return RetrievalResponse(
        query=result["query"],
        answer="",
        context=result["context"],
        sources=sources_out(result),
        retrieved_ids=result["retrieved_ids"],
        candidates=result["candidates"],
    )


async def answer(
    query: str, llm_call: LlmCall, recall_k: int = 10, final_k: int = 3
) -> AskResponse:
    """Retrieve context, ask the LLM, and validate citations in the answer."""
    pipeline = get_pipeline()
    result = pipeline.ask(query, recall_k=recall_k, final_k=final_k)
    completion = await llm_call(build_prompt(query, result["context"]))
    return AskResponse(
        query=result["query"],
        answer=completion["response"],
        context=result["context"],
        sources=sources_out(result),
        retrieved_ids=result["retrieved_ids"],
        candidates=result["candidates"],
        model=completion["model"],
        route=completion["route"],
        prompt_tokens=completion["prompt_tokens"],
        completion_tokens=completion["completion_tokens"],
        estimated_cost_usd=completion["estimated_cost_usd"],
        latency_ms=completion["latency_ms"],
        citations=pipeline.validate_answer(completion["response"], result["sources"]),
    )
