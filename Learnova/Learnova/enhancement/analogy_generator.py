"""
Learnova Enhancement Layer — Analogy Generator
================================================
Generates comparative analogies to help students build accurate mental models.
Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, List

from providers.provider_base import LLMProvider
from logger import logger

_SYSTEM_PROMPT = (
    "You are a master educator who explains complex ideas through vivid analogies. "
    "Your analogies must:\n"
    "- Connect the topic to something universally familiar (everyday objects, common experiences)\n"
    "- Highlight a structural or functional similarity — not just a surface resemblance\n"
    "- Be phrased as 'X is like Y because...' or 'Think of X as Y...'\n"
    "Return ONLY a valid JSON array of strings. No preamble, no markdown fences.\n"
    'Example format: ["Analogy 1.", "Analogy 2."]'
)


def generate_analogies(
    topic: str,
    context: str,
    llm: LLMProvider,
    n: int = 2,
    **kwargs: Any,
) -> List[str]:
    """
    Generate comparative analogies for a slide topic.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        n: Number of analogies to generate (default 2).
        **kwargs: Forwarded to the LLMProvider.

    Returns:
        List of analogy strings. Empty list on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        f"Generate {n} clear analogies that help a student understand '{topic}' "
        "by connecting it to something familiar."
    )
    try:
        raw = llm.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", 0.6),
            max_tokens=kwargs.get("max_tokens", 300),
        )
        return _parse_json_list(raw)
    except Exception as e:
        logger.warning("analogy_generator failed for '%s': %s", topic, e)
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
