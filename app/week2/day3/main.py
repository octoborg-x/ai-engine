"""
Main entry point for the RAG (Retrieval-Augmented Generation) system.
This module handles the ingestion of a Markdown handbook and provides a CLI for querying.
"""

import os

# pylint: disable=import-error
from embeddings import generate_embedding
from models import Chunk
from retriever import Retriever
from vector_store import VectorStore


def load_and_chunk_handbook(file_path: str):
    """Loads a markdown file and chunks it by H2 sections for indexing."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple chunking by Markdown sections (H2)
    sections = content.split("\n## ")
    chunks = []

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        lines = section.split("\n")
        title = lines[0].strip("# ")
        body = "\n".join(lines[1:]).strip()

        # Create a metadata-rich chunk
        text_to_embed = f"{title}\n{body}"
        embedding = generate_embedding(text_to_embed)

        chunks.append(
            Chunk(
                id=f"handbook_chunk_{i}",
                text=body,
                embedding=embedding,
                metadata={
                    "document_id": "employee_handbook",
                    "section": title,
                    "page": (i // 2) + 1,  # Dummy page calculation
                },
            )
        )
    return chunks


def main():
    """Initializes the store, indexes the handbook, and starts the interactive CLI."""
    handbook_path = (
        "/home/miloudlafttah849/ai-api-project/week2/day3/"
        "employee_handbook_rag_source.md"
    )

    if not os.path.exists(handbook_path):
        print(f"Error: Handbook not found at {handbook_path}")
        return

    store = VectorStore()
    print("Indexing Employee Handbook...")
    chunks = load_and_chunk_handbook(handbook_path)
    for c in chunks:
        store.add_chunk(c)

    retriever = Retriever(store)
    print("Indexing complete. (Type 'exit' to quit)")

    while True:
        query = input("\nQuery: ")
        if query.lower() in ["exit", "quit"]:
            break

        results = retriever.search(query, top_k=3)

        print("\nResults:")
        for i, res in enumerate(results, 1):
            print(
                f"{i}. {res['metadata']['document_id']} / page {res['metadata']['page']}"
            )
            # Show a snippet of the text
            print(f"   {res['text'][:150].replace(chr(10), ' ')}...")


if __name__ == "__main__":
    main()
