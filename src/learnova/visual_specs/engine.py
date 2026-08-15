"""
Learnova Visual Specification Engine — Orchestrator
====================================================
Day 8: Converts educational content into executable visual specifications.

Consumes:
  - TransformationPlan  (from learnova.intelligence.transformation)
  - EnhancedSlide       (from learnova.enhancement.schema)
  - SlideIntelligence   (from learnova.intelligence.schema)

Produces:
  - VisualSpecificationPlan (from learnova.visual_specs.schema)

All logic is purely deterministic — no LLMs, no Vision calls, no rendering.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from learnova.intelligence.schema import SlideIntelligence, VisualOpportunityType
from learnova.intelligence.transformation import TransformationPlan
from learnova.enhancement.schema import EnhancedSlide

from learnova.visual_specs.schema import (
    SelectedVisual,
    VisualSpec,
    VisualSpecificationPlan,
    VisualType,
)
from learnova.visual_specs import (
    flowchart_spec,
    timeline_spec,
    table_spec,
    graph_spec,
    kpi_spec,
    smartart_spec,
    mindmap_spec,
    image_prompt_spec,
    icon_spec,
)
from learnova.logging_config import logger

# Maximum number of primary visuals to include per slide
_MAX_PRIMARY_VISUALS = 5

# Map from VisualOpportunityType value → VisualType constant
_OPP_TO_VISUAL_TYPE: Dict[str, str] = {
    VisualOpportunityType.FLOWCHART.value:        VisualType.FLOWCHART,
    VisualOpportunityType.TIMELINE.value:         VisualType.TIMELINE,
    VisualOpportunityType.ROADMAP.value:          VisualType.TIMELINE,
    VisualOpportunityType.COMPARISON_TABLE.value: VisualType.COMPARISON_TABLE,
    VisualOpportunityType.MATRIX.value:           VisualType.MATRIX,
    VisualOpportunityType.KPI_CARDS.value:        VisualType.KPI_CARDS,
    VisualOpportunityType.SMART_ART.value:        VisualType.SMART_ART,
    VisualOpportunityType.PYRAMID.value:          VisualType.SMART_ART,
    VisualOpportunityType.CYCLE_DIAGRAM.value:    VisualType.CYCLE_DIAGRAM,
    VisualOpportunityType.PROCESS_DIAGRAM.value:  VisualType.PROCESS_DIAGRAM,
    VisualOpportunityType.DECISION_TREE.value:    VisualType.DECISION_TREE,
    VisualOpportunityType.ORG_CHART.value:        VisualType.ORG_CHART,
    VisualOpportunityType.ICON_GRID.value:        VisualType.ICON_GRID,
    VisualOpportunityType.CHECKLIST.value:        VisualType.CHECKLIST,
    VisualOpportunityType.INFOGRAPHIC.value:      VisualType.SMART_ART,
    VisualOpportunityType.IMAGE_WITH_CAPTION.value: VisualType.AI_IMAGE,
}

# Source fields associated with each visual type
_VISUAL_TYPE_SOURCE_FIELDS: Dict[str, List[str]] = {
    VisualType.FLOWCHART:        ["steps", "processes"],
    VisualType.PROCESS_DIAGRAM:  ["steps", "processes"],
    VisualType.TIMELINE:         ["chronology", "steps"],
    VisualType.COMPARISON_TABLE: ["comparisons", "advantages", "disadvantages"],
    VisualType.MATRIX:           ["key_concepts", "supporting_concepts"],
    VisualType.KPI_CARDS:        ["numbers_and_statistics"],
    VisualType.SMART_ART:        ["key_concepts", "processes"],
    VisualType.HIERARCHY:        ["information_hierarchy"],
    VisualType.MIND_MAP:         ["information_hierarchy", "key_concepts"],
    VisualType.DECISION_TREE:    ["steps", "processes"],
    VisualType.CYCLE_DIAGRAM:    ["processes", "steps"],
    VisualType.ORG_CHART:        ["information_hierarchy"],
    VisualType.GRAPH:            ["numbers_and_statistics", "formulas"],
    VisualType.AI_IMAGE:         ["main_topic", "key_concepts"],
    VisualType.ICON_GRID:        ["key_concepts"],
    VisualType.CHECKLIST:        ["steps"],
}


class VisualSpecificationEngine:
    """
    Converts educational content into structured visual specifications.

    Accepts TransformationPlan + EnhancedSlide + SlideIntelligence and
    produces a VisualSpecificationPlan ready for downstream layout engines.

    No LLMs. No rendering. No Mermaid.
    """

    def generate(
        self,
        plan: TransformationPlan,
        enhanced: EnhancedSlide,
        intel: SlideIntelligence,
    ) -> VisualSpecificationPlan:
        """
        Run the full visual specification pipeline for one slide.

        Args:
            plan:     TransformationPlan from SlideTransformationEngine.
            enhanced: EnhancedSlide from ContentEnhancementEngine.
            intel:    SlideIntelligence from SlideIntelligenceEngine.

        Returns:
            VisualSpecificationPlan with selected_visuals and visual_specifications.
        """
        logger.info(
            "VisualSpecificationEngine: generating for slide %s '%s'",
            intel.slide_id, intel.slide_title,
        )

        # Step 1: Select and rank visual types
        selected_visuals = self._select_visuals(plan, enhanced, intel)

        # Step 2: Build a spec for each selected visual type
        visual_specifications: List[VisualSpec] = []
        seen_types: Set[str] = set()

        for sv in selected_visuals:
            vtype = sv.visual_type
            if vtype in seen_types:
                continue
            seen_types.add(vtype)

            spec_dict = self._build_spec(vtype, plan, enhanced, intel)
            if spec_dict is not None:
                visual_specifications.append(VisualSpec(
                    visual_type=vtype,
                    spec=spec_dict,
                ))

        # Step 3: Always append AI Image and Mind Map as supplementary specs
        for supp_type, builder_fn in [
            (VisualType.AI_IMAGE, lambda: image_prompt_spec.build_image_prompt_spec(intel, enhanced).to_dict()),
            (VisualType.MIND_MAP, lambda: mindmap_spec.build_mindmap_spec(intel).to_dict()),
        ]:
            if supp_type not in seen_types:
                try:
                    spec_dict = builder_fn()
                    visual_specifications.append(VisualSpec(visual_type=supp_type, spec=spec_dict))
                    # Add to selected_visuals list as supplementary
                    selected_visuals.append(SelectedVisual(
                        visual_type=supp_type,
                        rationale="Supplementary visual always included for educational richness.",
                        priority_rank=len(selected_visuals),
                        source_fields=_VISUAL_TYPE_SOURCE_FIELDS.get(supp_type, []),
                    ))
                except Exception as e:
                    logger.warning("Supplementary spec %s failed: %s", supp_type, e)

        # Step 4: Compute density and confidence
        density    = self._compute_density(visual_specifications, intel)
        confidence = self._compute_confidence(plan, intel, visual_specifications)

        vsp = VisualSpecificationPlan(
            slide_id=intel.slide_id,
            selected_visuals=selected_visuals,
            visual_specifications=visual_specifications,
            estimated_visual_density=density,
            confidence=confidence,
        )
        logger.info(vsp.summary_line())
        return vsp

    # ─────────────────────────────────────────────────────────────────────────
    # Visual Type Selection
    # ─────────────────────────────────────────────────────────────────────────

    def _select_visuals(
        self,
        plan: TransformationPlan,
        enhanced: EnhancedSlide,
        intel: SlideIntelligence,
    ) -> List[SelectedVisual]:
        """
        Rank and select visual types using a 3-signal priority cascade:
        1. SlideIntelligence.visual_opportunities (ranked by confidence)
        2. TransformationPlan.visual_actions (confirmation signal)
        3. EnhancedSlide supplementary signals (examples → Icon Grid,
           revision_points → Checklist)
        """
        selected: List[SelectedVisual] = []
        seen: Set[str] = set()

        # Signal 1: visual_opportunities from SlideIntelligence
        for opp in sorted(intel.visual_opportunities, key=lambda x: x.confidence, reverse=True):
            if len(selected) >= _MAX_PRIMARY_VISUALS:
                break
            vtype = _OPP_TO_VISUAL_TYPE.get(opp.visual_type.value)
            if not vtype or vtype in seen:
                continue
            seen.add(vtype)
            selected.append(SelectedVisual(
                visual_type=vtype,
                rationale=(
                    f"Detected from SlideIntelligence visual_opportunities "
                    f"(confidence={opp.confidence:.2f}): {opp.rationale}"
                ),
                priority_rank=len(selected),
                source_fields=list(opp.source_fields),
            ))

        # Signal 2: visual_actions from TransformationPlan (confirm or add)
        for action in plan.visual_actions:
            if len(selected) >= _MAX_PRIMARY_VISUALS:
                break
            target = action.get("target_opportunity", "")
            # Find matching VisualType constant
            vtype = self._match_visual_type(target)
            if not vtype or vtype in seen:
                continue
            seen.add(vtype)
            selected.append(SelectedVisual(
                visual_type=vtype,
                rationale=(
                    f"Confirmed from TransformationPlan visual_actions: "
                    f"{action.get('description', target)}"
                ),
                priority_rank=len(selected),
                source_fields=_VISUAL_TYPE_SOURCE_FIELDS.get(vtype, []),
            ))

        # Signal 3: EnhancedSlide supplementary signals
        if enhanced.examples and VisualType.ICON_GRID not in seen:
            seen.add(VisualType.ICON_GRID)
            selected.append(SelectedVisual(
                visual_type=VisualType.ICON_GRID,
                rationale="EnhancedSlide.examples available — Icon Grid enriches with concrete examples.",
                priority_rank=len(selected),
                source_fields=["key_concepts", "examples"],
            ))

        if enhanced.revision_points and VisualType.CHECKLIST not in seen:
            seen.add(VisualType.CHECKLIST)
            selected.append(SelectedVisual(
                visual_type=VisualType.CHECKLIST,
                rationale="EnhancedSlide.revision_points available — Checklist provides structured review.",
                priority_rank=len(selected),
                source_fields=["steps", "revision_points"],
            ))

        # Ensure we always have at least Graph if stats are available
        if intel.numbers_and_statistics and VisualType.GRAPH not in seen:
            seen.add(VisualType.GRAPH)
            selected.append(SelectedVisual(
                visual_type=VisualType.GRAPH,
                rationale="Numeric statistics detected — Graph visualises quantitative data.",
                priority_rank=len(selected),
                source_fields=["numbers_and_statistics"],
            ))

        return selected

    # ─────────────────────────────────────────────────────────────────────────
    # Spec Builders Dispatch
    # ─────────────────────────────────────────────────────────────────────────

    def _build_spec(
        self,
        vtype: str,
        plan: TransformationPlan,
        enhanced: EnhancedSlide,
        intel: SlideIntelligence,
    ) -> Optional[Dict[str, Any]]:
        """Dispatch to the appropriate sub-module builder and return a dict."""
        try:
            if vtype in (VisualType.FLOWCHART, VisualType.PROCESS_DIAGRAM):
                return flowchart_spec.build_flowchart_spec(intel).to_dict()

            elif vtype == VisualType.TIMELINE:
                return timeline_spec.build_timeline_spec(intel).to_dict()

            elif vtype == VisualType.COMPARISON_TABLE:
                return table_spec.build_comparison_table_spec(intel).to_dict()

            elif vtype == VisualType.MATRIX:
                return table_spec.build_matrix_spec(intel).to_dict()

            elif vtype == VisualType.DECISION_TREE:
                return table_spec.build_decision_tree_spec(intel).to_dict()

            elif vtype == VisualType.ORG_CHART:
                return table_spec.build_org_chart_spec(intel).to_dict()

            elif vtype == VisualType.GRAPH:
                return graph_spec.build_graph_spec(intel).to_dict()

            elif vtype == VisualType.KPI_CARDS:
                return kpi_spec.build_kpi_spec(intel, enhanced).to_dict()

            elif vtype in (VisualType.SMART_ART, VisualType.HIERARCHY):
                if vtype == VisualType.HIERARCHY:
                    return smartart_spec.build_hierarchy_spec(intel).to_dict()
                return smartart_spec.build_smartart_spec(intel).to_dict()

            elif vtype == VisualType.CYCLE_DIAGRAM:
                return smartart_spec.build_cycle_spec(intel).to_dict()

            elif vtype == VisualType.MIND_MAP:
                return mindmap_spec.build_mindmap_spec(intel).to_dict()

            elif vtype == VisualType.AI_IMAGE:
                return image_prompt_spec.build_image_prompt_spec(intel, enhanced).to_dict()

            elif vtype == VisualType.ICON_GRID:
                return icon_spec.build_icon_grid_spec(intel, enhanced).to_dict()

            elif vtype == VisualType.CHECKLIST:
                return icon_spec.build_checklist_spec(intel).to_dict()

            else:
                logger.warning("VisualSpecificationEngine: unknown type '%s'", vtype)
                return None

        except Exception as e:
            logger.warning("Spec builder failed for type '%s': %s", vtype, e)
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _compute_density(
        specs: List[VisualSpec],
        intel: SlideIntelligence,
    ) -> float:
        """
        Estimate what fraction of the slide will be visual content.
        More specs + richer content = higher density.
        """
        base = min(len(specs) * 0.15, 0.75)
        # Bonus for slides with visuals already or high visual opportunity count
        opp_bonus = min(len(intel.visual_opportunities) * 0.05, 0.2)
        existing  = 0.05 if intel.has_existing_visuals else 0.0
        return round(min(base + opp_bonus + existing, 1.0), 3)

    @staticmethod
    def _compute_confidence(
        plan: TransformationPlan,
        intel: SlideIntelligence,
        specs: List[VisualSpec],
    ) -> float:
        """
        Compute a composite confidence score (0.0–1.0).
          - Base from TransformationPlan.confidence
          - Adjusted for number of successful spec builds
          - Capped at 0.98
        """
        base = plan.confidence * 0.5
        spec_score = min(len(specs) / max(len(intel.visual_opportunities) + 2, 1), 1.0) * 0.4
        richness = 0.1 if intel.word_count > 50 else 0.05
        return round(min(base + spec_score + richness, 0.98), 3)

    # ─────────────────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _match_visual_type(target: str) -> Optional[str]:
        """
        Match a TransformationPlan target_opportunity string to a VisualType constant.
        Case-insensitive prefix/substring match.
        """
        t = target.lower().replace(" ", "").replace("_", "")
        for vtype in VisualType.ALL:
            v = vtype.lower().replace(" ", "").replace("_", "")
            if t == v or t in v or v in t:
                return vtype
        return None
