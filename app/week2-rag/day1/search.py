"""Semantic search implementation using cosine similarity."""

import numpy as np


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""
    denominator = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)

    if denominator == 0:
        return 0.0

    return np.dot(vector_a, vector_b) / denominator


def search(query_vector, document_list, top_k=3):
    """Return the top_k most similar documents to a query vector."""
    scored_documents = []

    for document in document_list:
        similarity_score = cosine_similarity(
            query_vector,
            document["embedding"],
        )

        scored_documents.append(
            {
                "text": document["text"],
                "score": similarity_score,
            }
        )

    scored_documents.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return scored_documents[:top_k]


def main():
    """Run the semantic search demonstration."""

    document_list = [
        {
            "text": "Customers can request a refund within 30 days.",
            "embedding": np.array([0.95, 0.10, 0.05]),
        },
        {
            "text": "You can reset your password from account settings.",
            "embedding": np.array([0.05, 0.95, 0.10]),
        },
        {
            "text": "Shipping usually takes between 3 and 5 business days.",
            "embedding": np.array([0.10, 0.05, 0.95]),
        },
    ]

    demo_query_vector = np.array([0.90, 0.15, 0.05])

    search_results = search(
        demo_query_vector,
        document_list,
        top_k=2,
    )

    for result_item in search_results:
        print(f"{result_item['score']:.3f} - {result_item['text']}")


if __name__ == "__main__":
    main()
