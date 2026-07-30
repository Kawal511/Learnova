"""
Learnova AI Provider Layer package.
Exposes core abstract interfaces and concrete vendor implementations.
"""

import os
# Disable pydantic plugin scanning before groq/pydantic are imported —
# prevents TimeoutError from Anaconda's entry_points.txt on macOS.
os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")

from providers.provider_base import LLMProvider, VisionProvider, EmbeddingProvider
from providers.llm_provider import GroqProvider
from providers.vision_provider import GeminiVisionProvider
from providers.embedding_provider import GeminiEmbeddingProvider

__all__ = [
    "LLMProvider",
    "VisionProvider",
    "EmbeddingProvider",
    "GroqProvider",
    "GeminiVisionProvider",
    "GeminiEmbeddingProvider",
]
