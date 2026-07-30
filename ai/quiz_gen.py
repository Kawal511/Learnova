"""
Quiz Generator Module for Learnova
Uses Groq to create MCQ quizzes and interleave checkpoint slides.

IMPORTANT: Do NOT use ThreadPoolExecutor here.
httpx.Client has internal keepalive connection pool background threads. When a ThreadPoolExecutor
exits and Python GC destroys the GroqProvider (httpx client), those background threads crash
macOS with exit code 139 (SIGSEGV). Sequential processing with module-level singleton is safe.
"""

import json
import os
import re
import time
from dotenv import load_dotenv
from providers import GroqProvider
from logger import logger

load_dotenv()

DELAY_BETWEEN_CALLS = 0.5

SYSTEM_PROMPT = (
    "You are an educational quiz designer. "
    "Generate 1 multiple choice question based on the content provided. "
    "Return ONLY valid JSON: "
    '{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct": "A", "explanation": "..."}'
)

# Module-level singleton GroqProvider — created once and reused.
# Avoids creating/destroying httpx pools which causes macOS segfaults.
_quiz_provider: GroqProvider | None = None

def _get_quiz_provider() -> GroqProvider | None:
    global _quiz_provider
    if _quiz_provider is None:
        try:
            _quiz_provider = GroqProvider(timeout=10.0)
        except Exception as e:
            logger.warning("Could not initialize Groq client for quizzes: %s", e)
    return _quiz_provider


def _parse_llm_json(raw_response: str) -> dict | None:
    text = raw_response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_quizzes(improved_results: list[dict]) -> list[dict]:
    """
    Generate MCQs for improved slides.
    Sequential execution — safe on macOS with httpx connection pools.
    """
    provider = _get_quiz_provider()
    if not provider:
        return []

    # Group slides into batches of 3
    batches = []
    for batch_start in range(0, len(improved_results), 3):
        batches.append(improved_results[batch_start : batch_start + 3])

    quizzes = []

    for idx, batch in enumerate(batches):
        combined_parts = []
        source_slides = []

        for entry in batch:
            imp = entry["improved"]
            title = imp.get("title", "")
            bullets = "\n".join(f"- {b}" for b in imp.get("bullets", []))
            takeaway = imp.get("takeaway", "")
            combined_parts.append(f"{title}\n{bullets}\n{takeaway}".strip())
            source_slides.append(entry.get("original", {}).get("source", "?"))

        combined_content = "\n\n".join(combined_parts)

        try:
            raw_content = provider.generate(
                prompt=f"Content:\n{combined_content}",
                system_prompt=SYSTEM_PROMPT,
                model="llama-3.1-8b-instant",
                temperature=0.3,
                max_tokens=400,
                timeout=10.0,
            )
            parsed = _parse_llm_json(raw_content)

            if parsed and "question" in parsed and "options" in parsed:
                raw_correct = str(parsed.get("correct", "A")).strip()
                match = re.search(r"([A-D])", raw_correct.upper())
                parsed["correct"] = match.group(1) if match else "A"
                parsed["source_slides"] = source_slides
                quizzes.append(parsed)
        except Exception as e:
            logger.error("Groq quiz call failed: %s", e)

        # Small delay between batches to respect TPM limits
        if idx < len(batches) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    logger.info("Generated %d quiz(es)", len(quizzes))
    return quizzes


def interleave_quizzes_into_slides(improved_results: list[dict], quizzes: list[dict], frequency: int = 4) -> list[dict]:
    """
    Interleaves quiz checkpoint slides into the slide sequence after every `frequency` slides.
    """
    if not quizzes:
        return improved_results

    final_deck = []
    quiz_idx = 0

    for i, slide_item in enumerate(improved_results, 1):
        final_deck.append(slide_item)
        if i % frequency == 0 and quiz_idx < len(quizzes):
            q_data = quizzes[quiz_idx]
            quiz_idx += 1
            checkpoint_slide = {
                "original": {"title": "Knowledge Checkpoint", "source": f"Quiz #{quiz_idx}"},
                "improved": {
                    "layout_type": "QUIZ",
                    "title": f"⚡ Checkpoint Quiz #{quiz_idx}",
                    "question": q_data.get("question", "What is the key takeaway from the previous slides?"),
                    "options": q_data.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                    "correct": q_data.get("correct", "A"),
                    "explanation": q_data.get("explanation", "Review previous slide takeaways."),
                    "takeaway": "Test your active recall!",
                }
            }
            final_deck.append(checkpoint_slide)

    return final_deck
