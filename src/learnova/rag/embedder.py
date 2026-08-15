"""
Embedder Module for Learnova RAG Pipeline
Generates embeddings for text chunks using Google Generative AI.
"""

import os
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"

from dotenv import load_dotenv
from learnova.providers import GeminiEmbeddingProvider, EmbeddingProvider
from learnova.logging_config import logger

load_dotenv()


def get_embeddings_model() -> EmbeddingProvider:
    """Return a configured EmbeddingProvider instance."""
    return GeminiEmbeddingProvider()


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generate embeddings for each chunk's text.

    Args:
        chunks: List of chunk dicts from chunker (must have "text" key).

    Returns:
        List of dicts: [{"chunk": <original_chunk>, "embedding": [float, ...]}, ...]
    """
    provider = get_embeddings_model()
    texts = [c["text"] for c in chunks]

    try:
        vectors = provider.embed(texts)
    except Exception as e:
        logger.error("Embedding generation failed: %s", e, exc_info=True)
        raise ValueError(f"Embedding generation failed: {e}")

    results = []
    for chunk, vector in zip(chunks, vectors):
        results.append({"chunk": chunk, "embedding": vector})

    logger.info("Generated embeddings for %d chunks", len(results))
    return results
