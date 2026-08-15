"""
Learnova Enhancement Layer — Question Generator
=================================================
Generates:
  - interview_questions  : technical interview / viva / exam questions
  - discussion_questions : open-ended Socratic discussion prompts

Uses only the LLMProvider interface — no SDK-specific code.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from learnova.providers.base import LLMProvider
from learnova.logging_config import logger

_SYSTEM_PROMPT = """\
You are an expert assessment designer for educational content. For the given topic, \
generate a JSON object with exactly these two keys:

1. "interview_questions" (array of strings): 3–5 technical interview, viva, or exam questions.
   These should test genuine understanding of mechanism, application, and edge cases.
   Not simple recall questions — target higher-order thinking (Bloom's Analyze / Evaluate).

2. "discussion_questions" (array of strings): 3–4 open-ended Socratic discussion prompts.
   These should provoke debate, comparison, or ethical reflection.
   Start each with "Why...", "How...", "What would happen if...", "In what ways..."

Return ONLY valid JSON. No markdown, no explanation outside the JSON.
"""


def generate_questions(
    topic: str,
    context: str,
    llm: LLMProvider,
    **kwargs: Any,
) -> Dict[str, List[str]]:
    """
    Generate interview questions and discussion questions for a slide topic.

    Args:
        topic: The main concept / slide title.
        context: Additional context derived from SlideIntelligence / TransformationPlan.
        llm: LLMProvider instance (injected by the engine).
        **kwargs: Forwarded to the LLMProvider.

    Returns:
        Dict with keys: interview_questions, discussion_questions.
        Falls back to empty lists on failure.
    """
    prompt = (
        f"Topic: {topic}\n\n"
        f"Context:\n{context}\n\n"
        "Generate the questions JSON for this topic."
    )
    _default: Dict[str, List[str]] = {
        "interview_questions": [],
        "discussion_questions": [],
    }
    try:
        raw = llm.generate(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            temperature=kwargs.get("temperature", 0.5),
            max_tokens=kwargs.get("max_tokens", 500),
        )
        data = _parse_json_obj(raw)
        return {
            "interview_questions":  _as_str_list(data.get("interview_questions", [])),
            "discussion_questions": _as_str_list(data.get("discussion_questions", [])),
        }
    except Exception as e:
        logger.warning("question_generator failed for '%s': %s", topic, e)
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
