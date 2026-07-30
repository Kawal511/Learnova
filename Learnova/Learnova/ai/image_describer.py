"""Gemini Vision image description utilities for Learnova."""

import base64
import os
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"

import time

from dotenv import load_dotenv
from providers import GeminiVisionProvider
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
    try:
        provider = GeminiVisionProvider()
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

            try:
                description = provider.describe_image(
                    image_bytes=image_bytes,
                    prompt=IMAGE_PROMPT,
                    models_to_try=["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"],
                    max_retries=2,
                )
                if description:
                    described_images.append({
                        "index": image.get("index", idx),
                        "description": description,
                        "bytes": image_bytes,
                    })
            except Exception as e:
                err_str = str(e)
                if "Quota exceeded" in err_str:
                    quota_exceeded = True
                logger.warning("Image description skipped for image %s: %s", image.get("index", idx), e)
        except Exception as e:
            logger.warning("Image description skipped for image %s: %s", image.get("index", idx), e)

        if idx < total - 1 and not quota_exceeded:
            time.sleep(DELAY_BETWEEN_CALLS)

    return described_images
