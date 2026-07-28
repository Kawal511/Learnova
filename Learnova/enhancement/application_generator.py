"""
Learnova Enhancement Layer — Application Generator
====================================================
Generates practical real-world applications of a concept across industries.
Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, List

from providers.provider_base import LLMProvider
from logger import logger

_SYSTEM_PROMPT = (
    "You are an applied learning specialist who bridges academic theory with real-world practice. "
    "Each application must:\n"
    "- Name the specific industry, field, or context (e.g., healthcare, finance, agriculture)\n"
    "- Describe concretely HOW the concept is applied or why it matters there\n"
    "- Be distinct from the others — no repetition of the same domain\n"
    "Return ONLY a valid JSON array of strings. No preamble, no markdown fences.\n"
    'Example format: ["In healthcare: ...", "In finance: ...", "In agriculture: ..."]'
)


def generate_applications(
    topic: str,
    context: str,
    llm: LLMProvider,
    n: int = 3,
    **kwargs: Any,
) -> List[str]:
    """
    Generate real-world applications of a concept across different industries.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        n: Number of applications to generate (default 3).
        **kwargs: Forwarded to the LLMProvider.

    Returns:
        List of application strings. Empty list on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        f"Generate {n} real-world applications of '{topic}' across different "
        "industries or practical domains."
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
        logger.warning("application_generator failed for '%s': %s", topic, e)
        return []


def _parse_json_list(raw: str) -> List[str]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    items = json.loads(raw)
    return [str(item).strip() for item in items if str(item).strip()]
