"""Gemini Vision image description utilities for Learnova."""

import base64
import os
import time

from google import genai
from dotenv import load_dotenv

from logger import logger

load_dotenv()

IMAGE_PROMPT = (
    "You are an educational content assistant.\n"
    "Describe this image in 2-3 sentences focusing on\n"
    "what a student should learn from it.\n"
    "Be concise and educational."
)
DELAY_BETWEEN_CALLS = 0.5


def _mime_from_ext(ext: str) -> str:
    ext_l = (ext or "").lower().strip(".")
    if ext_l in {"jpg", "jpeg"}:
        return "image/jpeg"
    if ext_l == "webp":
        return "image/webp"
    if ext_l == "gif":
        return "image/gif"
    if ext_l == "bmp":
        return "image/bmp"
    return "image/png"


def describe_images(images: list[dict]) -> list[dict]:
    """Describe page images with Gemini Vision.

    Args:
        images: List like [{"index": 0, "bytes": b"...", "ext": "png", "base64": "..."}, ...]

    Returns:
        List like [{"index": 0, "description": "...", "bytes": b"..."}, ...]
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY missing; skipping image descriptions")
        return []

    client = genai.Client(api_key=api_key)

    described_images = []
    total = len(images or [])

    for idx, image in enumerate(images or []):
        try:
            image_bytes = image.get("bytes")
            if not image_bytes and image.get("base64"):
                image_bytes = base64.b64decode(image.get("base64"))
            if not image_bytes:
                continue

            mime_type = _mime_from_ext(image.get("ext", "png"))

            import io
            from PIL import Image
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.warning(f"Could not open image with PIL: {e}")
                continue

            # Add robust retry logic for Google's 503 errors
            max_retries = 3
            response = None
            last_err = None
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model="gemini-1.5-flash",
                        contents=[
                            IMAGE_PROMPT,
                            pil_img,
                        ]
                    )
                    break
                except Exception as e:
                    last_err = e
                    if "503" in str(e) or "429" in str(e):
                        time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s...
                    else:
                        break
            
            if not response:
                raise last_err or Exception("Failed to generate content")

            description = (getattr(response, "text", "") or "").strip()
            if description:
                described_images.append({
                    "index": image.get("index", idx),
                    "description": description,
                    "bytes": image_bytes,
                })
        except Exception as e:
            logger.error("Image description failed for image %s: %s", image.get("index", idx), e, exc_info=True)

        if idx < total - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    return described_images
