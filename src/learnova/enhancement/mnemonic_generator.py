"""
Learnova Enhancement Layer — Mnemonic Generator
=================================================
Generates:
  - mnemonic     : a memorable acronym, rhyme, or phrase encoding key concepts
  - learning_tips: study strategies, memory techniques, and recommended learning paths

Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from learnova.providers.base import LLMProvider
from learnova.logging_config import logger

_SYSTEM_PROMPT = """\
You are a cognitive learning specialist who creates powerful memory aids and study guidance. \
For the given topic, generate a JSON object with exactly these two keys:

1. "mnemonic" (string): A memorable acronym, phrase, or rhyme that encodes the key concepts.
   - For an acronym: each letter should represent one key concept (explain it after).
   - For a phrase/rhyme: it should be short, catchy, and meaningful.
   - Include a brief explanation of what each element represents.

2. "learning_tips" (array of strings): 3–5 specific, actionable study tips.
   - Reference proven learning techniques (spaced repetition, active recall, mind maps, etc.)
   - Be specific to this topic — not generic study advice.
   - Each tip ≤ 20 words.

Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""


def generate_mnemonic_and_tips(
    topic: str,
    context: str,
    llm: LLMProvider,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Generate a mnemonic and learning tips for a slide topic.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        **kwargs: Forwarded to the LLMProvider.

    Returns:
        Dict with keys: mnemonic (str), learning_tips (List[str]).
        Falls back to empty string/list on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        "Generate the mnemonic and learning tips JSON for this topic."
    )
    _default: Dict[str, Any] = {
        "mnemonic": "",
        "learning_tips": [],
    }
    try:
        raw = llm.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 400),
        )
        data = _parse_json_obj(raw)
        return {
            "mnemonic":      str(data.get("mnemonic", "")).strip(),
            "learning_tips": _as_str_list(data.get("learning_tips", [])),
        }
    except Exception as e:
        logger.warning("mnemonic_generator failed for '%s': %s", topic, e)
        return _default


def _parse_json_obj(raw: str) -> Dict[str, Any]:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    return json.loads(raw)


def _as_str_list(obj: Any) -> List[str]:
    if not isinstance(obj, list):
        return []
    return [str(item).strip() for item in obj if str(item).strip()]
