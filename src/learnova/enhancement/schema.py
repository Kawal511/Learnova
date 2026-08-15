"""
Learnova Enhancement Layer — Schema
=====================================
Defines the EnhancedSlide dataclass — the root output of the
Educational Content Enhancement Engine (Day 7).

EnhancedSlide is the contract between the enhancement engine and any
downstream consumer (app.py, reporting, future UI components).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class EnhancedSlide:
    """
    Root output object produced by the ContentEnhancementEngine.

    Contains pedagogically enriched content derived from a TransformationPlan
    and SlideIntelligence object. All fields are purely content — no layout
    decisions, no rendering hints, no PPT artefacts.

    Confidence is a 0.0–1.0 composite quality score reflecting how many
    generators succeeded and how rich the source content was.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    slide_id: int
    slide_title: str

    # ── Core Explanations ─────────────────────────────────────────────────────
    improved_explanation: str = ""
    """Pedagogically enhanced explanation — richer, clearer, better structured."""

    simplified_explanation: str = ""
    """Plain-language ELI5 version suitable for beginners or quick recall."""

    # ── Concrete Learning Support ─────────────────────────────────────────────
    examples: List[str] = field(default_factory=list)
    """2–3 concrete, real-world examples that illustrate the concept."""

    analogies: List[str] = field(default_factory=list)
    """Comparative analogies that help students build accurate mental models."""

    real_world_applications: List[str] = field(default_factory=list)
    """Practical applications across industries or everyday life."""

    # ── Common Pitfalls ───────────────────────────────────────────────────────
    common_mistakes: List[str] = field(default_factory=list)
    """Frequent student misconceptions, errors, and traps to avoid."""

    # ── Assessment & Review ───────────────────────────────────────────────────
    interview_questions: List[str] = field(default_factory=list)
    """Technical interview, viva, or exam questions targeting this concept."""

    revision_points: List[str] = field(default_factory=list)
    """Concise bullet-point cheat sheet for last-minute review."""

    # ── Memorisation Aid ──────────────────────────────────────────────────────
    mnemonic: str = ""
    """A memorable acronym, phrase, or rhyme encoding the key concepts."""

    # ── Discussion & Tips ─────────────────────────────────────────────────────
    discussion_questions: List[str] = field(default_factory=list)
    """Open-ended Socratic discussion prompts for classroom or group study."""

    learning_tips: List[str] = field(default_factory=list)
    """Study strategies, memory techniques, and recommended learning paths."""

    # ── Quality Metadata ──────────────────────────────────────────────────────
    confidence: float = 0.0
    """
    Composite quality confidence score (0.0–1.0).
    Reflects source content richness and how many generators succeeded.
    """

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary for JSON output, logging, or caching."""
        return {
            "slide_id":               self.slide_id,
            "slide_title":            self.slide_title,
            "improved_explanation":   self.improved_explanation,
            "simplified_explanation": self.simplified_explanation,
            "examples":               self.examples,
            "analogies":              self.analogies,
            "real_world_applications": self.real_world_applications,
            "common_mistakes":        self.common_mistakes,
            "interview_questions":    self.interview_questions,
            "revision_points":        self.revision_points,
            "mnemonic":               self.mnemonic,
            "discussion_questions":   self.discussion_questions,
            "learning_tips":          self.learning_tips,
            "confidence":             round(self.confidence, 3),
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary_line(self) -> str:
        """One-line human-readable summary for logging."""
        filled = sum([
            bool(self.improved_explanation),
            bool(self.simplified_explanation),
            bool(self.examples),
            bool(self.analogies),
            bool(self.real_world_applications),
            bool(self.common_mistakes),
            bool(self.interview_questions),
            bool(self.revision_points),
            bool(self.mnemonic),
            bool(self.discussion_questions),
            bool(self.learning_tips),
        ])
        return (
            f"[EnhancedSlide {self.slide_id}] '{self.slide_title}' | "
            f"Fields filled: {filled}/11 | "
            f"Confidence: {self.confidence:.2f}"
        )
