"""
Embedder Module for Learnova RAG Pipeline
Generates embeddings for text chunks using Google Generative AI.
"""

import os
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from logger import logger

load_dotenv()


def get_embeddings_model() -> GoogleGenerativeAIEmbeddings:
    """Return a configured GoogleGenerativeAIEmbeddings instance."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=api_key,
    )


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Generate embeddings for each chunk's text.

    Args:
        chunks: List of chunk dicts from chunker (must have "text" key).

    Returns:
        List of dicts: [{"chunk": <original_chunk>, "embedding": [float, ...]}, ...]
    """
    model = get_embeddings_model()
    texts = [c["text"] for c in chunks]

    try:
        vectors = model.embed_documents(texts)
    except Exception as e:
        logger.error("Embedding generation failed: %s", e, exc_info=True)
        raise ValueError(f"Embedding generation failed: {e}")

    results = []
    for chunk, vector in zip(chunks, vectors):
        results.append({"chunk": chunk, "embedding": vector})

    logger.info("Generated embeddings for %d chunks", len(results))
    return results
