"""
Retriever Module for Learnova RAG Pipeline
Lightweight in-memory store — no FAISS, no gRPC, no C++ libs.

The full embedding pipeline (langchain_google_genai / gRPC) was causing macOS
SIGSEGV (exit 139) due to gRPC C-library thread conflicts. Since the retriever
is used only for context storage (never queried in the main pipeline), we skip
embedding entirely and use a simple list-based store with keyword matching.
"""

import os
from dotenv import load_dotenv
from logger import logger

load_dotenv()


class ChunkRetriever:
    """
    Lightweight in-memory chunk store.
    No FAISS, no gRPC, no C++ libraries — completely safe on macOS.
    Falls back to keyword-overlap scoring for retrieval.
    """

    def __init__(self, chunks: list[dict]):
        """
        Store chunks in memory. No API calls, no embeddings.

        Args:
            chunks: List of chunk dicts (must have "text", "id", "title", "source").
        """
        self._chunks = list(chunks)
        logger.info("FAISS index built with %d chunks", len(chunks))

    def retrieve(self, query: str, k: int = 3) -> list[dict]:
        """
        Return top-k chunks most relevant to the query using keyword overlap.
        Pure Python — no external libraries.
        """
        if not self._chunks:
            return []

        query_words = set(query.lower().split())

        scored = []
        for chunk in self._chunks:
            chunk_words = set(chunk.get("text", "").lower().split())
            overlap = len(query_words & chunk_words)
            scored.append((overlap, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [c for _, c in scored[:k]]
        return [{"text": c["text"], **{key: c[key] for key in ("id", "title", "source") if key in c}}
                for c in top]

    def get_all_chunks(self) -> list[dict]:
        """Return all original chunks (for full-file processing)."""
        return list(self._chunks)
