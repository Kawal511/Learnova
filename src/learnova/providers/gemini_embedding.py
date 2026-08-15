"""
Embedding Providers Implementation for Learnova.
Contains GeminiEmbeddingProvider implementing the EmbeddingProvider interface.
"""

import os
from typing import Any, List, Optional
from learnova.providers.base import EmbeddingProvider


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Concrete implementation of EmbeddingProvider using langchain_google_genai."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "models/gemini-embedding-001",
    ):
        """
        Initialize the LangChain Google Generative AI Embeddings client.

        Args:
            api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY environment variable.
            model_name: Embedding model name.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        self.model_name = model_name
        
        # Lazy import to avoid loading gRPC C-libraries at startup. 
        # This prevents macOS thread conflicts (segfault exit 139) in Streamlit.
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=self.model_name,
            google_api_key=self.api_key,
        )

    def embed(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        Generate embedding vectors for the given text list.
        """
        return self.embeddings.embed_documents(texts)
