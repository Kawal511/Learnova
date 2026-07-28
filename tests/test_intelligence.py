"""
Unit and Integration Tests for Day 4 Intelligent Content Understanding Engine
Run with: python3 -m pytest tests/test_intelligence.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers.schema import (
    SlidePageEntity,
    TextBlockElement,
    TableElement,
    EquationElement,
    VisualAssetElement,
)
from intelligence.schema import (
    SlideIntelligence,
    PresentationIntent,
    TextPriority,
    VisualOpportunityType,
    ComplexityLevel,
)
from intelligence.engine import SlideIntelligenceEngine
from intelligence import concept_extractor
from intelligence import content_classifier
from intelligence import text_prioritizer
from intelligence import visual_opportunity
from intelligence import complexity_scorer


@pytest.fixture
def sample_slide() -> SlidePageEntity:
    """Constructs a sample SlidePageEntity representing an educational slide."""
    return SlidePageEntity(
        id=0,
        unit_number=1,
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
                text="Page 1 / 10 | Confidential",
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


class TestConceptExtractor:
    def test_extract_main_topic(self, sample_slide):
        topic = concept_extractor.extract_main_topic(sample_slide)
        assert topic == "Photosynthesis Mechanism & Energy Production"

    def test_extract_learning_objective(self, sample_slide):
        obj = concept_extractor.extract_learning_objective(sample_slide)
        assert "understand" in obj.lower()

    def test_extract_key_concepts(self, sample_slide):
        concepts = concept_extractor.extract_key_concepts(sample_slide)
        assert len(concepts) > 0
        assert any("Photosynthesis" in c for c in concepts)

    def test_extract_definitions(self, sample_slide):
        defs = concept_extractor.extract_definitions(sample_slide)
        assert "Photosynthesis" in defs or any("photosynthesis" in k.lower() for k in defs)

    def test_extract_steps(self, sample_slide):
        steps = concept_extractor.extract_steps(sample_slide)
        assert len(steps) >= 3
        assert any("Light absorption" in s for s in steps)

    def test_extract_numbers_and_statistics(self, sample_slide):
        stats = concept_extractor.extract_numbers_and_statistics(sample_slide)
        assert len(stats) > 0
        assert any("84%" in s for s in stats)

    def test_extract_formulas(self, sample_slide):
        formulas = concept_extractor.extract_formulas(sample_slide)
        assert len(formulas) > 0
        assert any("6CO2" in f for f in formulas)


class TestContentClassifier:
    def test_classify_slide(self, sample_slide):
        extracted = concept_extractor.extract_all(sample_slide)
        result = content_classifier.classify(sample_slide, extracted)
        intents = result["presentation_intents"]
        assert len(intents) > 0
        assert any(i in intents for i in [
            PresentationIntent.WORKFLOW,
            PresentationIntent.PROCESS,
            PresentationIntent.DEFINITION,
            PresentationIntent.FORMULA,
            PresentationIntent.STATISTICS,
        ])


class TestTextPrioritizer:
    def test_prioritize_text_blocks(self, sample_slide):
        extracted = concept_extractor.extract_all(sample_slide)
        prioritized = text_prioritizer.prioritize_text_blocks(sample_slide, extracted)
        assert len(prioritized) == len(sample_slide.text_blocks)
        
        # Check title is HIGH priority
        title_block = next(p for p in prioritized if p.block_id == "tb_title")
        assert title_block.priority == TextPriority.HIGH

        # Check footer is DECORATIVE priority
        footer_block = next(p for p in prioritized if p.block_id == "tb_footer")
        assert footer_block.priority == TextPriority.DECORATIVE


class TestVisualOpportunityDetector:
    def test_detect_visual_opportunities(self, sample_slide):
        extracted = concept_extractor.extract_all(sample_slide)
        classification = content_classifier.classify(sample_slide, extracted)
        opps = visual_opportunity.detect_visual_opportunities(
            sample_slide, extracted, classification["presentation_intents"]
        )
        assert len(opps) > 0
        opp_types = [o.visual_type for o in opps]
        assert any(t in opp_types for t in [
            VisualOpportunityType.FLOWCHART,
            VisualOpportunityType.PROCESS_DIAGRAM,
            VisualOpportunityType.KPI_CARDS,
            VisualOpportunityType.ICON_GRID,
        ])
        for opp in opps:
            assert len(opp.rationale) > 10
            assert 0.0 <= opp.confidence <= 1.0


class TestComplexityScorer:
    def test_compute_complexity_score(self, sample_slide):
        extracted = concept_extractor.extract_all(sample_slide)
        score, level = complexity_scorer.compute_complexity_score(sample_slide, extracted)
        assert 0.0 <= score <= 10.0
        assert isinstance(level, ComplexityLevel)


class TestSlideIntelligenceEngine:
    def test_engine_analyze_slide(self, sample_slide):
        engine = SlideIntelligenceEngine()
        intel = engine.analyze_slide(sample_slide)
        assert isinstance(intel, SlideIntelligence)
        assert intel.main_topic == "Photosynthesis Mechanism & Energy Production"
        assert len(intel.presentation_intents) > 0
        assert len(intel.prioritized_text) == len(sample_slide.text_blocks)
        assert isinstance(intel.to_dict(), dict)

    def test_engine_summary_line(self, sample_slide):
        engine = SlideIntelligenceEngine()
        intel = engine.analyze_slide(sample_slide)
        summary = intel.summary_line()
        assert "[Slide 1]" in summary
        assert "Photosynthesis" in summary
