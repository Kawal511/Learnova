"""
Learnova Intelligence Layer — Schema
=====================================
Defines all strongly-typed output structures produced by the
Intelligent Content Understanding Engine for every SlidePageEntity.

These objects are the contract between Day 4 (understanding) and
Day 5+ (layout generation, visual rendering, content transformation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Enumerations
# ─────────────────────────────────────────────────────────────────────────────

class PresentationIntent(str, Enum):
    """
    Classifies the pedagogical / visual purpose of a slide.
    A slide may have multiple intents; the first is the primary intent.
    """
    DEFINITION    = "Definition"
    PROCESS       = "Process"
    WORKFLOW      = "Workflow"
    TIMELINE      = "Timeline"
    COMPARISON    = "Comparison"
    TABLE         = "Table"
    STATISTICS    = "Statistics"
    HIERARCHY     = "Hierarchy"
    CYCLE         = "Cycle"
    PROBLEM       = "Problem"
    SOLUTION      = "Solution"
    ARCHITECTURE  = "Architecture"
    FORMULA       = "Formula"
    CASE_STUDY    = "Case Study"
    SUMMARY       = "Summary"
    CONCLUSION    = "Conclusion"
    CHECKLIST     = "Checklist"
    FAQ           = "FAQ"
    GENERAL       = "General"          # fallback when no intent is confident


class TextPriority(str, Enum):
    """
    Importance classification of an individual text block.
    Downstream layout modules use this to decide what to keep, summarize, or replace.
    """
    HIGH        = "High"        # Must remain visible — title, key concept, heading
    MEDIUM      = "Medium"      # Keep as supporting detail
    LOW         = "Low"         # Candidate for removal or visual replacement
    DECORATIVE  = "Decorative"  # Aesthetic only — no semantic content
    REDUNDANT   = "Redundant"   # Near-duplicate of a higher-priority block
    REPEATED    = "Repeated"    # Appears on another slide in the same document


class VisualOpportunityType(str, Enum):
    """All recognized visual transformation targets."""
    FLOWCHART           = "Flowchart"
    TIMELINE            = "Timeline"
    COMPARISON_TABLE    = "Comparison Table"
    SMART_ART           = "SmartArt"
    DECISION_TREE       = "Decision Tree"
    PYRAMID             = "Pyramid"
    CYCLE_DIAGRAM       = "Cycle Diagram"
    PROCESS_DIAGRAM     = "Process Diagram"
    ORG_CHART           = "Organization Chart"
    MATRIX              = "Matrix"
    ROADMAP             = "Roadmap"
    CHECKLIST           = "Checklist"
    ICON_GRID           = "Icon Grid"
    INFOGRAPHIC         = "Infographic"
    IMAGE_WITH_CAPTION  = "Image with Caption"
    KPI_CARDS           = "KPI Cards"


class ComplexityLevel(str, Enum):
    """Human-readable complexity band mapped from the 0–10 score."""
    INTRODUCTORY  = "Introductory"   # 0–2
    INTERMEDIATE  = "Intermediate"   # 3–5
    ADVANCED      = "Advanced"       # 6–8
    EXPERT        = "Expert"         # 9–10


class RelationshipType(str, Enum):
    """Semantic relationship types between concepts."""
    IS_A            = "is_a"
    PART_OF         = "part_of"
    CAUSES          = "causes"
    LEADS_TO        = "leads_to"
    DEPENDS_ON      = "depends_on"
    CONTRASTS_WITH  = "contrasts_with"
    SUPPORTS        = "supports"
    DEFINED_BY      = "defined_by"
    INCLUDES        = "includes"
    FOLLOWS         = "follows"
    UNKNOWN         = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Sub-dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ConceptRelationship:
    """
    A semantic triple linking two concepts extracted from the slide.
    Example: subject="Photosynthesis", predicate=LEADS_TO, object="Glucose production"
    """
    subject:   str
    predicate: RelationshipType
    object:    str
    confidence: float = 0.5          # 0.0–1.0 heuristic confidence


@dataclass
class VisualOpportunity:
    """
    Describes a single opportunity to replace or augment text with a visual.
    Each opportunity records WHAT type of visual is appropriate and WHY.
    """
    visual_type:    VisualOpportunityType
    rationale:      str               # Human-readable explanation of why this fits
    confidence:     float             # 0.0–1.0
    source_fields:  List[str] = field(default_factory=list)   # which extracted fields triggered this
    priority_rank:  int = 0           # lower = more important; set by engine after sorting


@dataclass
class PrioritizedTextBlock:
    """
    Wraps a reference to a TextBlockElement with its assigned priority and reason.
    The `block_id` matches TextBlockElement.id from the parsers layer.
    """
    block_id:    str
    text:        str
    priority:    TextPriority
    reason:      str                  # Why this priority was assigned
    word_count:  int = 0


@dataclass
class IntentScore:
    """Internal scoring record — used during classification, not part of final output."""
    intent: PresentationIntent
    score:  float
    signals: List[str] = field(default_factory=list)   # which signals fired


# ─────────────────────────────────────────────────────────────────────────────
# Root Output Object
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SlideIntelligence:
    """
    Root intelligence object produced for every SlidePageEntity.

    This is the complete output of the Intelligent Content Understanding Engine.
    All downstream modules (layout generator, visual renderer, content transformer)
    consume this object instead of the raw SlidePageEntity.

    Fields map directly to the 20 responsibilities + classification + prioritization
    + visual detection requirements specified in the Day 4 sprint.
    """

    # ── Identity ─────────────────────────────────────────────────────────────
    slide_id:    int
    unit_number: int
    slide_title: str

    # ── Responsibility 1: Main Topic ─────────────────────────────────────────
    main_topic: str = ""

    # ── Responsibility 2: Learning Objective ─────────────────────────────────
    learning_objective: str = ""

    # ── Responsibility 3: Key Concepts ───────────────────────────────────────
    key_concepts: List[str] = field(default_factory=list)

    # ── Responsibility 4: Supporting Concepts ────────────────────────────────
    supporting_concepts: List[str] = field(default_factory=list)

    # ── Responsibility 5: Definitions ────────────────────────────────────────
    definitions: Dict[str, str] = field(default_factory=dict)          # term → definition text

    # ── Responsibility 6: Important Facts ────────────────────────────────────
    important_facts: List[str] = field(default_factory=list)

    # ── Responsibility 7: Numbers & Statistics ───────────────────────────────
    numbers_and_statistics: List[str] = field(default_factory=list)    # raw matched strings

    # ── Responsibility 8: Processes ──────────────────────────────────────────
    processes: List[str] = field(default_factory=list)

    # ── Responsibility 9: Comparisons ────────────────────────────────────────
    comparisons: List[Dict[str, Any]] = field(default_factory=list)    # [{left, right, aspect}]

    # ── Responsibility 10: Cause & Effect ────────────────────────────────────
    cause_and_effect: List[Dict[str, str]] = field(default_factory=list)  # [{cause, effect}]

    # ── Responsibility 11: Chronology ────────────────────────────────────────
    chronology: List[str] = field(default_factory=list)                # ordered temporal items

    # ── Responsibility 12: Advantages ────────────────────────────────────────
    advantages: List[str] = field(default_factory=list)

    # ── Responsibility 13: Disadvantages ─────────────────────────────────────
    disadvantages: List[str] = field(default_factory=list)

    # ── Responsibility 14: Steps ─────────────────────────────────────────────
    steps: List[str] = field(default_factory=list)

    # ── Responsibility 15: Examples ──────────────────────────────────────────
    examples: List[str] = field(default_factory=list)

    # ── Responsibility 16: Formulas ──────────────────────────────────────────
    formulas: List[str] = field(default_factory=list)

    # ── Responsibility 17: Lists ─────────────────────────────────────────────
    lists: List[List[str]] = field(default_factory=list)               # list-of-lists (each bullet group)

    # ── Responsibility 18: FAQs ──────────────────────────────────────────────
    faqs: List[Dict[str, str]] = field(default_factory=list)           # [{question, answer}]

    # ── Responsibility 19: Relationships ─────────────────────────────────────
    relationships: List[ConceptRelationship] = field(default_factory=list)

    # ── Responsibility 20: Complexity ────────────────────────────────────────
    complexity_score: float = 0.0                                      # 0.0–10.0
    complexity_level: ComplexityLevel = ComplexityLevel.INTRODUCTORY

    # ── Content Classification ────────────────────────────────────────────────
    presentation_intents: List[PresentationIntent] = field(default_factory=list)
    primary_intent: PresentationIntent = PresentationIntent.GENERAL
    intent_scores: List[IntentScore] = field(default_factory=list)     # full scoring breakdown

    # ── Text Prioritization ───────────────────────────────────────────────────
    prioritized_text: List[PrioritizedTextBlock] = field(default_factory=list)

    # ── Visual Opportunities ──────────────────────────────────────────────────
    visual_opportunities: List[VisualOpportunity] = field(default_factory=list)
    suggested_visualizations: List[str] = field(default_factory=list)  # ordered VisualOpportunityType names

    # ── Information Hierarchy ─────────────────────────────────────────────────
    information_hierarchy: Dict[str, Any] = field(default_factory=dict)
    # Shape: {
    #   "level_1": str (main topic),
    #   "level_2": List[str] (key concepts),
    #   "level_3": List[str] (supporting concepts),
    #   "level_4": List[str] (examples / details)
    # }

    # ── Metadata ──────────────────────────────────────────────────────────────
    has_existing_visuals: bool = False    # slide already contains images/charts/diagrams
    word_count: int = 0
    sentence_count: int = 0
    text_block_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dictionary for logging, caching, or downstream JSON consumption."""
        return {
            "slide_id":             self.slide_id,
            "unit_number":          self.unit_number,
            "slide_title":          self.slide_title,
            "main_topic":           self.main_topic,
            "learning_objective":   self.learning_objective,
            "key_concepts":         self.key_concepts,
            "supporting_concepts":  self.supporting_concepts,
            "definitions":          self.definitions,
            "important_facts":      self.important_facts,
            "numbers_and_statistics": self.numbers_and_statistics,
            "processes":            self.processes,
            "comparisons":          self.comparisons,
            "cause_and_effect":     self.cause_and_effect,
            "chronology":           self.chronology,
            "advantages":           self.advantages,
            "disadvantages":        self.disadvantages,
            "steps":                self.steps,
            "examples":             self.examples,
            "formulas":             self.formulas,
            "lists":                self.lists,
            "faqs":                 self.faqs,
            "relationships": [
                {
                    "subject":    r.subject,
                    "predicate":  r.predicate.value,
                    "object":     r.object,
                    "confidence": r.confidence,
                }
                for r in self.relationships
            ],
            "complexity_score":     self.complexity_score,
            "complexity_level":     self.complexity_level.value,
            "presentation_intents": [i.value for i in self.presentation_intents],
            "primary_intent":       self.primary_intent.value,
            "prioritized_text": [
                {
                    "block_id":   p.block_id,
                    "text":       p.text,
                    "priority":   p.priority.value,
                    "reason":     p.reason,
                    "word_count": p.word_count,
                }
                for p in self.prioritized_text
            ],
            "visual_opportunities": [
                {
                    "visual_type":   v.visual_type.value,
                    "rationale":     v.rationale,
                    "confidence":    v.confidence,
                    "source_fields": v.source_fields,
                    "priority_rank": v.priority_rank,
                }
                for v in self.visual_opportunities
            ],
            "suggested_visualizations": self.suggested_visualizations,
            "information_hierarchy":    self.information_hierarchy,
            "has_existing_visuals":     self.has_existing_visuals,
            "word_count":               self.word_count,
            "sentence_count":           self.sentence_count,
            "text_block_count":         self.text_block_count,
        }

    def summary_line(self) -> str:
        """One-line human-readable summary for logging."""
        intents = ", ".join(i.value for i in self.presentation_intents[:3])
        visuals = len(self.visual_opportunities)
        return (
            f"[Slide {self.unit_number}] '{self.slide_title}' | "
            f"Topic: {self.main_topic or '—'} | "
            f"Intents: {intents or 'General'} | "
            f"Complexity: {self.complexity_score:.1f} ({self.complexity_level.value}) | "
            f"Visual Opps: {visuals}"
        )
