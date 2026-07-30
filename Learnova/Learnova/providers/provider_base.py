"""
Abstract Base Classes for the Learnova AI Provider Layer.
Defines interfaces for LLM, Vision, and Embedding providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class LLMProvider(ABC):
    """Abstract interface for Language Model providers."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate content using a prompt and an optional system prompt.

        Args:
            prompt: User prompt.
            system_prompt: Optional instructions to guide model behavior.
            **kwargs: Provider-specific execution arguments (e.g. model, temperature).

        Returns:
            The generated text response.
        """
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """
        Generate a response based on a multi-turn chat message history.

        Args:
            messages: List of message dictionaries, e.g. [{"role": "user", "content": "..."}]
            **kwargs: Provider-specific execution arguments (e.g. model, temperature).

        Returns:
            The generated text response from the model.
        """
        pass

    @abstractmethod
    def rewrite(self, text: str, instructions: str, **kwargs: Any) -> str:
        """
        Rewrite an existing body of text according to instructions.

        Args:
            text: Original text to rewrite.
            instructions: Instructions on how to modify the text.
            **kwargs: Provider-specific execution arguments.

        Returns:
            The rewritten text.
        """
        pass


class VisionProvider(ABC):
    """Abstract interface for Vision/Multimodal AI providers."""

    @abstractmethod
    def describe_image(self, image_bytes: bytes, prompt: str, **kwargs: Any) -> str:
        """
        Generate a description of the image content based on a prompt.

        Args:
            image_bytes: Raw binary data of the image.
            prompt: Instruction prompt for the vision model.
            **kwargs: Provider-specific execution arguments.

        Returns:
            Structured text description of the image contents.
        """
        pass

    @abstractmethod
    def ocr_image(self, image_bytes: bytes, **kwargs: Any) -> str:
        """
        Perform OCR on an image to extract text elements.

        Args:
            image_bytes: Raw binary data of the image.
            **kwargs: Provider-specific execution arguments.

        Returns:
            Extracted text content from the image.
        """
        pass


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    def embed(self, texts: List[str], **kwargs: Any) -> List[List[float]]:
        """
        Generate embedding vectors for a list of input texts.

        Args:
            texts: List of strings to embed.
            **kwargs: Provider-specific execution arguments.

        Returns:
            A list of float lists, representing the embedding vectors.
        """
        pass
