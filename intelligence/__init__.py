"""
Learnova Intelligence Layer Package
====================================
Exports the primary entry point and schema for the Intelligent Content Understanding Engine.
"""

from intelligence.engine import SlideIntelligenceEngine
from intelligence.schema import (
    ComplexityLevel,
    ConceptRelationship,
    PrioritizedTextBlock,
    PresentationIntent,
    RelationshipType,
    SlideIntelligence,
    TextPriority,
    VisualOpportunity,
    VisualOpportunityType,
)
from intelligence.transformation import (
    SlideTransformationEngine,
    TransformationPlan,
    TextActionType,
)

__all__ = [
    "SlideIntelligenceEngine",
    "SlideIntelligence",
    "PresentationIntent",
    "TextPriority",
    "VisualOpportunityType",
    "VisualOpportunity",
    "PrioritizedTextBlock",
    "ComplexityLevel",
    "ConceptRelationship",
    "RelationshipType",
    "SlideTransformationEngine",
    "TransformationPlan",
    "TextActionType",
]
