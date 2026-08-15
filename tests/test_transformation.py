"""
Unit and Integration Tests for Day 5 Content Transformation & Visual Planning Engine.
Run with: python3 -m pytest tests/test_transformation.py -v
"""

import os
import sys
import pytest


from learnova.parsers.schema import (
    SlidePageEntity,
    TextBlockElement,
    EquationElement,
)
from learnova.intelligence.schema import (
    SlideIntelligence,
    TextPriority,
    VisualOpportunityType,
)
from learnova.intelligence.engine import SlideIntelligenceEngine
from learnova.intelligence.transformation import (
    SlideTransformationEngine,
    TransformationPlan,
    TextActionType,
)


@pytest.fixture
def sample_slide() -> SlidePageEntity:
    """Constructs a sample SlidePageEntity representing an educational slide with multiple structures."""
    return SlidePageEntity(
        id=12,
        unit_number=5,
        title="Photosynthesis Mechanism & Energy Production",
        text_blocks=[
            TextBlockElement(
                id="tb_title",
                text="Photosynthesis Mechanism & Energy Production",
                is_heading=True,
                heading_level=1,
                font_size=24.0,
                reading_order=0,
            ),
            TextBlockElement(
                id="tb_obj",
                text="Students will understand how plants convert light energy into chemical energy.",
                is_heading=False,
                bullet_level=0,
                reading_order=1,
            ),
            TextBlockElement(
                id="tb_def",
                text="Photosynthesis is defined as the biological process of converting solar energy into glucose.",
                is_heading=False,
                is_bold=True,
                bullet_level=0,
                reading_order=2,
            ),
            TextBlockElement(
                id="tb_step1",
                text="Step 1: Light absorption by chlorophyll pigment in thylakoid membranes.",
                is_heading=False,
                bullet_level=1,
                reading_order=3,
            ),
            TextBlockElement(
                id="tb_step2",
                text="Step 2: Water photolysis splits H2O molecules into hydrogen ions and oxygen gas.",
                is_heading=False,
                bullet_level=1,
                reading_order=4,
            ),
            TextBlockElement(
                id="tb_step3",
                text="Step 3: Carbon fixation in Calvin cycle produces glucose with 84% conversion efficiency.",
                is_heading=False,
                bullet_level=1,
                reading_order=5,
            ),
            TextBlockElement(
                id="tb_stat",
                text="Research shows 84% efficiency under optimal 25°C temperature.",
                is_heading=False,
                bullet_level=0,
                reading_order=6,
            ),
            TextBlockElement(
                id="tb_footer",
                text="Page 5 / 10 | Confidential Boilerplate",
                is_heading=False,
                reading_order=7,
            ),
        ],
        equations=[
            EquationElement(
                id="eq_1",
                latex_expression="6CO2 + 6H2O -> C6H12O6 + 6O2",
                ascii_fallback="6CO2 + 6H2O -> C6H12O6 + 6O2",
            )
        ],
    )


def test_transformation_planning(sample_slide):
    # 1. Generate Slide Intelligence
    intel_engine = SlideIntelligenceEngine()
    slide_intel = intel_engine.analyze_slide(sample_slide)

    # 2. Run Transformation Plan
    transform_engine = SlideTransformationEngine()
    plan = transform_engine.plan_transformation(slide_intel, sample_slide)

    # 3. Assert Plan structure and contents
    assert isinstance(plan, TransformationPlan)
    assert plan.slide_id == 12

    # Check text actions mapping
    assert "tb_title" in plan.text_actions
    assert plan.text_actions["tb_title"]["action"] == TextActionType.KEEP.value
    assert "Title block" in plan.text_actions["tb_title"]["reason"]

    assert "tb_footer" in plan.text_actions
    assert plan.text_actions["tb_footer"]["action"] == TextActionType.REMOVE.value
    assert "Boilerplate" in plan.text_actions["tb_footer"]["reason"]

    # Verify that steps were identified and moved to visual/summarized
    assert "tb_step1" in plan.text_actions
    assert plan.text_actions["tb_step1"]["action"] in [TextActionType.MOVE_TO_VISUAL.value, TextActionType.SUMMARIZE.value]

    # Verify visual actions tracing
    assert len(plan.visual_actions) > 0
    assert any(va["target_opportunity"] in ["Flowchart", "Process Diagram"] for va in plan.visual_actions)

    # Verify visual specifications mapping
    assert len(plan.visual_specs) > 0
    flowchart_spec = next((vs["spec"] for vs in plan.visual_specs if vs["type"] in ["Flowchart", "Process Diagram"]), None)
    assert flowchart_spec is not None
    assert len(flowchart_spec["nodes"]) >= 3
    assert len(flowchart_spec["edges"]) >= 2
    assert flowchart_spec["start_node"] == "step_1"
    assert flowchart_spec["recommended_orientation"] == "LR"

    # Verify KPI spec is generated
    kpi_spec = next((vs["spec"] for vs in plan.visual_specs if vs["type"] == "KPI Cards"), None)
    assert kpi_spec is not None
    assert len(kpi_spec["metrics"]) >= 1
    assert any("84%" in m["value"] or "25" in m["value"] for m in kpi_spec["metrics"])

    # Verify AI Image spec is present
    ai_image_spec = next((vs["spec"] for vs in plan.visual_specs if vs["type"] == "AI Image"), None)
    assert ai_image_spec is not None
    assert "style" in ai_image_spec
    assert "composition" in ai_image_spec
    assert "subject" in ai_image_spec
    assert "negative_prompt" in ai_image_spec

    # Verify remaining text does not contain footer or steps that are moved to visual
    assert any("Photosynthesis" in text for text in plan.remaining_text)
    assert not any("Confidential Boilerplate" in text for text in plan.remaining_text)

    # Speaker notes should compile context and objective
    assert "understand how plants convert" in plan.speaker_notes

    # Compression statistics check
    stats = plan.compression_statistics
    assert stats["original_word_count"] > 0
    assert stats["target_word_count"] > 0
    assert stats["compression_ratio"] < 1.0  # density should be reduced
    assert "improvement" in stats["expected_readability_improvement"]

    # Serialization test
    plan_dict = plan.to_dict()
    assert plan_dict["slide_id"] == 12
    assert isinstance(plan_dict["text_actions"], dict)
    assert isinstance(plan_dict["visual_specs"], list)
    assert plan_dict["confidence"] > 0.0
