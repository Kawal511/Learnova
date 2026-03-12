"""
AI Improver Module for Learnova
Uses Gemini to transform raw slide text into polished educational content.
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from logger import logger

load_dotenv()

MAX_CHUNKS = 15
DELAY_BETWEEN_CALLS = 0.5  # seconds — avoid Gemini rate limits

IMPROVE_PROMPT = (
    "You are an expert educational content designer.\n"
    "Transform the given raw slide text into clean engaging teaching content.\n"
    "Return ONLY valid JSON:\n"
    '{{"title": "...", "bullets": ["...", "..."], "takeaway": "..."}}\n\n'
    "Raw text:\n{text}"
)


def _get_llm() -> ChatGoogleGenerativeAI:
    """Return a configured Gemini chat model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
    )


def _parse_llm_json(raw_response: str) -> dict | None:
    """Strip markdown fences and parse JSON from LLM output."""
    text = raw_response.strip()
    # Remove ```json ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def improve_chunks(chunks: list[dict]) -> list[dict]:
    """
    Send each chunk to Gemini for educational improvement.

    Args:
        chunks: List of chunk dicts (must have "title" and "text").

    Returns:
        List of dicts with keys: original, improved.
        'improved' is {"title", "bullets", "takeaway"} or a fallback dict.
    """
    llm = _get_llm()
    capped = chunks[:MAX_CHUNKS]
    results = []

    for i, chunk in enumerate(capped):
        prompt = IMPROVE_PROMPT.format(text=chunk["text"])
        try:
            response = llm.invoke(prompt)
            parsed = _parse_llm_json(response.content)

            if parsed and "title" in parsed and "bullets" in parsed:
                improved = parsed
            else:
                # Fallback — wrap the raw response as-is
                logger.warning("Chunk %d: LLM returned non-JSON, using fallback", chunk["id"])
                improved = {
                    "title": chunk["title"],
                    "bullets": [response.content.strip()],
                    "takeaway": "",
                }
        except Exception as e:
            logger.error("Gemini call failed for chunk %d: %s", chunk["id"], e, exc_info=True)
            improved = {
                "title": chunk["title"],
                "bullets": ["(AI improvement unavailable for this chunk)"],
                "takeaway": "",
            }

        results.append({"original": chunk, "improved": improved})

        # Rate-limit delay (skip after last chunk)
        if i < len(capped) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    logger.info("Improved %d / %d chunks via Gemini", len(results), len(chunks))
    return results
