"""
Learnova Intelligence Layer — Visual Opportunity Detector
===========================================================
Analyzes extracted slide concepts, structure, and presentation intents to identify
opportunities where text can later be transformed into rich visual components.

Output visual opportunity types:
  - Flowchart, Timeline, Comparison Table, SmartArt, Decision Tree, Pyramid,
    Cycle Diagram, Process Diagram, Organization Chart, Matrix, Roadmap, Checklist,
    Icon Grid, Infographic, Image with Caption, KPI Cards

For each detected opportunity, provides a confidence score and clear rationale WHY it fits.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from parsers.schema import SlidePageEntity
from intelligence.schema import (
    PresentationIntent,
    VisualOpportunity,
    VisualOpportunityType,
)


def detect_visual_opportunities(
    slide: SlidePageEntity,
    concepts: Dict[str, Any],
    intents: List[PresentationIntent],
) -> List[VisualOpportunity]:
    """
    Detects opportunities to convert dense text/data into structured visual elements.

    Args:
        slide: SlidePageEntity
        concepts: Extracted concepts dictionary
        intents: List of detected PresentationIntent values

    Returns:
        List of VisualOpportunity objects ordered by confidence/priority.
    """
    opportunities: List[VisualOpportunity] = []

    steps = concepts.get("steps", [])
    processes = concepts.get("processes", [])
    chronology = concepts.get("chronology", [])
    comparisons = concepts.get("comparisons", [])
    key_concepts = concepts.get("key_concepts", [])
    supporting_concepts = concepts.get("supporting_concepts", [])
    stats = concepts.get("numbers_and_statistics", [])
    advantages = concepts.get("advantages", [])
    disadvantages = concepts.get("disadvantages", [])
    lists = concepts.get("lists", [])
    relationships = concepts.get("relationships", [])

    all_text = " ".join([tb.text for tb in slide.text_blocks if tb.text]).lower()

    # 1. Flowchart
    if (len(steps) >= 3 or len(processes) >= 1) and PresentationIntent.WORKFLOW in intents:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.FLOWCHART,
                rationale=f"Found {len(steps)} sequential steps/processes; a flowchart clearly visualizes execution flow.",
                confidence=0.9,
                source_fields=["steps", "processes"],
            )
        )

    # 2. Timeline
    if len(chronology) >= 2 or PresentationIntent.TIMELINE in intents:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.TIMELINE,
                rationale=f"Detected {len(chronology)} chronological points; a timeline organizes temporal progression visually.",
                confidence=0.88,
                source_fields=["chronology"],
            )
        )

    # 3. Comparison Table
    if comparisons or (advantages and disadvantages) or PresentationIntent.COMPARISON in intents:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.COMPARISON_TABLE,
                rationale="Content involves direct side-by-side comparison or pros/cons analysis.",
                confidence=0.85,
                source_fields=["comparisons", "advantages", "disadvantages"],
            )
        )

    # 4. KPI Cards
    if len(stats) >= 2 or PresentationIntent.STATISTICS in intents:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.KPI_CARDS,
                rationale=f"Extracted {len(stats)} key metrics/statistics; metric callout cards emphasize data impact.",
                confidence=0.85,
                source_fields=["numbers_and_statistics"],
            )
        )

    # 5. Icon Grid / SmartArt
    if 3 <= len(key_concepts) <= 6:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.ICON_GRID,
                rationale=f"Identified {len(key_concepts)} core concept pillars ideal for an icon-backed card grid layout.",
                confidence=0.80,
                source_fields=["key_concepts"],
            )
        )
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.SMART_ART,
                rationale=f"Pillar concepts ({len(key_concepts)}) fit structured SmartArt graphic containers.",
                confidence=0.75,
                source_fields=["key_concepts"],
            )
        )

    # 6. Cycle Diagram
    if PresentationIntent.CYCLE in intents or any(kw in all_text for kw in ["loop", "cycle", "repeat", "circular"]):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.CYCLE_DIAGRAM,
                rationale="Content describes an iterative or continuous cycle mechanism.",
                confidence=0.82,
                source_fields=["processes"],
            )
        )

    # 7. Process Diagram
    if len(steps) >= 2 and VisualOpportunityType.FLOWCHART not in [opp.visual_type for opp in opportunities]:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.PROCESS_DIAGRAM,
                rationale=f"{len(steps)} procedural steps map effectively to a horizontal process block diagram.",
                confidence=0.78,
                source_fields=["steps"],
            )
        )

    # 8. Checklist
    if (len(steps) >= 3 or PresentationIntent.CHECKLIST in intents) and any(kw in all_text for kw in ["task", "check", "verify", "ensure", "action"]):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.CHECKLIST,
                rationale="Content represents actionable guidelines or verification steps suitable for a checklist.",
                confidence=0.75,
                source_fields=["steps"],
            )
        )

    # 9. Pyramid / Hierarchy
    if PresentationIntent.HIERARCHY in intents or any(kw in all_text for kw in ["pyramid", "hierarchy", "tier", "level", "foundation"]):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.PYRAMID,
                rationale="Hierarchical or tiered concepts are best understood through a pyramid model.",
                confidence=0.80,
                source_fields=["key_concepts"],
            )
        )

    # 10. Decision Tree
    if any(kw in all_text for kw in ["if ", "else", "decision", "choice", "branch", "condition"]):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.DECISION_TREE,
                rationale="Conditional logic or decision paths benefit from a branching decision tree.",
                confidence=0.72,
                source_fields=["processes"],
            )
        )

    # 11. Image with Caption
    if slide.visual_assets:
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.IMAGE_WITH_CAPTION,
                rationale="Slide contains raw visual asset; pairing with a structured caption enhances context.",
                confidence=0.90,
                source_fields=["visual_assets"],
            )
        )

    # 12. Matrix / Grid
    if PresentationIntent.TABLE in intents or (len(comparisons) >= 2 and len(key_concepts) >= 4):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.MATRIX,
                rationale="Multi-attribute breakdown maps to a 2x2 matrix or quadrant layout.",
                confidence=0.70,
                source_fields=["comparisons", "key_concepts"],
            )
        )

    # 13. Roadmap
    if PresentationIntent.TIMELINE in intents and any(kw in all_text for kw in ["phase", "release", "q1", "q2", "q3", "q4", "roadmap", "milestone"]):
        opportunities.append(
            VisualOpportunity(
                visual_type=VisualOpportunityType.ROADMAP,
                rationale="Strategic planning milestones are ideally rendered as a milestone roadmap.",
                confidence=0.82,
                source_fields=["chronology"],
            )
        )

    # Sort opportunities by confidence descending
    opportunities.sort(key=lambda x: x.confidence, reverse=True)

    # Set priority rank
    for idx, opp in enumerate(opportunities):
        opp.priority_rank = idx + 1

    return opportunities
