"""
Learnova Intelligence Layer — Engine Orchestrator
=================================================
Main entry point for the Intelligent Content Understanding Engine.

Orchestrates all sub-modules:
  - concept_extractor
  - content_classifier
  - text_prioritizer
  - visual_opportunity
  - complexity_scorer

Consumes SlidePageEntity / DocumentEntity and produces SlideIntelligence object(s).
No LLMs, no slide redesigns, no external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from learnova.parsers.schema import DocumentEntity, SlidePageEntity
from learnova.intelligence import concept_extractor
from learnova.intelligence import content_classifier
from learnova.intelligence import text_prioritizer
from learnova.intelligence import visual_opportunity
from learnova.intelligence import complexity_scorer
from learnova.intelligence.schema import SlideIntelligence


class SlideIntelligenceEngine:
    """
    Intelligent Content Understanding Engine for Learnova.
    """

    def analyze_slide(
        self,
        slide: SlidePageEntity,
        doc_repeated_texts: Set[str] = None,
    ) -> SlideIntelligence:
        """
        Analyzes a single SlidePageEntity and produces a complete SlideIntelligence object.

        Args:
            slide: SlidePageEntity to understand
            doc_repeated_texts: Global document-level set of repeated text blocks

        Returns:
            Structured SlideIntelligence object
        """
        # Step 1: Extract all 20 concept responsibilities
        extracted = concept_extractor.extract_all(slide)

        # Step 2: Content classification into PresentationIntents
        classification = content_classifier.classify(slide, extracted)

        # Step 3: Text prioritization
        prioritized_text = text_prioritizer.prioritize_text_blocks(
            slide=slide,
            concepts=extracted,
            doc_repeated_texts=doc_repeated_texts,
        )

        # Step 4: Visual Opportunity Detection
        opps = visual_opportunity.detect_visual_opportunities(
            slide=slide,
            concepts=extracted,
            intents=classification["presentation_intents"],
        )

        # Step 5: Complexity Scoring
        score, level = complexity_scorer.compute_complexity_score(slide, extracted)

        # Step 6: Construct Information Hierarchy
        info_hierarchy = {
            "level_1_topic": extracted["main_topic"],
            "level_2_key_concepts": extracted["key_concepts"],
            "level_3_supporting": extracted["supporting_concepts"],
            "level_4_details": (
                extracted["important_facts"]
                + extracted["examples"]
                + extracted["numbers_and_statistics"]
            )[:8],
        }

        # Step 7: Check existing visual assets
        has_existing_visuals = bool(
            slide.visual_assets or slide.charts or slide.diagrams or slide.rendered_page_image
        )

        # Word count & sentence count metrics
        all_text = slide.get_full_text()
        word_count = len(all_text.split())
        sentence_count = extracted["complexity_signals"].get("sentence_count", 0)

        # Build final SlideIntelligence object
        return SlideIntelligence(
            slide_id=slide.id,
            unit_number=slide.unit_number,
            slide_title=slide.title or f"Slide {slide.unit_number}",
            main_topic=extracted["main_topic"],
            learning_objective=extracted["learning_objective"],
            key_concepts=extracted["key_concepts"],
            supporting_concepts=extracted["supporting_concepts"],
            definitions=extracted["definitions"],
            important_facts=extracted["important_facts"],
            numbers_and_statistics=extracted["numbers_and_statistics"],
            processes=extracted["processes"],
            comparisons=extracted["comparisons"],
            cause_and_effect=extracted["cause_and_effect"],
            chronology=extracted["chronology"],
            advantages=extracted["advantages"],
            disadvantages=extracted["disadvantages"],
            steps=extracted["steps"],
            examples=extracted["examples"],
            formulas=extracted["formulas"],
            lists=extracted["lists"],
            faqs=extracted["faqs"],
            relationships=extracted["relationships"],
            complexity_score=score,
            complexity_level=level,
            presentation_intents=classification["presentation_intents"],
            primary_intent=classification["primary_intent"],
            intent_scores=classification["intent_scores"],
            prioritized_text=prioritized_text,
            visual_opportunities=opps,
            suggested_visualizations=[o.visual_type.value for o in opps],
            information_hierarchy=info_hierarchy,
            has_existing_visuals=has_existing_visuals,
            word_count=word_count,
            sentence_count=sentence_count,
            text_block_count=len(slide.text_blocks),
        )

    def analyze_document(self, doc: DocumentEntity) -> List[SlideIntelligence]:
        """
        Analyzes an entire DocumentEntity slide by slide.
        Computes document-wide repeated text for global de-duplication.

        Args:
            doc: DocumentEntity graph from parser

        Returns:
            List of SlideIntelligence objects (one per slide)
        """
        # Pre-pass: Identify repeated boilerplate across slides
        text_counts: Dict[str, int] = {}
        for slide in doc.slides:
            for tb in slide.text_blocks:
                t = tb.text.strip().lower()
                if t and len(t.split()) <= 8:
                    text_counts[t] = text_counts.get(t, 0) + 1

        doc_repeated = {t for t, count in text_counts.items() if count >= 3}

        # Main analysis pass
        slide_intelligences: List[SlideIntelligence] = []
        for slide in doc.slides:
            intelligence = self.analyze_slide(slide, doc_repeated_texts=doc_repeated)
            slide_intelligences.append(intelligence)

        return slide_intelligences
