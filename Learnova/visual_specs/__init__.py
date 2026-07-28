"""
Learnova Visual Specification Engine Package
============================================
Day 8: Converts educational content into executable visual specifications.

Exports:
  - VisualSpecificationEngine  — orchestrator
  - VisualSpecificationPlan    — root output schema
  - VisualType                 — string constants for all 16 visual types
"""

from visual_specs.engine import VisualSpecificationEngine
from visual_specs.schema import (
    AIImageSpec,
    FlowchartSpec,
    GraphSpec,
    IconSpec,
    KPISpec,
    MindMapSpec,
    SmartArtSpec,
    TableSpec,
    TimelineSpec,
    SelectedVisual,
    VisualSpec,
    VisualSpecificationPlan,
    VisualType,
)

__all__ = [
    "VisualSpecificationEngine",
    "VisualSpecificationPlan",
    "VisualType",
    "SelectedVisual",
    "VisualSpec",
    "FlowchartSpec",
    "TimelineSpec",
    "TableSpec",
    "GraphSpec",
    "KPISpec",
    "SmartArtSpec",
    "MindMapSpec",
    "AIImageSpec",
    "IconSpec",
]
