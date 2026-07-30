"""
Unit Tests for Learnova AI Provider Layer
Run with: pytest tests/test_providers.py -v
"""

import os
import pytest
from providers import GroqProvider, GeminiVisionProvider, GeminiEmbeddingProvider
from providers.provider_base import LLMProvider, VisionProvider, EmbeddingProvider


def test_provider_interfaces():
    # Verify that the providers subclass the correct interfaces
    assert issubclass(GroqProvider, LLMProvider)
    assert issubclass(GeminiVisionProvider, VisionProvider)
    assert issubclass(GeminiEmbeddingProvider, EmbeddingProvider)


@pytest.mark.skipif(not os.getenv("GROQ_API_KEY"), reason="GROQ_API_KEY not set")
def test_groq_provider_generate():
    provider = GroqProvider()
    response = provider.generate("Say hello", system_prompt="You are a friendly assistant")
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
def test_gemini_embedding_provider():
    provider = GeminiEmbeddingProvider()
    embeddings = provider.embed(["This is a test document."])
    assert isinstance(embeddings, list)
    assert len(embeddings) == 1
    assert isinstance(embeddings[0], list)
    assert len(embeddings[0]) > 0
    assert isinstance(embeddings[0][0], float)
