"""
Retriever Module for Learnova RAG Pipeline
Builds a FAISS vector store and retrieves relevant chunks by query.
"""

import os

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS

from rag.embedder import get_embeddings_model
from logger import logger

load_dotenv()


class ChunkRetriever:
    """Wraps a FAISS index built from text chunks."""

    def __init__(self, chunks: list[dict]):
        """
        Build a FAISS index from chunks.

        Args:
            chunks: List of chunk dicts (must have "text", "id", "title", "source").
        """
        self._chunks = chunks
        texts = [c["text"] for c in chunks]
        metadatas = [{"id": c["id"], "title": c["title"], "source": c["source"]}
                     for c in chunks]

        try:
            embeddings = get_embeddings_model()
            self._store = FAISS.from_texts(texts, embeddings, metadatas=metadatas)
            logger.info("FAISS index built with %d chunks", len(chunks))
        except Exception as e:
            logger.error("Failed to build FAISS index: %s", e, exc_info=True)
            raise ValueError(f"Failed to build FAISS index: {e}")

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """Return top-k chunks most relevant to the query."""
        try:
            docs = self._store.similarity_search(query, k=k)
            results = []
            for doc in docs:
                results.append({
                    "text": doc.page_content,
                    **doc.metadata,
                })
            return results
        except Exception as e:
            logger.error("Retrieval failed for query '%s': %s", query, e, exc_info=True)
            return []

    def get_all_chunks(self) -> list[dict]:
        """Return all original chunks (for full-file processing)."""
        return list(self._chunks)
