"""
Runtime verification script for Day 4 Intelligent Content Understanding Engine.
Parses sample_test_presentation.pptx (or sample generated deck) and runs SlideIntelligenceEngine.
"""

import os
import sys
import json

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from parsers.ppt_parser import PPTXParser
from intelligence.engine import SlideIntelligenceEngine

def main():
    sample_pptx = os.path.join(os.path.dirname(__file__), "sample_test_presentation.pptx")
    
    if not os.path.exists(sample_pptx):
        # Generate sample presentation if it doesn't exist
        print(f"Sample file {sample_pptx} not found, generating sample pptx...")
        from generate_sample import create_sample_presentation
        create_sample_presentation(sample_pptx)

    print(f"=== Parsing Document: {sample_pptx} ===")
    parser = PPTXParser()
    doc_entity = parser.parse(sample_pptx)
    print(f"Document ingested: {doc_entity.filename} with {doc_entity.total_units} slides.\n")

    print("=== Running Intelligent Content Understanding Engine ===")
    engine = SlideIntelligenceEngine()
    slide_intelligences = engine.analyze_document(doc_entity)

    print(f"\nSuccessfully analyzed {len(slide_intelligences)} slides.\n")
    print("=" * 80)
    for intel in slide_intelligences:
        print(intel.summary_line())
        print("-" * 80)
        print("  Main Topic:           ", intel.main_topic)
        print("  Primary Intent:       ", intel.primary_intent.value)
        print("  All Intents:          ", [i.value for i in intel.presentation_intents])
        print("  Key Concepts:         ", intel.key_concepts)
        print("  Definitions:          ", list(intel.definitions.keys()))
        print("  Steps:                ", intel.steps)
        print("  Stats/Numbers:        ", intel.numbers_and_statistics)
        print("  Visual Opportunities: ", [v.visual_type.value for v in intel.visual_opportunities])
        print("  Prioritized Text Count:", len(intel.prioritized_text))
        print("=" * 80)

    # Print full JSON of slide 1 as verification
    print("\n=== Sample Slide 1 JSON Output ===")
    print(json.dumps(slide_intelligences[0].to_dict(), indent=2))
    print("\nRuntime verification finished successfully!")

if __name__ == "__main__":
    main()
