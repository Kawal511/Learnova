"""Gemini Vision image description utilities for Learnova."""

import base64
import os
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"

import time

from google import genai
from dotenv import load_dotenv

from logger import logger

load_dotenv()

IMAGE_PROMPT = (
    "You are an expert OCR and Educational Visual Content Transcriber.\n"
    "1. EXTRACT AND TRANSCRIBE ALL TEXT, LABELS, CAPTIONS, HEADINGS, NUMBERS, AND TABLES VISIBLE IN THIS IMAGE WORD-FOR-WORD.\n"
    "2. IF THIS IMAGE IS A DIAGRAM, FLOWCHART, ARCHITECTURE, OR INFOGRAPHIC, DESCRIBE EVERY NODE, STEP, ARROW, RELATIONSHIP, AND CONNECTED CONCEPT IN DETAIL.\n"
    "3. RETURN A STRUCTURED TEXT TRANSCRIPTION THAT CONTAINS ALL KNOWLEDGE AND TEXT FROM THE IMAGE SO IT CAN BE USED FOR EDUCATIONAL SLIDES."
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

    try:
        client = genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning("Could not initialize Gemini Client: %s", e)
        return []

    described_images = []
    total = len(images or [])
    quota_exceeded = False

    for idx, image in enumerate(images or []):
        if quota_exceeded:
            break

        try:
            image_bytes = image.get("bytes")
            if not image_bytes and image.get("base64"):
                image_bytes = base64.b64decode(image.get("base64"))
            if not image_bytes:
                continue

            import io
            from PIL import Image
            try:
                pil_img = Image.open(io.BytesIO(image_bytes))
            except Exception as e:
                logger.warning(f"Could not open image with PIL: {e}")
                continue

            max_retries = 2
            response = None

            # Models to try in priority order
            models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"]

            for model_name in models_to_try:
                if response:
                    break
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=[
                                IMAGE_PROMPT,
                                pil_img,
                            ]
                        )
                        if response and getattr(response, "text", None):
                            break
                    except Exception as e:
                        err_str = str(e)
                        if "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str:
                            logger.warning(
                                "Gemini Vision API quota limit reached on model %s: %s", model_name, err_str
                            )
                            if model_name == models_to_try[-1]:
                                quota_exceeded = True
                            break  # Try next model or stop
                        elif "503" in err_str or "429" in err_str:
                            time.sleep(1.5 * (attempt + 1))
                        else:
                            break  # non-retryable error for this model

            if not response:
                logger.warning("Could not describe image %s; skipping", image.get("index", idx))
                continue

            description = (getattr(response, "text", "") or "").strip()
            if description:
                described_images.append({
                    "index": image.get("index", idx),
                    "description": description,
                    "bytes": image_bytes,
                })
        except Exception as e:
            logger.warning("Image description skipped for image %s: %s", image.get("index", idx), e)

        if idx < total - 1 and not quota_exceeded:
            time.sleep(DELAY_BETWEEN_CALLS)

    return described_images
