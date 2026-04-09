"""
Quiz Generator Module for Learnova
Uses Groq to create MCQ quizzes from improved slide content.
"""

import json
import os
import re
import time

from dotenv import load_dotenv
from groq import Groq

from logger import logger

load_dotenv()

DELAY_BETWEEN_CALLS = 0.3  # seconds

SYSTEM_PROMPT = (
    "You are an educational quiz designer. "
    "Generate 1 multiple choice question based on the content provided. "
    "Return ONLY valid JSON: "
    '{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct": "A", "explanation": "..."}'
)


def _get_client() -> Groq:
    """Return a configured Groq client."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    return Groq(api_key=api_key)


def _parse_llm_json(raw_response: str) -> dict | None:
    """Strip markdown fences and parse JSON from LLM output."""
    text = raw_response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_quizzes(improved_results: list[dict]) -> list[dict]:
    """
    Generate 1 MCQ per every 3 improved slides.

    Args:
        improved_results: List of {"original": ..., "improved": ...} dicts
                          from improver.improve_chunks().

    Returns:
        List of quiz dicts with keys: question, options, correct, explanation, source_slides.
    """
    client = _get_client()
    quizzes = []

    # Group into batches of 3
    for batch_start in range(0, len(improved_results), 3):
        batch = improved_results[batch_start : batch_start + 3]

        # Combine the improved bullets into one content block
        combined_parts = []
        source_slides = []
        for entry in batch:
            imp = entry["improved"]
            title = imp.get("title", "")
            bullets = "\n".join(f"- {b}" for b in imp.get("bullets", []))
            takeaway = imp.get("takeaway", "")
            combined_parts.append(f"{title}\n{bullets}\n{takeaway}".strip())
            source_slides.append(entry["original"].get("source", "?"))

        combined_content = "\n\n".join(combined_parts)

        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": combined_content},
                ],
                temperature=0.7,
                max_tokens=400,
            )
            raw_content = (completion.choices[0].message.content or "").strip()
            parsed = _parse_llm_json(raw_content)

            if parsed and "question" in parsed and "options" in parsed:
                parsed["source_slides"] = source_slides
                quizzes.append(parsed)
            else:
                logger.warning(
                    "Quiz gen returned non-JSON for slides %s, skipping", source_slides
                )
        except Exception as e:
            logger.error(
                "Groq quiz call failed for slides %s: %s",
                source_slides, e, exc_info=True,
            )

        # Rate-limit delay
        if batch_start + 3 < len(improved_results):
            time.sleep(DELAY_BETWEEN_CALLS)

    logger.info("Generated %d quiz(es) from %d improved slides via Groq",
                len(quizzes), len(improved_results))
    return quizzes
