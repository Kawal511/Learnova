"""
Learnova AI Provider Layer package.
Exposes core abstract interfaces and concrete vendor implementations.
"""

import os

# Disable pydantic plugin scanning before groq/pydantic are imported —
# prevents TimeoutError from Anaconda's entry_points.txt scan.
os.environ.setdefault("PYDANTIC_DISABLE_PLUGINS", "1")

from learnova.providers.base import EmbeddingProvider, LLMProvider, VisionProvider
from learnova.providers.gemini_embedding import GeminiEmbeddingProvider
from learnova.providers.gemini_vision import GeminiVisionProvider
from learnova.providers.groq_provider import GroqProvider
from learnova.providers.nvidia_provider import NvidiaProvider
from learnova.providers.router import LLMRouter, get_router

__all__ = [
    "LLMProvider",
    "VisionProvider",
    "EmbeddingProvider",
    "GroqProvider",
    "NvidiaProvider",
    "GeminiVisionProvider",
    "GeminiEmbeddingProvider",
    "LLMRouter",
    "get_router",
]
