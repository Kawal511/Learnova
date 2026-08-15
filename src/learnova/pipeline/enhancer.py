"""
Bridge that wires ``enhancement/`` into the runtime pipeline.

``ContentEnhancementEngine`` wants a ``TransformationPlan`` and a
``SlideIntelligence`` — objects the runtime path never built, which is why the
package sat unused. This module constructs both from a chunk of text and runs
the engine over the deck.

Every call is LLM-backed, so this stage is:
  * **optional** — skipped entirely at ``low`` density,
  * **degrading** — a provider failure yields an empty ``EnhancedSlide`` rather
    than failing the run,
  * **bounded** — only the first N slides are enhanced, since each slide costs
    six sequential LLM calls and a 60-slide deck would take minutes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from learnova.logging_config import logger

# Enhancing every slide of a long deck is too slow to sit in a request path.
MAX_ENHANCED_SLIDES = 12


def _build_intel_and_plan(title: str, text: str, slide_id: int):
    """Recreate the two objects the enhancement engine expects."""
    from learnova.intelligence.engine import SlideIntelligenceEngine
    from learnova.intelligence.transformation import SlideTransformationEngine
    from learnova.pipeline.visual_planner import _build_slide_entity

    entity = _build_slide_entity(title, text, slide_id)
    intel = SlideIntelligenceEngine().analyze_slide(entity)
    plan = SlideTransformationEngine().plan_transformation(intel, entity)
    return intel, plan


def _empty(slide_id: int, title: str):
    from learnova.enhancement.schema import EnhancedSlide

    return EnhancedSlide(slide_id=slide_id, slide_title=title)


def enhance_deck(
    deck: List[dict],
    density: str = "medium",
    max_slides: int = MAX_ENHANCED_SLIDES,
) -> Dict[int, Any]:
    """
    Produce an ``EnhancedSlide`` per slide, keyed by deck index.

    Returns an empty mapping when no LLM provider is configured — the caller
    then simply renders the original content.
    """
    from learnova.pipeline.density import get_profile

    profile = get_profile(density)
    if not profile.include_enhancement:
        logger.info("enhancement skipped: density '%s' does not use it", profile.id)
        return {}

    provider = _resolve_provider()
    if provider is None:
        logger.info("enhancement skipped: no LLM provider available")
        return {}

    from learnova.enhancement.engine import ContentEnhancementEngine

    engine = ContentEnhancementEngine(provider)
    results: Dict[int, Any] = {}

    for index, entry in enumerate(deck):
        if len(results) >= max_slides:
            logger.info("enhancement capped at %d slide(s)", max_slides)
            break

        improved = entry.get("improved") or {}
        if str(improved.get("layout_type", "")).upper() == "QUIZ":
            continue

        title = improved.get("title") or entry.get("original", {}).get("title") or ""
        text = entry.get("original", {}).get("text") or "\n".join(
            improved.get("bullets") or []
        )
        if not text.strip():
            continue

        try:
            intel, plan = _build_intel_and_plan(title, text, index)
            results[index] = engine.enhance(plan, intel)
        except Exception as exc:
            # One bad slide must not sink the deck.
            logger.warning("enhancement failed for slide %d (%s)", index, exc)
            results[index] = _empty(index, title)

    logger.info("enhancement produced content for %d slide(s)", len(results))
    return results


def _resolve_provider():
    """Return an LLMProvider, or None when nothing is configured."""
    try:
        from learnova.providers.router import get_router

        router = get_router()
        if router.available:
            return router
    except Exception as exc:
        logger.debug("router unavailable: %s", exc)

    try:
        from learnova.providers.groq_provider import GroqProvider

        return GroqProvider()
    except Exception as exc:
        logger.debug("Groq unavailable: %s", exc)

    return None


__all__ = ["enhance_deck", "MAX_ENHANCED_SLIDES"]
