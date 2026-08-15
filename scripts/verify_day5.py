"""
Runtime verification script for Day 5 Content Transformation & Visual Planning Engine.
Parses sample_test_presentation.pptx, runs SlideIntelligenceEngine,
then generates and exports a TransformationPlan for every slide.
"""

import json
import os
import pathlib
import sys

# Make `src/` importable and locate the shared fixture directory.
_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
_FIXTURES = _ROOT / "tests" / "fixtures"
_OUT = _ROOT / ".cache"

from learnova.parsers.ppt_parser import PPTXParser
from learnova.intelligence.engine import SlideIntelligenceEngine
from learnova.intelligence.transformation import SlideTransformationEngine

def main():
    sample_pptx = str(_FIXTURES / "sample_test_presentation.pptx")
    
    if not os.path.exists(sample_pptx):
        print(f"Sample file {sample_pptx} not found, generating sample pptx...")
        from generate_sample import create_sample_presentation
        create_sample_presentation(sample_pptx)

    print(f"=== [Day 5] Ingesting Document: {sample_pptx} ===")
    parser = PPTXParser()
    doc_entity = parser.parse(sample_pptx)
    print(f"Document parsed successfully: {doc_entity.filename} with {doc_entity.total_units} slides.\n")

    print("=== Running Day 4 SlideIntelligence Engine ===")
    intel_engine = SlideIntelligenceEngine()
    slide_intelligences = intel_engine.analyze_document(doc_entity)
    print(f"Constructed SlideIntelligence for {len(slide_intelligences)} slides.\n")

    print("=== Running Day 5 SlideTransformation Engine ===")
    transform_engine = SlideTransformationEngine()
    
    transformation_plans = []
    for idx, slide_intel in enumerate(slide_intelligences):
        slide_entity = doc_entity.slides[idx]
        plan = transform_engine.plan_transformation(slide_intel, slide_entity)
        transformation_plans.append(plan)

    print(f"Successfully generated {len(transformation_plans)} Transformation Plans.\n")
    print("=" * 80)
    for plan in transformation_plans:
        slide_idx = plan.slide_id
        stats = plan.compression_statistics
        print(f"Slide {slide_idx + 1} | Topic: {slide_intelligences[slide_idx].main_topic or '—'}")
        print(f"  Confidence:             {plan.confidence:.2f}")
        print(f"  Visual Specifications:   {[vs['type'] for vs in plan.visual_specs]}")
        print(f"  Word Count Reduction:    {stats['original_word_count']} -> {stats['target_word_count']} (Ratio: {stats['compression_ratio']:.2%})")
        print(f"  Readability Improvement: {stats['expected_readability_improvement']}")
        
        # Summary of text actions
        actions = [act["action"] for act in plan.text_actions.values()]
        action_counts = {act: actions.count(act) for act in set(actions)}
        print(f"  Text Actions Summary:   {action_counts}")
        print("-" * 80)

    # Save to JSON
    output_json = str(_OUT / "day5_transformation_plans.json")
    serializable_plans = [plan.to_dict() for plan in transformation_plans]
    _OUT.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(serializable_plans, f, indent=2)

    print(f"\nWritten all plans to: {output_json}")

    # Print slide 3 plan JSON (typically the flowchart candidate) as verification
    print("\n=== Sample Slide 3 (Flowchart Candidate) TransformationPlan JSON ===")
    slide3_plan = next((p for p in transformation_plans if p.slide_id == 2), transformation_plans[0])
    print(json.dumps(slide3_plan.to_dict(), indent=2))
    print("\n[Day 5] Runtime verification finished successfully!")

if __name__ == "__main__":
    main()
