"""
Learnova Visual Specification Engine — SmartArt, Hierarchy & Cycle Builder
===========================================================================
Deterministic builder for:
  - SmartArt (Relationship, Process, Chevron, Pyramid)
  - Hierarchy (from information_hierarchy)
  - Cycle Diagram (closed-loop processes)

Output: SmartArtSpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from learnova.intelligence.schema import PresentationIntent, SlideIntelligence
from learnova.visual_specs.schema import SmartArtElement, SmartArtSpec

# SmartArt type selection signals
_SMARTART_SIGNALS: Dict[str, List[str]] = {
    "Hierarchy":     ["hierarchy", "level", "tree", "parent", "child", "subordinate", "tier"],
    "Cycle":         ["cycle", "loop", "repeat", "iterative", "continuous", "recurring"],
    "Process":       ["process", "pipeline", "workflow", "sequence", "stage", "phase", "step"],
    "Pyramid":       ["pyramid", "priority", "level", "foundation", "tier", "rank", "most important"],
    "Chevron":       ["arrow", "flow", "direction", "forward", "progression", "advance"],
    "Relationship":  ["relationship", "connect", "link", "depend", "interact", "between", "among"],
}

_INTENT_TO_SMARTART = {
    PresentationIntent.HIERARCHY:  "Hierarchy",
    PresentationIntent.CYCLE:      "Cycle",
    PresentationIntent.PROCESS:    "Process",
    PresentationIntent.WORKFLOW:   "Process",
    PresentationIntent.TIMELINE:   "Chevron",
    PresentationIntent.COMPARISON: "Relationship",
}


def build_smartart_spec(
    intel: SlideIntelligence,
    forced_type: Optional[str] = None,
) -> SmartArtSpec:
    """
    Build a SmartArt specification.

    Type selection priority:
    1. forced_type (used for Pyramid override)
    2. Infer from PresentationIntent
    3. Infer from keyword signals in content
    4. Default: Relationship

    Args:
        intel: SlideIntelligence object.
        forced_type: Override the SmartArt type (e.g. "Pyramid").

    Returns:
        SmartArtSpec.
    """
    smartart_type = forced_type or _select_smartart_type(intel)
    elements      = _build_elements(intel, smartart_type)
    depth         = _compute_depth(smartart_type, elements)
    alignment     = "horizontal" if smartart_type in ("Process", "Chevron") else "vertical"

    structure = {
        "layout":     smartart_type,
        "depth":      depth,
        "alignment":  alignment,
        "node_count": len(elements),
    }

    return SmartArtSpec(
        smartart_type=smartart_type,
        elements=elements,
        depth=depth,
        alignment=alignment,
        structure=structure,
    )


def build_hierarchy_spec(intel: SlideIntelligence) -> SmartArtSpec:
    """Build a Hierarchy SmartArt from information_hierarchy."""
    hierarchy = intel.information_hierarchy
    root     = hierarchy.get("level_1_topic",   intel.main_topic or intel.slide_title)
    level_2  = hierarchy.get("level_2_key_concepts", intel.key_concepts[:4])
    level_3  = hierarchy.get("level_3_supporting",   intel.supporting_concepts[:4])

    elements: List[SmartArtElement] = [
        SmartArtElement(label=root, level=0, children=list(level_2[:4]))
    ]
    for concept in level_2[:4]:
        children = [s for s in level_3 if s][:2]
        elements.append(SmartArtElement(label=concept, level=1, children=children))

    structure = {
        "layout":    "Hierarchy",
        "depth":     2 if level_3 else 1,
        "alignment": "vertical",
        "node_count": len(elements),
    }

    return SmartArtSpec(
        smartart_type="Hierarchy",
        elements=elements,
        depth=2 if level_3 else 1,
        alignment="vertical",
        structure=structure,
    )


def build_cycle_spec(intel: SlideIntelligence) -> SmartArtSpec:
    """Build a Cycle Diagram SmartArt from processes or steps."""
    items = intel.processes if intel.processes else intel.steps
    if not items:
        items = [intel.main_topic or "Phase 1", "Phase 2", "Phase 3"]

    elements = [
        SmartArtElement(label=item[:40], level=0)
        for item in items[:8]
    ]

    structure = {
        "layout":         "Cycle",
        "depth":          1,
        "alignment":      "radial",
        "flow_direction": "clockwise",
        "is_closed":      True,
        "node_count":     len(elements),
    }

    return SmartArtSpec(
        smartart_type="Cycle",
        elements=elements,
        depth=1,
        alignment="radial",
        structure=structure,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _select_smartart_type(intel: SlideIntelligence) -> str:
    """Infer SmartArt type from PresentationIntent, then keyword signals."""
    # 1. Intent-based selection
    for intent in intel.presentation_intents:
        if intent in _INTENT_TO_SMARTART:
            return _INTENT_TO_SMARTART[intent]

    # 2. Keyword-based fallback
    combined = " ".join([
        intel.main_topic,
        intel.learning_objective,
        " ".join(intel.key_concepts),
        " ".join(intel.processes),
    ]).lower()

    scores = {stype: 0 for stype in _SMARTART_SIGNALS}
    for stype, signals in _SMARTART_SIGNALS.items():
        for sig in signals:
            if sig in combined:
                scores[stype] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Relationship"


def _build_elements(intel: SlideIntelligence, smartart_type: str) -> List[SmartArtElement]:
    """Select and build SmartArt elements from appropriate source fields."""
    if smartart_type in ("Hierarchy",):
        hierarchy = intel.information_hierarchy
        l2 = hierarchy.get("level_2_key_concepts", intel.key_concepts[:4])
        return [
            SmartArtElement(label=label[:40], level=0)
            for label in ([intel.main_topic] + list(l2))[:6]
        ]
    elif smartart_type in ("Cycle",):
        items = intel.processes or intel.steps or intel.key_concepts
    elif smartart_type in ("Process", "Chevron"):
        items = intel.steps or intel.processes or intel.key_concepts
    else:
        items = intel.key_concepts or intel.supporting_concepts

    return [
        SmartArtElement(label=item[:40], level=0)
        for item in (items or ["Concept A", "Concept B", "Concept C"])[:8]
    ]


def _compute_depth(smartart_type: str, elements: List[SmartArtElement]) -> int:
    if smartart_type == "Hierarchy":
        return 2
    if len(elements) > 5:
        return 2
    return 1
