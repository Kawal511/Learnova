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
from learnova.providers.base import LLMProvider
from learnova.providers.router import TASK_QUIZ, get_router
from learnova.logging_config import logger

load_dotenv()

DELAY_BETWEEN_CALLS = 0.5

SYSTEM_PROMPT = (
    "You are an educational quiz designer. "
    "Generate 1 multiple choice question based on the content provided. "
    "Return ONLY valid JSON: "
    '{"question": "...", "options": ["A) ...", "B) ...", "C) ...", "D) ..."], "correct": "A", "explanation": "..."}'
)

# Module-level singleton router — created once and reused. Avoids
# creating/destroying httpx pools, which causes macOS segfaults.
#
# Distractor quality is what makes a checkpoint worth answering, so TASK_QUIZ
# prefers Nemotron Ultra and falls back to Groq. Going through the router also
# means a Groq 429 no longer costs the deck its quizzes.
_quiz_provider: LLMProvider | None = None

def _get_quiz_provider() -> LLMProvider | None:
    global _quiz_provider
    if _quiz_provider is None:
        router = get_router()
        if not router.available:
            logger.warning("No LLM provider configured — skipping quiz generation.")
            return None
        _quiz_provider = router
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
                task=TASK_QUIZ,          # router picks the model per provider
                temperature=0.3,
                max_tokens=400,
                timeout=20.0,
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


def interleave_quizzes_into_slides(
    improved_results: list[dict],
    quizzes: list[dict],
    frequency: int = 4,
    inline: bool = True,
) -> list[dict]:
    """
    Attach a checkpoint question after every ``frequency`` slides.

    With ``inline=True`` (the default) the question is fixed to the *bottom of
    the slide that closes the run* as an ``inline_quiz`` payload, rather than
    interrupting the deck with a standalone slide. A checkpoint reads better
    beside the material it tests, and it keeps the slide count honest — the
    old behaviour inflated a 12-slide deck to 15.

    Passing ``inline=False`` restores the separate QUIZ slide.
    """
    if not quizzes:
        return improved_results

    final_deck: list[dict] = []
    quiz_idx = 0

    for position, slide_item in enumerate(improved_results, 1):
        item = slide_item
        due = position % frequency == 0 and quiz_idx < len(quizzes)

        if due and inline:
            q = quizzes[quiz_idx]
            quiz_idx += 1
            improved = dict(item.get("improved") or {})
            improved["inline_quiz"] = {
                "index": quiz_idx,
                "question": q.get("question", "What was the key idea in this section?"),
                "options": q.get("options", [])[:4],
                "correct": q.get("correct", "A"),
                "explanation": q.get("explanation", ""),
            }
            item = {**item, "improved": improved}

        final_deck.append(item)

        if due and not inline:
            q = quizzes[quiz_idx]
            quiz_idx += 1
            final_deck.append({
                "original": {"title": "Knowledge Checkpoint", "source": f"Quiz #{quiz_idx}"},
                "improved": {
                    "layout_type": "QUIZ",
                    "title": f"Checkpoint Quiz #{quiz_idx}",
                    "question": q.get("question", "What is the key takeaway so far?"),
                    "options": q.get("options", ["Option A", "Option B", "Option C", "Option D"]),
                    "correct": q.get("correct", "A"),
                    "explanation": q.get("explanation", "Review the previous takeaways."),
                    "takeaway": "Test your active recall.",
                },
            })

    return final_deck
