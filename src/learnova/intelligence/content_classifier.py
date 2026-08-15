"""
Learnova Intelligence Layer — Content Classifier
=================================================
Classifies every SlidePageEntity into one or more PresentationIntent values
using pure heuristic signals from the extracted concept dictionary.

No LLM calls. No external API. Fully deterministic.

Classification outputs:
  - presentation_intents: ordered list of matched intents (strongest first)
  - primary_intent: single most-confident intent
  - intent_scores: full scoring breakdown for debugging / downstream tuning
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from learnova.parsers.schema import SlidePageEntity
from learnova.intelligence.schema import IntentScore, PresentationIntent


# ─────────────────────────────────────────────────────────────────────────────
# Intent → signal keyword tables
# ─────────────────────────────────────────────────────────────────────────────

_INTENT_KEYWORDS: Dict[PresentationIntent, List[str]] = {
    PresentationIntent.DEFINITION: [
        "is defined as", "refers to", "known as", "means", "definition",
        "defined", "glossary", "terminology", "what is", "is a type of",
    ],
    PresentationIntent.PROCESS: [
        "process", "mechanism", "procedure", "how it works",
        "operation", "method", "technique", "approach", "protocol",
    ],
    PresentationIntent.WORKFLOW: [
        "workflow", "pipeline", "flow", "sequence of steps",
        "step by step", "systematic", "stage", "phase",
    ],
    PresentationIntent.TIMELINE: [
        "timeline", "history", "chronology", "evolution", "milestones",
        "year", "century", "decade", "era", "period", "date",
    ],
    PresentationIntent.COMPARISON: [
        "vs", "versus", "compared to", "comparison", "difference",
        "similarities", "unlike", "whereas", "contrast", "pros and cons",
    ],
    PresentationIntent.TABLE: [
        "table", "matrix", "grid", "spreadsheet", "rows", "columns",
    ],
    PresentationIntent.STATISTICS: [
        "statistics", "data", "percentage", "survey", "study found",
        "research shows", "according to", "percent", "rate", "ratio",
        "average", "median", "mean", "growth rate",
    ],
    PresentationIntent.HIERARCHY: [
        "hierarchy", "level", "tier", "rank", "order", "classification",
        "taxonomy", "category", "sub-category", "breakdown",
    ],
    PresentationIntent.CYCLE: [
        "cycle", "loop", "iteration", "recurring", "repeat", "circular",
        "continuous", "ongoing", "round", "rotation",
    ],
    PresentationIntent.PROBLEM: [
        "problem", "challenge", "issue", "limitation", "obstacle",
        "barrier", "bottleneck", "pain point", "difficulty", "failure",
    ],
    PresentationIntent.SOLUTION: [
        "solution", "resolve", "address", "mitigate", "fix",
        "answer", "approach", "remedy", "overcome", "solve",
    ],
    PresentationIntent.ARCHITECTURE: [
        "architecture", "component", "layer", "module", "system design",
        "infrastructure", "framework", "stack", "platform", "design pattern",
    ],
    PresentationIntent.FORMULA: [
        "formula", "equation", "expression", "calculation", "theorem",
        "law of", "mathematical", "derivation", "proof",
    ],
    PresentationIntent.CASE_STUDY: [
        "case study", "real world", "scenario", "example company",
        "case of", "study of", "analysis of", "in practice",
    ],
    PresentationIntent.SUMMARY: [
        "summary", "in summary", "to summarize", "recap", "overview",
        "key takeaways", "in brief", "to conclude", "at a glance",
    ],
    PresentationIntent.CONCLUSION: [
        "conclusion", "in conclusion", "therefore", "finally",
        "to sum up", "overall", "ultimately", "in the end",
    ],
    PresentationIntent.CHECKLIST: [
        "checklist", "to-do", "action items", "tasks", "steps to follow",
        "requirements", "criteria", "check", "verify", "ensure",
    ],
    PresentationIntent.FAQ: [
        "faq", "frequently asked", "common questions",
        "q&a", "questions and answers", "q:", "a:",
    ],
}

# Minimum score threshold to include an intent in the output list
_CONFIDENCE_THRESHOLD = 0.2

# Maximum number of intents to report (ordered by score)
_MAX_INTENTS = 4


# ─────────────────────────────────────────────────────────────────────────────
# Scoring helpers
# ─────────────────────────────────────────────────────────────────────────────

def _keyword_score(text_lower: str, keywords: List[str]) -> tuple[float, List[str]]:
    """
    Return (score, fired_signals) where score is a normalised match ratio.
    Each keyword hit contributes equally; score is capped at 1.0.
    """
    fired: List[str] = []
    for kw in keywords:
        if kw in text_lower:
            fired.append(kw)
    # Score: each unique keyword hit adds proportional weight
    score = min(1.0, len(fired) / max(1, len(keywords) * 0.3))
    return score, fired


# ─────────────────────────────────────────────────────────────────────────────
# Structural bonus signals
# ─────────────────────────────────────────────────────────────────────────────

def _structural_bonuses(
    slide: SlidePageEntity,
    concepts: Dict[str, Any],
    intent: PresentationIntent,
) -> tuple[float, List[str]]:
    """
    Compute extra score points from structural slide features
    (table count, equation count, bullet depth, visual assets, etc.)
    Returns (bonus_score, fired_signals).
    """
    bonus   = 0.0
    signals: List[str] = []

    if intent == PresentationIntent.TABLE:
        if slide.tables:
            bonus += 0.8
            signals.append(f"{len(slide.tables)} table(s) detected")

    elif intent == PresentationIntent.FORMULA:
        if slide.equations:
            bonus += 0.9
            signals.append(f"{len(slide.equations)} equation(s) detected")

    elif intent == PresentationIntent.WORKFLOW:
        steps = concepts.get("steps", [])
        if len(steps) >= 3:
            bonus += 0.5
            signals.append(f"{len(steps)} ordered steps")
        if slide.diagrams:
            bonus += 0.3
            signals.append("diagram present")

    elif intent == PresentationIntent.TIMELINE:
        chrono = concepts.get("chronology", [])
        if len(chrono) >= 2:
            bonus += 0.6
            signals.append(f"{len(chrono)} chronological items")

    elif intent == PresentationIntent.COMPARISON:
        comps = concepts.get("comparisons", [])
        if comps:
            bonus += 0.6
            signals.append(f"{len(comps)} comparison(s) detected")

    elif intent == PresentationIntent.DEFINITION:
        defs = concepts.get("definitions", {})
        if defs:
            bonus += 0.6
            signals.append(f"{len(defs)} definition(s) detected")

    elif intent == PresentationIntent.STATISTICS:
        stats = concepts.get("numbers_and_statistics", [])
        if len(stats) >= 2:
            bonus += 0.5
            signals.append(f"{len(stats)} numeric expressions")

    elif intent == PresentationIntent.PROCESS:
        procs = concepts.get("processes", [])
        if procs:
            bonus += 0.5
            signals.append(f"{len(procs)} process description(s)")

    elif intent == PresentationIntent.CHECKLIST:
        lists = concepts.get("lists", [])
        steps = concepts.get("steps", [])
        if lists or len(steps) >= 3:
            bonus += 0.4
            signals.append("list/checklist structure detected")

    elif intent == PresentationIntent.FAQ:
        faqs = concepts.get("faqs", [])
        if faqs:
            bonus += 0.8
            signals.append(f"{len(faqs)} FAQ pair(s) detected")

    elif intent == PresentationIntent.HIERARCHY:
        max_depth = max(
            (tb.bullet_level for tb in slide.text_blocks), default=0
        )
        if max_depth >= 2:
            bonus += 0.4
            signals.append(f"bullet depth {max_depth}")

    elif intent == PresentationIntent.ARCHITECTURE:
        if slide.diagrams:
            bonus += 0.5
            signals.append("diagram/SmartArt element detected")
        if slide.charts:
            bonus += 0.2
            signals.append("chart element detected")

    elif intent == PresentationIntent.CASE_STUDY:
        examples = concepts.get("examples", [])
        if len(examples) >= 2:
            bonus += 0.4
            signals.append(f"{len(examples)} example(s)")

    return min(bonus, 1.0), signals


# ─────────────────────────────────────────────────────────────────────────────
# Public classifier
# ─────────────────────────────────────────────────────────────────────────────

def classify(
    slide: SlidePageEntity,
    concepts: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify a slide into one or more PresentationIntent values.

    Args:
        slide:    The SlidePageEntity from the extraction layer.
        concepts: Output dict from concept_extractor.extract_all().

    Returns:
        {
            "presentation_intents": List[PresentationIntent],  # ordered, strongest first
            "primary_intent":       PresentationIntent,
            "intent_scores":        List[IntentScore],          # full breakdown
        }
    """
    # Aggregate all slide text for keyword scanning
    all_text_parts = [slide.title or ""]
    for tb in slide.text_blocks:
        if tb.text:
            all_text_parts.append(tb.text)
    if slide.speaker_notes:
        all_text_parts.append(slide.speaker_notes)

    all_text = " ".join(all_text_parts)
    all_text_lower = all_text.lower()

    intent_scores: List[IntentScore] = []

    for intent, keywords in _INTENT_KEYWORDS.items():
        kw_score, kw_signals = _keyword_score(all_text_lower, keywords)
        struct_score, struct_signals = _structural_bonuses(slide, concepts, intent)

        # Combined score: keyword hits (60%) + structural evidence (40%)
        combined = kw_score * 0.6 + struct_score * 0.4
        all_signals = kw_signals + struct_signals

        if combined >= _CONFIDENCE_THRESHOLD or all_signals:
            intent_scores.append(
                IntentScore(
                    intent=intent,
                    score=round(combined, 4),
                    signals=all_signals,
                )
            )

    # Sort by score descending
    intent_scores.sort(key=lambda x: x.score, reverse=True)

    # Select top intents above threshold
    selected_intents: List[PresentationIntent] = []
    for is_obj in intent_scores:
        if is_obj.score >= _CONFIDENCE_THRESHOLD and len(selected_intents) < _MAX_INTENTS:
            selected_intents.append(is_obj.intent)

    # Always have at least one intent
    if not selected_intents:
        selected_intents = [PresentationIntent.GENERAL]
        intent_scores.append(
            IntentScore(
                intent=PresentationIntent.GENERAL,
                score=0.1,
                signals=["no strong signals detected — default fallback"],
            )
        )

    primary_intent = selected_intents[0]

    return {
        "presentation_intents": selected_intents,
        "primary_intent":       primary_intent,
        "intent_scores":        intent_scores,
    }
