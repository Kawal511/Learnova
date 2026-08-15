"""
Learnova Enhancement Layer — Revision Generator
=================================================
Generates:
  - improved_explanation  : pedagogically enhanced explanation of the concept
  - simplified_explanation: plain-language ELI5 version
  - revision_points       : concise bullet cheat sheet for review
  - common_mistakes       : frequent student misconceptions

Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from learnova.providers.base import LLMProvider
from learnova.logging_config import logger

_SYSTEM_PROMPT = """\
You are an expert educational content writer specialising in making complex topics \
crystal-clear. For the given topic, generate a JSON object with exactly these four keys:

1. "improved_explanation" (string): A rich, pedagogically enhanced explanation (3–5 sentences).
   Include key mechanisms, cause-and-effect relationships, and precise terminology.

2. "simplified_explanation" (string): A plain-language ELI5 explanation (2–3 sentences).
   Assume the reader knows nothing. Use simple words and a relatable comparison if possible.

3. "revision_points" (array of strings): 4–6 concise bullet points for last-minute review.
   Each bullet ≤ 15 words. Cover the most important facts, formulas, or steps.

4. "common_mistakes" (array of strings): 3–4 common student misconceptions or errors.
   Phrase each as what students wrongly believe AND why it is incorrect.

Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""


def generate_revision_content(
    topic: str,
    context: str,
    llm: LLMProvider,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Generate improved/simplified explanations, revision points, and common mistakes.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        **kwargs: Forwarded to the LLMProvider.

    Returns:
        Dict with keys: improved_explanation, simplified_explanation,
                        revision_points, common_mistakes.
        Falls back to empty strings/lists on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        "Generate the revision content JSON for this topic."
    )
    _default: Dict[str, Any] = {
        "improved_explanation": "",
        "simplified_explanation": "",
        "revision_points": [],
        "common_mistakes": [],
    }
    try:
        raw = llm.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", 0.4),
            max_tokens=kwargs.get("max_tokens", 700),
        )
        data = _parse_json_obj(raw)
        return {
            "improved_explanation":   str(data.get("improved_explanation", "")).strip(),
            "simplified_explanation": str(data.get("simplified_explanation", "")).strip(),
            "revision_points":        _as_str_list(data.get("revision_points", [])),
            "common_mistakes":        _as_str_list(data.get("common_mistakes", [])),
        }
    except Exception as e:
        logger.warning("revision_generator failed for '%s': %s", topic, e)
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
