"""
Tests for Learnova Day 8 — Visual Specification Engine.
Run with: pytest tests/test_visual_specs.py -v
"""

from __future__ import annotations

import json
import os
import sys
from typing import List

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers.schema import SlidePageEntity, TextBlockElement, EquationElement
from intelligence.engine import SlideIntelligenceEngine
from intelligence.schema import SlideIntelligence
from intelligence.transformation import SlideTransformationEngine, TransformationPlan
from enhancement.schema import EnhancedSlide
from visual_specs.schema import (
    SelectedVisual,
    VisualSpec,
    VisualSpecificationPlan,
    VisualType,
    FlowchartSpec,
    TimelineSpec,
    TableSpec,
    GraphSpec,
    KPISpec,
    SmartArtSpec,
    MindMapSpec,
    AIImageSpec,
    IconSpec,
)
from visual_specs.engine import VisualSpecificationEngine
from visual_specs import (
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


# ═══════════════════════════════════════════════════════════════════════════════
# Shared Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_slide() -> SlidePageEntity:
    """Photosynthesis slide used across all sprint tests."""
    return SlidePageEntity(
        id=1,
        unit_number=1,
        title="Photosynthesis Mechanism & Energy Production",
        text_blocks=[
            TextBlockElement(id="tb_title",  text="Photosynthesis Mechanism & Energy Production",
                             is_heading=True, heading_level=1, font_size=24.0, reading_order=0),
            TextBlockElement(id="tb_obj",    text="Students will understand how plants convert light energy into chemical energy.",
                             is_heading=False, bullet_level=0, reading_order=1),
            TextBlockElement(id="tb_def",    text="Photosynthesis is defined as the biological process of converting solar energy into glucose.",
                             is_heading=False, is_bold=True, bullet_level=0, reading_order=2),
            TextBlockElement(id="tb_step1",  text="Step 1: Light absorption by chlorophyll pigment in thylakoid membranes.",
                             is_heading=False, bullet_level=1, reading_order=3),
            TextBlockElement(id="tb_step2",  text="Step 2: Water photolysis splits H2O molecules into hydrogen ions and oxygen gas.",
                             is_heading=False, bullet_level=1, reading_order=4),
            TextBlockElement(id="tb_step3",  text="Step 3: Carbon fixation in Calvin cycle produces glucose with 84% conversion efficiency.",
                             is_heading=False, bullet_level=1, reading_order=5),
            TextBlockElement(id="tb_stat",   text="Research shows 84% efficiency under optimal 25°C temperature.",
                             is_heading=False, bullet_level=0, reading_order=6),
            TextBlockElement(id="tb_footer", text="Page 1 / 10 | Confidential",
                             is_heading=False, reading_order=7),
        ],
        equations=[
            EquationElement(id="eq_1",
                            latex_expression="6CO2 + 6H2O -> C6H12O6 + 6O2",
                            ascii_fallback="6CO2 + 6H2O -> C6H12O6 + 6O2"),
        ],
    )


@pytest.fixture
def slide_intel(sample_slide) -> SlideIntelligence:
    return SlideIntelligenceEngine().analyze_slide(sample_slide)


@pytest.fixture
def transformation_plan(slide_intel, sample_slide) -> TransformationPlan:
    return SlideTransformationEngine().plan_transformation(slide_intel, sample_slide)


@pytest.fixture
def enhanced_slide(slide_intel) -> EnhancedSlide:
    """Lightweight EnhancedSlide with pre-populated data (no LLM needed)."""
    return EnhancedSlide(
        slide_id=slide_intel.slide_id,
        slide_title=slide_intel.slide_title,
        improved_explanation="Photosynthesis converts solar energy into chemical energy via two interdependent stages.",
        simplified_explanation="Plants use sunlight to make food from CO₂ and water.",
        examples=["Wheat crops storing solar energy as starch.", "Aquarium Elodea releasing oxygen bubbles in light."],
        analogies=["Think of photosynthesis as a solar-powered sugar factory."],
        real_world_applications=["In agriculture: engineering crops for higher yield.", "In bioenergy: algae biofuel."],
        common_mistakes=["Students wrongly think plants get mass from soil."],
        interview_questions=["Why does photosynthesis plateau at high light intensity?"],
        revision_points=["6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂", "84% efficiency at 25°C", "Two stages: light and dark reactions"],
        mnemonic="LIGHT mnemonic",
        discussion_questions=["How would a 2°C rise affect photosynthetic rates?"],
        learning_tips=["Draw the chloroplast from memory daily."],
        confidence=0.88,
    )


@pytest.fixture
def engine() -> VisualSpecificationEngine:
    return VisualSpecificationEngine()


# ═══════════════════════════════════════════════════════════════════════════════
# Schema Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualSpecificationPlanSchema:
    def test_plan_has_required_fields(self):
        plan = VisualSpecificationPlan(
            slide_id=1,
            selected_visuals=[],
            visual_specifications=[],
            estimated_visual_density=0.5,
            confidence=0.8,
        )
        for f in ["slide_id", "selected_visuals", "visual_specifications",
                  "estimated_visual_density", "confidence"]:
            assert hasattr(plan, f), f"Missing field: {f}"

    def test_plan_to_dict_has_all_keys(self):
        plan = VisualSpecificationPlan(
            slide_id=2,
            selected_visuals=[],
            visual_specifications=[],
            estimated_visual_density=0.4,
            confidence=0.7,
        )
        d = plan.to_dict()
        assert "slide_id" in d
        assert "selected_visuals" in d
        assert "visual_specifications" in d
        assert "estimated_visual_density" in d
        assert "confidence" in d

    def test_plan_to_json_valid(self):
        plan = VisualSpecificationPlan(
            slide_id=3,
            selected_visuals=[
                SelectedVisual(visual_type=VisualType.FLOWCHART,
                               rationale="steps detected", priority_rank=0,
                               source_fields=["steps"])
            ],
            visual_specifications=[
                VisualSpec(visual_type=VisualType.FLOWCHART, spec={"nodes": []})
            ],
            estimated_visual_density=0.6,
            confidence=0.85,
        )
        json_str = plan.to_json()
        parsed = json.loads(json_str)
        assert parsed["slide_id"] == 3
        assert len(parsed["selected_visuals"]) == 1
        assert len(parsed["visual_specifications"]) == 1

    def test_summary_line(self):
        plan = VisualSpecificationPlan(
            slide_id=5,
            selected_visuals=[SelectedVisual(visual_type="Flowchart", rationale="x",
                                             priority_rank=0, source_fields=[])],
            visual_specifications=[],
            estimated_visual_density=0.55,
            confidence=0.9,
        )
        summary = plan.summary_line()
        assert "5" in summary
        assert "Flowchart" in summary

    def test_visual_type_constants_complete(self):
        assert len(VisualType.ALL) == 16
        assert VisualType.FLOWCHART in VisualType.ALL
        assert VisualType.MIND_MAP in VisualType.ALL
        assert VisualType.AI_IMAGE in VisualType.ALL


# ═══════════════════════════════════════════════════════════════════════════════
# Individual Spec Builder Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlowchartSpecBuilder:
    def test_builds_from_steps(self, slide_intel):
        spec = flowchart_spec.build_flowchart_spec(slide_intel)
        assert isinstance(spec, FlowchartSpec)
        assert len(spec.nodes) >= 2
        assert len(spec.edges) >= 1
        assert spec.start_node != ""
        assert spec.end_node != ""
        assert spec.orientation in ("LR", "TB")

    def test_dict_has_required_keys(self, slide_intel):
        d = flowchart_spec.build_flowchart_spec(slide_intel).to_dict()
        for key in ["nodes", "edges", "labels", "orientation", "start_node", "end_node", "decision_nodes"]:
            assert key in d, f"Missing key: {key}"

    def test_nodes_have_id_label_type(self, slide_intel):
        spec = flowchart_spec.build_flowchart_spec(slide_intel)
        for node in spec.nodes:
            assert node.id != ""
            assert node.label != ""
            assert node.node_type in ("start", "end", "process", "decision")


class TestTimelineSpecBuilder:
    def test_builds_ordered_events(self, slide_intel):
        spec = timeline_spec.build_timeline_spec(slide_intel)
        assert isinstance(spec, TimelineSpec)
        assert len(spec.ordered_events) >= 1
        assert len(spec.dates) == len(spec.ordered_events)
        assert len(spec.sequence) == len(spec.ordered_events)

    def test_dict_has_required_keys(self, slide_intel):
        d = timeline_spec.build_timeline_spec(slide_intel).to_dict()
        for key in ["ordered_events", "milestones", "sequence", "dates"]:
            assert key in d, f"Missing key: {key}"

    def test_events_have_required_fields(self, slide_intel):
        spec = timeline_spec.build_timeline_spec(slide_intel)
        for event in spec.ordered_events:
            assert event.id != ""
            assert event.title != ""
            assert event.date != ""


class TestTableSpecBuilders:
    def test_comparison_table(self, slide_intel):
        spec = table_spec.build_comparison_table_spec(slide_intel)
        assert isinstance(spec, TableSpec)
        assert len(spec.headers) >= 2

    def test_matrix_spec(self, slide_intel):
        spec = table_spec.build_matrix_spec(slide_intel)
        assert isinstance(spec, TableSpec)
        assert len(spec.headers) == 3    # "", low effort, high effort
        assert len(spec.rows) == 2       # High Impact, Low Impact

    def test_decision_tree_spec(self, slide_intel):
        spec = table_spec.build_decision_tree_spec(slide_intel)
        assert isinstance(spec, TableSpec)
        assert len(spec.headers) == 4   # Step, Condition, Yes, No
        assert len(spec.rows) >= 1

    def test_org_chart_spec(self, slide_intel):
        spec = table_spec.build_org_chart_spec(slide_intel)
        assert isinstance(spec, TableSpec)
        assert len(spec.rows) >= 1
        assert spec.rows[0][3] == "—"   # root has no parent

    def test_dict_keys(self, slide_intel):
        d = table_spec.build_comparison_table_spec(slide_intel).to_dict()
        for key in ["headers", "rows", "highlight_columns", "highlighted_cells"]:
            assert key in d


class TestGraphSpecBuilder:
    def test_builds_graph(self, slide_intel):
        spec = graph_spec.build_graph_spec(slide_intel)
        assert isinstance(spec, GraphSpec)
        assert spec.chart_type in ("bar", "line", "pie", "scatter", "radar")
        assert spec.title != ""
        assert spec.x_axis != ""
        assert spec.y_axis != ""
        assert len(spec.series) >= 1

    def test_dict_has_required_keys(self, slide_intel):
        d = graph_spec.build_graph_spec(slide_intel).to_dict()
        for key in ["chart_type", "title", "x_axis", "y_axis", "series"]:
            assert key in d

    def test_series_have_values(self, slide_intel):
        spec = graph_spec.build_graph_spec(slide_intel)
        for s in spec.series:
            assert len(s.values) >= 1
            assert all(isinstance(v, float) for v in s.values)


class TestKPISpecBuilder:
    def test_builds_from_stats(self, slide_intel, enhanced_slide):
        spec = kpi_spec.build_kpi_spec(slide_intel, enhanced_slide)
        assert isinstance(spec, KPISpec)
        assert len(spec.metrics) >= 1

    def test_metrics_have_required_fields(self, slide_intel, enhanced_slide):
        spec = kpi_spec.build_kpi_spec(slide_intel, enhanced_slide)
        for m in spec.metrics:
            assert m.title != ""
            assert m.value != ""
            assert m.trend in ("up", "down", "neutral")

    def test_dict_has_metrics_key(self, slide_intel, enhanced_slide):
        d = kpi_spec.build_kpi_spec(slide_intel, enhanced_slide).to_dict()
        assert "metrics" in d
        assert isinstance(d["metrics"], list)


class TestSmartArtSpecBuilders:
    def test_smartart_spec(self, slide_intel):
        spec = smartart_spec.build_smartart_spec(slide_intel)
        assert isinstance(spec, SmartArtSpec)
        assert spec.smartart_type != ""
        assert len(spec.elements) >= 1
        assert spec.depth >= 1

    def test_hierarchy_spec(self, slide_intel):
        spec = smartart_spec.build_hierarchy_spec(slide_intel)
        assert isinstance(spec, SmartArtSpec)
        assert spec.smartart_type == "Hierarchy"

    def test_cycle_spec(self, slide_intel):
        spec = smartart_spec.build_cycle_spec(slide_intel)
        assert isinstance(spec, SmartArtSpec)
        assert spec.smartart_type == "Cycle"
        assert spec.structure.get("is_closed") is True

    def test_forced_type(self, slide_intel):
        spec = smartart_spec.build_smartart_spec(slide_intel, forced_type="Pyramid")
        assert spec.smartart_type == "Pyramid"

    def test_dict_keys(self, slide_intel):
        d = smartart_spec.build_smartart_spec(slide_intel).to_dict()
        for key in ["smartart_type", "elements", "depth", "alignment", "structure"]:
            assert key in d


class TestMindMapSpecBuilder:
    def test_builds_mindmap(self, slide_intel):
        spec = mindmap_spec.build_mindmap_spec(slide_intel)
        assert isinstance(spec, MindMapSpec)
        assert spec.central_topic != ""
        assert len(spec.branches) >= 1
        assert spec.depth >= 1

    def test_dict_has_required_keys(self, slide_intel):
        d = mindmap_spec.build_mindmap_spec(slide_intel).to_dict()
        for key in ["central_topic", "branches", "depth"]:
            assert key in d

    def test_branches_have_name(self, slide_intel):
        spec = mindmap_spec.build_mindmap_spec(slide_intel)
        for branch in spec.branches:
            assert branch.name != ""
            assert isinstance(branch.children, list)


class TestImagePromptSpecBuilder:
    def test_builds_spec(self, slide_intel, enhanced_slide):
        spec = image_prompt_spec.build_image_prompt_spec(slide_intel, enhanced_slide)
        assert isinstance(spec, AIImageSpec)
        assert spec.subject != ""
        assert spec.style != ""
        assert spec.negative_prompt != ""

    def test_analogy_enrichment(self, slide_intel, enhanced_slide):
        spec = image_prompt_spec.build_image_prompt_spec(slide_intel, enhanced_slide)
        # Subject should contain analogy text if enhanced_slide has analogies
        assert len(spec.subject) > 20

    def test_dict_has_required_keys(self, slide_intel, enhanced_slide):
        d = image_prompt_spec.build_image_prompt_spec(slide_intel, enhanced_slide).to_dict()
        for key in ["subject", "style", "composition", "camera_angle",
                    "educational_objective", "color_palette", "negative_prompt"]:
            assert key in d


class TestIconSpecBuilder:
    def test_builds_icon_grid(self, slide_intel, enhanced_slide):
        spec = icon_spec.build_icon_grid_spec(slide_intel, enhanced_slide)
        assert isinstance(spec, IconSpec)
        assert len(spec.items) >= 1

    def test_items_have_required_fields(self, slide_intel, enhanced_slide):
        spec = icon_spec.build_icon_grid_spec(slide_intel, enhanced_slide)
        for item in spec.items:
            assert item.concept != ""
            assert item.icon_name != ""
            assert item.placement_hint != ""

    def test_builds_checklist(self, slide_intel):
        spec = icon_spec.build_checklist_spec(slide_intel)
        assert isinstance(spec, IconSpec)
        assert len(spec.items) >= 1

    def test_dict_has_items_key(self, slide_intel, enhanced_slide):
        d = icon_spec.build_icon_grid_spec(slide_intel, enhanced_slide).to_dict()
        assert "items" in d
        assert isinstance(d["items"], list)


# ═══════════════════════════════════════════════════════════════════════════════
# Engine Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualSpecificationEngine:
    def test_engine_instantiates(self):
        e = VisualSpecificationEngine()
        assert e is not None

    def test_generate_returns_plan(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert isinstance(plan, VisualSpecificationPlan)

    def test_slide_id_matches(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert plan.slide_id == slide_intel.slide_id

    def test_selected_visuals_non_empty(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert len(plan.selected_visuals) >= 1, "selected_visuals should not be empty"

    def test_selected_visuals_have_priority_ranks(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        ranks = [sv.priority_rank for sv in plan.selected_visuals]
        assert len(ranks) == len(set(ranks)) or all(r >= 0 for r in ranks)

    def test_visual_specifications_non_empty(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert len(plan.visual_specifications) >= 1

    def test_always_includes_ai_image(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        types = [vs.visual_type for vs in plan.visual_specifications]
        assert VisualType.AI_IMAGE in types, "AI Image spec should always be present"

    def test_always_includes_mind_map(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        types = [vs.visual_type for vs in plan.visual_specifications]
        assert VisualType.MIND_MAP in types, "Mind Map spec should always be present"

    def test_confidence_in_range(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert 0.0 <= plan.confidence <= 1.0, f"confidence out of range: {plan.confidence}"

    def test_density_in_range(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        assert 0.0 <= plan.estimated_visual_density <= 1.0

    def test_no_duplicate_visual_types(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        types = [vs.visual_type for vs in plan.visual_specifications]
        assert len(types) == len(set(types)), f"Duplicate visual types found: {types}"

    def test_to_dict_serializable(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        d = plan.to_dict()
        assert isinstance(d, dict)
        json_str = plan.to_json()
        parsed = json.loads(json_str)
        assert parsed["slide_id"] == slide_intel.slide_id

    def test_all_specs_have_non_empty_spec_dict(self, engine, transformation_plan, enhanced_slide, slide_intel):
        plan = engine.generate(transformation_plan, enhanced_slide, slide_intel)
        for vs in plan.visual_specifications:
            assert isinstance(vs.spec, dict), f"{vs.visual_type} spec is not a dict"
            assert len(vs.spec) > 0, f"{vs.visual_type} spec dict is empty"

    def test_no_llm_imports_in_module(self):
        """Verify visual_specs package never imports LLM/SDK modules."""
        import visual_specs.engine as eng_mod
        import visual_specs.flowchart_spec as fc_mod
        import visual_specs.kpi_spec as kpi_mod

        # None of these modules should import groq, google.generativeai, or providers.llm_provider
        for mod in [eng_mod, fc_mod, kpi_mod]:
            src = open(mod.__file__).read()
            assert "groq" not in src.lower(), f"groq import found in {mod.__file__}"
            assert "generativeai" not in src.lower(), f"generativeai import found in {mod.__file__}"
            assert "llm_provider" not in src, f"llm_provider import found in {mod.__file__}"
