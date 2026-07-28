"""
Vision Providers Implementation for Learnova.
Contains GeminiVisionProvider implementing the VisionProvider interface.
"""

import io
import os
import time
from typing import Any, Optional
from google import genai
from PIL import Image
from providers.provider_base import VisionProvider
from logger import logger


class GeminiVisionProvider(VisionProvider):
    """Concrete implementation of VisionProvider using Google GenAI SDK."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Gemini GenAI client.

        Args:
            api_key: Gemini API key. If not provided, reads from GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        self.client = genai.Client(api_key=self.api_key)

    def describe_image(self, image_bytes: bytes, prompt: str, **kwargs: Any) -> str:
        """
        Describe the image using Gemini model list.
        """
        try:
            pil_img = Image.open(io.BytesIO(image_bytes))
        except Exception as e:
            logger.warning("Could not open image with PIL in provider: %s", e)
            raise ValueError(f"Could not open image with PIL: {e}")

        models_to_try = kwargs.get(
            "models_to_try", ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]
        )
        max_retries = kwargs.get("max_retries", 2)
        response = None
        quota_exceeded = False

        for model_name in models_to_try:
            if response:
                break
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[
                            prompt,
                            pil_img,
                        ],
                    )
                    if response and getattr(response, "text", None):
                        return response.text.strip()
                except Exception as e:
                    err_str = str(e)
                    if "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
                        logger.warning(
                            "Gemini Vision API quota limit reached on model %s: %s",
                            model_name,
                            err_str,
                        )
                        if model_name == models_to_try[-1]:
                            quota_exceeded = True
                            raise ValueError(f"Quota exceeded: {err_str}")
                        break  # Try next model
                    elif "503" in err_str or "429" in err_str:
                        time.sleep(1.5 * (attempt + 1))
                    else:
                        break  # non-retryable error for this model

        if quota_exceeded:
            raise ValueError("Quota exceeded for all tried Gemini Vision models.")
        raise ValueError("Could not generate content from Gemini Vision API.")

    def ocr_image(self, image_bytes: bytes, **kwargs: Any) -> str:
        """
        OCR text elements of the image using a default transcription prompt.
        """
        prompt = kwargs.get(
            "prompt",
            "Perform OCR on this image and extract all readable text word-for-word.",
        )
        return self.describe_image(image_bytes, prompt, **kwargs)
