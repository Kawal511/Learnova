"""
Learnova Enhancement Layer — Educational Content Enhancement Engine
====================================================================
Day 7: Transforms technically correct slide content into educationally
effective learning material.

Consumes:
  - TransformationPlan  (from learnova.intelligence.transformation)
  - SlideIntelligence   (from learnova.intelligence.schema)

Produces:
  - EnhancedSlide       (from learnova.enhancement.schema)

All AI calls go exclusively through the LLMProvider interface.
No SDK-specific code, no rendering, no layout decisions, no PPT generation.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from learnova.intelligence.schema import SlideIntelligence
from learnova.intelligence.transformation import TransformationPlan
from learnova.providers.base import LLMProvider

from learnova.enhancement.schema import EnhancedSlide
from learnova.enhancement import example_generator
from learnova.enhancement import analogy_generator
from learnova.enhancement import application_generator
from learnova.enhancement import revision_generator
from learnova.enhancement import question_generator
from learnova.enhancement import mnemonic_generator

from learnova.logging_config import logger

# ── Defaults ──────────────────────────────────────────────────────────────────
_DEFAULT_LLM_KWARGS: dict = {
    "model": "llama-3.1-8b-instant",
    "temperature": 0.5,
    "max_tokens": 600,
}

# Delay between generator calls to avoid rate-limiting on shared API quotas
_DELAY_BETWEEN_CALLS: float = 0.3


class ContentEnhancementEngine:
    """
    Orchestrates all pedagogical enhancement generators to produce an EnhancedSlide.

    Usage:
        from learnova.providers import GroqProvider
        from learnova.enhancement.engine import ContentEnhancementEngine

        llm = GroqProvider()
        engine = ContentEnhancementEngine(llm)
        enhanced = engine.enhance(transformation_plan, slide_intelligence)
    """

    def __init__(self, llm: LLMProvider, delay: float = _DELAY_BETWEEN_CALLS):
        """
        Args:
            llm: Any LLMProvider implementation (e.g. GroqProvider).
                 The engine never imports or instantiates a concrete provider.
            delay: Seconds to wait between sub-generator calls (default 0.3).
        """
        if not isinstance(llm, LLMProvider):
            raise TypeError(
                "ContentEnhancementEngine requires an LLMProvider instance. "
                f"Got: {type(llm).__name__}"
            )
        self._llm = llm
        self._delay = delay

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def enhance(
        self,
        plan: TransformationPlan,
        intel: SlideIntelligence,
        **kwargs: Any,
    ) -> EnhancedSlide:
        """
        Run the full enhancement pipeline for one slide.

        Args:
            plan:   TransformationPlan produced by SlideTransformationEngine.
            intel:  SlideIntelligence produced by SlideIntelligenceEngine.
            **kwargs: Optional overrides forwarded to all generators
                      (e.g. model="llama-3.1-8b-instant", temperature=0.4).

        Returns:
            EnhancedSlide with all pedagogical enrichment fields populated.
            Any generator that fails gracefully degrades to empty string / empty list.
        """
        topic = intel.slide_title or intel.main_topic or f"Slide {intel.slide_id}"
        context = self._build_context(plan, intel)
        llm_kwargs = {**_DEFAULT_LLM_KWARGS, **kwargs}

        logger.info("ContentEnhancementEngine: enhancing '%s'", topic)

        # ── 1. Revision content (improved + simplified + points + mistakes) ──
        revision = self._call(
            revision_generator.generate_revision_content,
            topic, context, llm_kwargs,
            default={
                "improved_explanation": "",
                "simplified_explanation": "",
                "revision_points": [],
                "common_mistakes": [],
            },
        )
        self._sleep()

        # ── 2. Examples ───────────────────────────────────────────────────────
        examples = self._call(
            example_generator.generate_examples,
            topic, context, llm_kwargs,
            default=[],
        )
        self._sleep()

        # ── 3. Analogies ──────────────────────────────────────────────────────
        analogies = self._call(
            analogy_generator.generate_analogies,
            topic, context, llm_kwargs,
            default=[],
        )
        self._sleep()

        # ── 4. Real-world applications ────────────────────────────────────────
        applications = self._call(
            application_generator.generate_applications,
            topic, context, llm_kwargs,
            default=[],
        )
        self._sleep()

        # ── 5. Questions (interview + discussion) ─────────────────────────────
        questions = self._call(
            question_generator.generate_questions,
            topic, context, llm_kwargs,
            default={"interview_questions": [], "discussion_questions": []},
        )
        self._sleep()

        # ── 6. Mnemonic + learning tips ───────────────────────────────────────
        mnemonics = self._call(
            mnemonic_generator.generate_mnemonic_and_tips,
            topic, context, llm_kwargs,
            default={"mnemonic": "", "learning_tips": []},
        )

        # ── 7. Compute confidence ─────────────────────────────────────────────
        confidence = self._compute_confidence(
            plan=plan,
            intel=intel,
            revision=revision,
            examples=examples,
            analogies=analogies,
            applications=applications,
            questions=questions,
            mnemonics=mnemonics,
        )

        # ── 8. Assemble EnhancedSlide ─────────────────────────────────────────
        enhanced = EnhancedSlide(
            slide_id=intel.slide_id,
            slide_title=topic,
            improved_explanation=revision.get("improved_explanation", ""),
            simplified_explanation=revision.get("simplified_explanation", ""),
            examples=examples if isinstance(examples, list) else [],
            analogies=analogies if isinstance(analogies, list) else [],
            real_world_applications=applications if isinstance(applications, list) else [],
            common_mistakes=revision.get("common_mistakes", []),
            interview_questions=questions.get("interview_questions", []),
            revision_points=revision.get("revision_points", []),
            mnemonic=mnemonics.get("mnemonic", ""),
            discussion_questions=questions.get("discussion_questions", []),
            learning_tips=mnemonics.get("learning_tips", []),
            confidence=confidence,
        )

        logger.info(enhanced.summary_line())
        return enhanced

    # ─────────────────────────────────────────────────────────────────────────
    # Private Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _build_context(
        self,
        plan: TransformationPlan,
        intel: SlideIntelligence,
    ) -> str:
        """
        Distil the most pedagogically useful fields from both inputs into a
        compact context string that is injected into every generator prompt.
        """
        parts = []

        # From SlideIntelligence
        if intel.main_topic:
            parts.append(f"Main topic: {intel.main_topic}")
        if intel.learning_objective:
            parts.append(f"Learning objective: {intel.learning_objective}")
        if intel.key_concepts:
            parts.append("Key concepts: " + ", ".join(intel.key_concepts[:6]))
        if intel.definitions:
            defs = "; ".join(
                f"{k}: {v}" for k, v in list(intel.definitions.items())[:3]
            )
            parts.append(f"Definitions: {defs}")
        if intel.steps:
            parts.append("Steps: " + " → ".join(intel.steps[:6]))
        if intel.formulas:
            parts.append("Formulas: " + " | ".join(intel.formulas[:3]))
        if intel.numbers_and_statistics:
            parts.append("Key stats: " + ", ".join(intel.numbers_and_statistics[:4]))
        if intel.important_facts:
            facts = " ".join(intel.important_facts[:3])
            parts.append(f"Important facts: {facts}")
        if intel.processes:
            parts.append("Processes: " + "; ".join(intel.processes[:3]))
        if intel.advantages:
            parts.append("Advantages: " + "; ".join(intel.advantages[:3]))
        if intel.disadvantages:
            parts.append("Disadvantages: " + "; ".join(intel.disadvantages[:2]))
        if intel.complexity_level:
            parts.append(f"Complexity level: {intel.complexity_level.value}")
        if intel.presentation_intents:
            intents = ", ".join(i.value for i in intel.presentation_intents[:3])
            parts.append(f"Content type: {intents}")

        # From TransformationPlan
        if plan.remaining_text:
            # Include first few remaining text items as additional context
            remaining = " ".join(plan.remaining_text[:4])
            parts.append(f"Slide content: {remaining[:400]}")
        if plan.speaker_notes:
            parts.append(f"Speaker notes excerpt: {plan.speaker_notes[:300]}")

        return "\n".join(parts)

    def _call(self, fn, topic: str, context: str, llm_kwargs: dict, default: Any) -> Any:
        """
        Safe wrapper to call a generator function and fall back to `default` on failure.
        """
        try:
            return fn(topic=topic, context=context, llm=self._llm, **llm_kwargs)
        except Exception as e:
            logger.warning(
                "Enhancement generator %s failed for '%s': %s",
                fn.__module__,
                topic,
                e,
            )
            return default

    def _sleep(self) -> None:
        if self._delay > 0:
            time.sleep(self._delay)

    @staticmethod
    def _compute_confidence(
        plan: TransformationPlan,
        intel: SlideIntelligence,
        revision: dict,
        examples: list,
        analogies: list,
        applications: list,
        questions: dict,
        mnemonics: dict,
    ) -> float:
        """
        Compute a composite confidence score (0.0–1.0) based on:
        - Source richness (from TransformationPlan and SlideIntelligence)
        - How many generator outputs are non-empty
        """
        # Source richness component (up to 0.4)
        richness = 0.0
        richness += 0.05 if intel.key_concepts else 0.0
        richness += 0.05 if intel.definitions else 0.0
        richness += 0.05 if intel.steps else 0.0
        richness += 0.05 if intel.formulas else 0.0
        richness += 0.05 if intel.numbers_and_statistics else 0.0
        richness += 0.05 if intel.important_facts else 0.0
        richness += 0.05 if plan.remaining_text else 0.0
        richness += 0.05 if plan.speaker_notes else 0.0
        richness = min(richness, 0.4)

        # Generator success component (up to 0.6)
        gen_checks = [
            bool(revision.get("improved_explanation")),
            bool(revision.get("simplified_explanation")),
            bool(revision.get("revision_points")),
            bool(revision.get("common_mistakes")),
            bool(examples),
            bool(analogies),
            bool(applications),
            bool(questions.get("interview_questions")),
            bool(questions.get("discussion_questions")),
            bool(mnemonics.get("mnemonic")),
            bool(mnemonics.get("learning_tips")),
        ]
        gen_score = sum(gen_checks) / len(gen_checks) * 0.6

        # Also factor in the plan's own confidence (up to a 10% bonus)
        plan_bonus = min(plan.confidence * 0.1, 0.1)

        return round(min(richness + gen_score + plan_bonus, 1.0), 3)
