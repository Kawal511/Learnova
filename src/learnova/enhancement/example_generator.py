"""
Learnova Enhancement Layer — Example Generator
================================================
Generates 2–3 concrete, real-world examples for a slide topic.
Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from learnova.providers.base import LLMProvider
from learnova.logging_config import logger

_SYSTEM_PROMPT = (
    "You are an expert educational content designer specialising in concrete examples. "
    "Your examples must be:\n"
    "- Specific and real-world (name real companies, processes, or phenomena)\n"
    "- Immediately relatable to a student learning this topic for the first time\n"
    "- Short (1–2 sentences each)\n"
    "Return ONLY a valid JSON array of strings. No preamble, no markdown fences.\n"
    'Example format: ["Example 1 text.", "Example 2 text.", "Example 3 text."]'
)


def generate_examples(
    topic: str,
    context: str,
    llm: LLMProvider,
    n: int = 3,
    **kwargs: Any,
) -> List[str]:
    """
    Generate concrete real-world examples for a slide topic.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        n: Number of examples to generate (default 3).
        **kwargs: Forwarded to the LLMProvider (model, temperature, etc.).

    Returns:
        List of example strings. Empty list on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        f"Generate {n} concrete, real-world examples that illustrate this topic clearly."
    )
    try:
        raw = llm.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", 0.5),
            max_tokens=kwargs.get("max_tokens", 400),
        )
        return _parse_json_list(raw)
    except Exception as e:
        logger.warning("example_generator failed for '%s': %s", topic, e)
        return []


def _parse_json_list(raw: str) -> List[str]:
    """Extract a JSON array of strings from raw LLM output."""
    raw = raw.strip()
    # Strip markdown fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Find the first JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    items = json.loads(raw)
    return [str(item).strip() for item in items if str(item).strip()]
