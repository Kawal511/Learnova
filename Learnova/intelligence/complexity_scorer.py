"""
Learnova Intelligence Layer — Complexity Scorer
================================================
Calculates a 0.0 – 10.0 complexity score and maps it to a ComplexityLevel band
based on semantic, typographic, structural, and syntactic density of a SlidePageEntity.

No LLM calls. Fully heuristic and deterministic formula.
"""

from __future__ import annotations

from typing import Any, Dict

from parsers.schema import SlidePageEntity
from intelligence.schema import ComplexityLevel


def compute_complexity_score(
    slide: SlidePageEntity,
    concepts: Dict[str, Any],
) -> tuple[float, ComplexityLevel]:
    """
    Computes a 0.0 - 10.0 complexity score for a slide.

    Score components:
      - Vocab richness (unique words / total words): weight 2.0
      - Avg sentence length (words per sentence): weight 2.0
      - Technical domain term density: weight 2.5
      - Structural element density (equations, tables, charts, diagrams): weight 2.0
      - Nested depth (bullet level): weight 1.5

    Returns:
        (score, ComplexityLevel)
    """
    signals = concepts.get("complexity_signals", {})

    vocab_richness = signals.get("vocab_richness", 0.5)
    avg_sent_len = signals.get("avg_sent_length", 10.0)
    tech_density = signals.get("technical_density", 0.0)
    element_count = signals.get("element_count", 1)
    max_bullet_depth = signals.get("max_bullet_depth", 0)

    # 1. Vocab component (0 to 2.0)
    # Higher richness (0.7+) indicates dense, academic text
    vocab_sub = min(2.0, vocab_richness * 2.5)

    # 2. Sentence length component (0 to 2.0)
    # 25+ words per sentence maps to max score
    sent_sub = min(2.0, (avg_sent_len / 25.0) * 2.0)

    # 3. Technical term density component (0 to 2.5)
    # 5+ tech terms per 100 words maps to max score
    tech_sub = min(2.5, (tech_density / 5.0) * 2.5)

    # 4. Element complexity component (0 to 2.0)
    # Equations, charts, diagrams, tables add inherent complexity
    special_elements = len(slide.equations) * 1.0 + len(slide.tables) * 0.8 + len(slide.charts) * 0.8 + len(slide.diagrams) * 0.8
    elem_sub = min(2.0, special_elements + (element_count * 0.1))

    # 5. Bullet nesting component (0 to 1.5)
    depth_sub = min(1.5, max_bullet_depth * 0.5)

    # Total score calculation
    raw_total = vocab_sub + sent_sub + tech_sub + elem_sub + depth_sub
    final_score = round(max(0.0, min(10.0, raw_total)), 1)

    # Map to band
    if final_score <= 2.5:
        level = ComplexityLevel.INTRODUCTORY
    elif final_score <= 5.5:
        level = ComplexityLevel.INTERMEDIATE
    elif final_score <= 8.0:
        level = ComplexityLevel.ADVANCED
    else:
        level = ComplexityLevel.EXPERT

    return final_score, level
