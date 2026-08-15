"""
Learnova Visual Specification Engine — AI Image Prompt Builder
==============================================================
Deterministic builder for AI Image prompt specifications.
Cross-enriched with EnhancedSlide.analogies for richer subject context.

Output: AIImageSpec

No LLMs. No rendering. No actual image generation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from learnova.intelligence.schema import ComplexityLevel, SlideIntelligence
from learnova.enhancement.schema import EnhancedSlide
from learnova.visual_specs.schema import AIImageSpec

# Style library — keyed by complexity level
_STYLE_BY_COMPLEXITY: Dict[str, str] = {
    ComplexityLevel.INTRODUCTORY.value: (
        "Flat design illustration, minimal shapes, bold primary colours, "
        "friendly and approachable visual style"
    ),
    ComplexityLevel.INTERMEDIATE.value: (
        "Modern minimalist educational infographic, clean line art, "
        "vibrant gradient accents (teal and deep blue)"
    ),
    ComplexityLevel.ADVANCED.value: (
        "Technical schematic illustration, precise vector art, "
        "dark-mode background with neon accent highlights"
    ),
    ComplexityLevel.EXPERT.value: (
        "High-detail scientific diagram style, isometric projection, "
        "monochromatic palette with strategic colour accent"
    ),
}

# Color palette by complexity
_PALETTE_BY_COMPLEXITY: Dict[str, str] = {
    ComplexityLevel.INTRODUCTORY.value: "#4A90D9, #F5A623, #7ED321, white background",
    ComplexityLevel.INTERMEDIATE.value: "#00BCD4, #3F51B5, #E91E63, white background",
    ComplexityLevel.ADVANCED.value:     "#1DE9B6, #651FFF, #FF6D00, dark #121212 background",
    ComplexityLevel.EXPERT.value:       "#00E5FF, #B388FF, #FFFFFF, dark #0D1117 background",
}

_NEGATIVE_PROMPT = (
    "photorealistic photo, text, words, labels, captions, watermark, "
    "noisy background, cluttered composition, dark shadowy mood, "
    "human faces, hands, stock photo clichés"
)


def build_image_prompt_spec(
    intel: SlideIntelligence,
    enhanced: Optional[EnhancedSlide] = None,
) -> AIImageSpec:
    """
    Build an AI Image prompt specification.

    Subject is enriched with EnhancedSlide.analogies (if available) to produce
    a more evocative and contextually grounded image description.

    Args:
        intel: SlideIntelligence object.
        enhanced: Optional EnhancedSlide for analogy-based subject enrichment.

    Returns:
        AIImageSpec with subject, style, composition, camera_angle,
        educational_objective, color_palette, negative_prompt.
    """
    subject = _build_subject(intel, enhanced)
    complexity_key = intel.complexity_level.value
    style      = _STYLE_BY_COMPLEXITY.get(complexity_key, _STYLE_BY_COMPLEXITY[ComplexityLevel.INTERMEDIATE.value])
    palette    = _PALETTE_BY_COMPLEXITY.get(complexity_key, _PALETTE_BY_COMPLEXITY[ComplexityLevel.INTERMEDIATE.value])
    composition = _build_composition(intel)
    camera_angle = _select_camera_angle(intel)
    educational_objective = _build_educational_objective(intel)

    return AIImageSpec(
        subject=subject,
        style=style,
        composition=composition,
        camera_angle=camera_angle,
        educational_objective=educational_objective,
        color_palette=palette,
        negative_prompt=_NEGATIVE_PROMPT,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_subject(
    intel: SlideIntelligence,
    enhanced: Optional[EnhancedSlide],
) -> str:
    """Build the image subject description, enriched with analogies if available."""
    topic = intel.main_topic or intel.slide_title
    concepts = ", ".join(intel.key_concepts[:3])

    subject = f"An educational visual representation of {topic}."
    if concepts:
        subject += f" Illustrating the core concepts: {concepts}."

    # Cross-enrich with analogy if available (Day 8 ↔ Day 7 link)
    if enhanced and enhanced.analogies:
        best_analogy = enhanced.analogies[0][:120]
        subject += f" Visual metaphor inspired by: {best_analogy}."

    return subject[:300]


def _build_composition(intel: SlideIntelligence) -> str:
    """Select composition based on number of concepts."""
    n = len(intel.key_concepts)
    if n <= 1:
        return "Centred single focal point, clean white studio background"
    if n <= 3:
        return "Triptych layout, three equal columns, minimal dividers"
    return "Isometric grid composition, multiple concept zones, clear visual hierarchy"


def _select_camera_angle(intel: SlideIntelligence) -> str:
    """Select camera angle based on presentation intent."""
    from learnova.intelligence.schema import PresentationIntent
    intents = intel.presentation_intents
    if PresentationIntent.PROCESS in intents or PresentationIntent.WORKFLOW in intents:
        return "Top-down birds-eye view showing flow direction left to right"
    if PresentationIntent.HIERARCHY in intents:
        return "Slightly elevated angle showing hierarchical depth"
    if PresentationIntent.STATISTICS in intents:
        return "Straight-on frontal view for data clarity"
    return "Eye-level straight-on perspective"


def _build_educational_objective(intel: SlideIntelligence) -> str:
    """Build a concise educational objective sentence for the image."""
    obj = intel.learning_objective
    topic = intel.main_topic or intel.slide_title
    if obj:
        return f"To visually reinforce: {obj}"[:120]
    return f"To help students build a mental model of {topic}."[:120]
