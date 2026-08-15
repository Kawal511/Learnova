"""
Learnova Visual Specification Engine — Icon Grid & Checklist Builder
=====================================================================
Deterministic builder for Icon Grid and Checklist visual specifications.

Icon Grid cross-enriches item explanations with EnhancedSlide.examples
(the Day 8 ↔ Day 7 cross-module link).

Checklist is derived from steps with actionability detection.

Output: IconSpec (used for both Icon Grid and Checklist)

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from learnova.intelligence.schema import SlideIntelligence
from learnova.enhancement.schema import EnhancedSlide
from learnova.visual_specs.schema import IconItem, IconSpec

# Deterministic keyword → icon name map (Feather Icons / Lucide naming)
_ICON_MAP: Dict[str, str] = {
    # Technology
    "ai":           "cpu",
    "artificial":   "cpu",
    "algorithm":    "cpu",
    "machine":      "cpu",
    "neural":       "cpu",
    "model":        "cpu",
    # Education
    "learn":        "book-open",
    "student":      "book-open",
    "course":       "book-open",
    "education":    "book-open",
    "teach":        "book-open",
    "knowledge":    "book-open",
    # Data
    "data":         "database",
    "database":     "database",
    "storage":      "database",
    # Analytics
    "stat":         "bar-chart-2",
    "metric":       "bar-chart-2",
    "analytic":     "bar-chart-2",
    "report":       "bar-chart-2",
    "graph":        "bar-chart-2",
    "chart":        "bar-chart-2",
    # Process
    "process":      "activity",
    "flow":         "activity",
    "pipeline":     "activity",
    "workflow":     "activity",
    # Performance
    "speed":        "zap",
    "perform":      "zap",
    "fast":         "zap",
    "efficient":    "zap",
    "optim":        "zap",
    # People
    "team":         "users",
    "collaborat":   "users",
    "social":       "users",
    "communic":     "users",
    "network":      "users",
    # Security
    "secure":       "shield",
    "protect":      "shield",
    "safety":       "shield",
    "auth":         "shield",
    "trust":        "shield",
    # Infrastructure
    "cloud":        "cloud",
    "server":       "server",
    "deploy":       "server",
    # Finance
    "cost":         "dollar-sign",
    "price":        "dollar-sign",
    "money":        "dollar-sign",
    "budget":       "dollar-sign",
    "revenue":      "dollar-sign",
    # Science
    "science":      "flask",
    "biology":      "flask",
    "chemistry":    "flask",
    "experiment":   "flask",
    "lab":          "flask",
    # Time
    "time":         "clock",
    "schedule":     "clock",
    "deadline":     "clock",
    # Check / Task
    "verify":       "check-square",
    "task":         "check-square",
    "action":       "check-square",
    "ensure":       "check-square",
    "checklist":    "check-square",
    # Default
}

_DEFAULT_ICON = "circle"

# Placement grid — cycles through positions for multi-item grids
_PLACEMENT_GRID = [
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
]


def build_icon_grid_spec(
    intel: SlideIntelligence,
    enhanced: Optional[EnhancedSlide] = None,
) -> IconSpec:
    """
    Build an Icon Grid specification from SlideIntelligence.

    Item explanations are enriched with EnhancedSlide.examples when available
    (the key cross-module link introduced in Day 8).

    Args:
        intel: SlideIntelligence object.
        enhanced: Optional EnhancedSlide for example-based explanation enrichment.

    Returns:
        IconSpec with a list of IconItem objects.
    """
    concepts = intel.key_concepts if intel.key_concepts else intel.supporting_concepts[:6]
    if not concepts:
        concepts = [intel.main_topic or "Core Concept"]

    example_lookup = _build_example_lookup(enhanced)

    items: List[IconItem] = []
    for i, concept in enumerate(concepts[:9]):
        icon_name = _resolve_icon(concept)
        placement = _PLACEMENT_GRID[i % len(_PLACEMENT_GRID)]
        explanation = _build_explanation(concept, intel, example_lookup)

        items.append(IconItem(
            concept=concept[:50],
            icon_name=icon_name,
            placement_hint=placement,
            explanation=explanation[:120],
        ))

    return IconSpec(items=items)


def build_checklist_spec(intel: SlideIntelligence) -> IconSpec:
    """
    Build a Checklist specification from SlideIntelligence.steps.

    Each step becomes a checklist item with a check-square icon.

    Args:
        intel: SlideIntelligence object.

    Returns:
        IconSpec with check-square icons for each step.
    """
    steps = intel.steps or intel.processes
    if not steps:
        steps = [f"Task {i + 1}" for i in range(3)]

    items: List[IconItem] = []
    for i, step in enumerate(steps[:12]):
        is_action = any(
            kw in step.lower()
            for kw in ["ensure", "verify", "check", "validate", "confirm", "complete", "review"]
        )
        items.append(IconItem(
            concept=step[:60],
            icon_name="check-square" if is_action else "circle",
            placement_hint=f"row-{i + 1}",
            explanation=f"Action item {i + 1}: {step[:60]}",
        ))

    return IconSpec(items=items)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_icon(concept: str) -> str:
    """Map a concept string to an icon name via keyword lookup."""
    lower = concept.lower()
    for keyword, icon in _ICON_MAP.items():
        if keyword in lower:
            return icon
    return _DEFAULT_ICON


def _build_example_lookup(enhanced: Optional[EnhancedSlide]) -> Dict[str, str]:
    """Build a keyword → example map for explanation enrichment."""
    if not enhanced or not enhanced.examples:
        return {}
    lookup: Dict[str, str] = {}
    for example in enhanced.examples:
        words = example.lower().split()
        for word in words:
            if len(word) > 5:
                lookup[word] = example[:80]
    return lookup


def _build_explanation(
    concept: str,
    intel: SlideIntelligence,
    example_lookup: Dict[str, str],
) -> str:
    """Build an item explanation, enriched with examples if available."""
    # Try definition first
    defn = intel.definitions.get(concept, "")
    if defn:
        return defn[:100]

    # Try matching with examples from EnhancedSlide
    lower = concept.lower()
    for keyword, example in example_lookup.items():
        if keyword in lower:
            return f"Example: {example}"[:100]

    return f"Key educational concept: {concept.lower()}."[:100]
