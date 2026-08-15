"""
Learnova Visual Specification Engine — Mind Map Builder
========================================================
Deterministic builder for Mind Map visual specifications.
New in Day 8 — not available in intelligence/transformation.py.

Derives the mind map structure from SlideIntelligence.information_hierarchy:
  - Level 1 (topic)       → central_topic
  - Level 2 (key)         → branches
  - Level 3 (supporting)  → branch children
  - Level 4 (details)     → leaf nodes (optional)

Output: MindMapSpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

from typing import List

from learnova.intelligence.schema import SlideIntelligence
from learnova.visual_specs.schema import MindMapBranch, MindMapSpec


def build_mindmap_spec(intel: SlideIntelligence) -> MindMapSpec:
    """
    Build a Mind Map specification from SlideIntelligence.

    Uses the information_hierarchy to populate the central topic,
    first-level branches, and child nodes.

    Args:
        intel: SlideIntelligence object.

    Returns:
        MindMapSpec with central_topic, branches, and depth.
    """
    hierarchy = intel.information_hierarchy

    # Central topic — Level 1
    central_topic = (
        hierarchy.get("level_1_topic")
        or intel.main_topic
        or intel.slide_title
        or "Main Topic"
    )

    # Level 2 → branches
    level_2: List[str] = hierarchy.get("level_2_key_concepts", intel.key_concepts[:6])
    # Level 3 → children of branches
    level_3: List[str] = hierarchy.get("level_3_supporting", intel.supporting_concepts[:8])
    # Level 4 → leaf details (facts, examples, stats)
    level_4: List[str] = hierarchy.get("level_4_details", [])

    # Assign children to branches
    branches: List[MindMapBranch] = []
    for i, branch_name in enumerate(level_2[:8]):
        # Distribute level_3 items among branches
        children = _assign_children(level_3, branch_index=i, total_branches=len(level_2))

        # Optionally append a level_4 leaf to the first branch
        if i == 0 and level_4:
            children.extend(_safe_slice(level_4, 0, 2))

        branches.append(MindMapBranch(
            name=branch_name[:50],
            children=[c[:50] for c in children[:4]],  # max 4 children per branch
        ))

    # If no branches, fall back to key_concepts
    if not branches:
        for concept in intel.key_concepts[:6]:
            defn = intel.definitions.get(concept, "")
            branches.append(MindMapBranch(
                name=concept[:50],
                children=[defn[:50]] if defn else [],
            ))

    # Determine depth
    has_children = any(bool(b.children) for b in branches)
    depth = 2 if has_children else 1

    return MindMapSpec(
        central_topic=central_topic[:80],
        branches=branches,
        depth=depth,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _assign_children(
    items: List[str],
    branch_index: int,
    total_branches: int,
) -> List[str]:
    """
    Distribute level_3 items round-robin across branches.
    Returns the items belonging to branch at `branch_index`.
    """
    if not items or total_branches == 0:
        return []
    return [
        items[j]
        for j in range(branch_index, len(items), total_branches)
    ][:3]


def _safe_slice(lst: List[str], start: int, end: int) -> List[str]:
    if not lst:
        return []
    return lst[start:end]
