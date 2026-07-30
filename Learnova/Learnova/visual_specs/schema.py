"""
Learnova Visual Specification Engine — Schema
==============================================
Day 8: Defines all strongly-typed output structures produced by the
Visual Specification Engine.

These objects are the contract between Day 8 (visual spec generation)
and downstream layout/rendering engines (Days 9+).

No LLMs. No rendering. No Mermaid. Purely structured data.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Supported Visual Types (string constants — avoids import cycles)
# ─────────────────────────────────────────────────────────────────────────────

class VisualType:
    """String constants for all supported visual specification types."""
    FLOWCHART         = "Flowchart"
    TIMELINE          = "Timeline"
    COMPARISON_TABLE  = "Comparison Table"
    MATRIX            = "Matrix"
    KPI_CARDS         = "KPI Cards"
    SMART_ART         = "SmartArt"
    HIERARCHY         = "Hierarchy"
    MIND_MAP          = "Mind Map"
    PROCESS_DIAGRAM   = "Process Diagram"
    DECISION_TREE     = "Decision Tree"
    CYCLE_DIAGRAM     = "Cycle Diagram"
    ORG_CHART         = "Organization Chart"
    GRAPH             = "Graph"
    AI_IMAGE          = "AI Image"
    ICON_GRID         = "Icon Grid"
    CHECKLIST         = "Checklist"

    ALL = [
        FLOWCHART, TIMELINE, COMPARISON_TABLE, MATRIX, KPI_CARDS,
        SMART_ART, HIERARCHY, MIND_MAP, PROCESS_DIAGRAM, DECISION_TREE,
        CYCLE_DIAGRAM, ORG_CHART, GRAPH, AI_IMAGE, ICON_GRID, CHECKLIST,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Typed Spec Dataclasses (one per visual family)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FlowchartNode:
    id: str
    label: str
    node_type: str = "process"   # "process" | "decision" | "start" | "end"


@dataclass
class FlowchartEdge:
    from_node: str
    to_node: str
    condition: str = ""          # label for decision branches


@dataclass
class FlowchartSpec:
    nodes: List[FlowchartNode]
    edges: List[FlowchartEdge]
    labels: Dict[str, str]          # node_id → display label
    orientation: str                # "LR" | "TB"
    start_node: str
    end_node: str
    decision_nodes: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [{"id": n.id, "label": n.label, "type": n.node_type} for n in self.nodes],
            "edges": [{"from": e.from_node, "to": e.to_node, "condition": e.condition} for e in self.edges],
            "labels": self.labels,
            "orientation": self.orientation,
            "start_node": self.start_node,
            "end_node": self.end_node,
            "decision_nodes": self.decision_nodes,
        }


@dataclass
class TimelineEvent:
    id: str
    title: str
    description: str
    date: str
    is_milestone: bool = False


@dataclass
class TimelineSpec:
    ordered_events: List[TimelineEvent]
    milestones: List[str]           # event ids that are milestones
    sequence: List[str]             # ordered list of event titles
    dates: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ordered_events": [
                {"id": e.id, "title": e.title, "description": e.description,
                 "date": e.date, "is_milestone": e.is_milestone}
                for e in self.ordered_events
            ],
            "milestones": self.milestones,
            "sequence": self.sequence,
            "dates": self.dates,
        }


@dataclass
class TableSpec:
    headers: List[str]
    rows: List[List[str]]
    highlight_columns: List[int]
    highlighted_cells: List[Dict[str, int]]   # [{"row": r, "col": c}]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": self.rows,
            "highlight_columns": self.highlight_columns,
            "highlighted_cells": self.highlighted_cells,
        }


@dataclass
class GraphSeries:
    name: str
    values: List[float]


@dataclass
class GraphSpec:
    chart_type: str                 # "bar" | "line" | "pie" | "scatter" | "radar"
    title: str
    x_axis: str
    y_axis: str
    series: List[GraphSeries]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "x_axis": self.x_axis,
            "y_axis": self.y_axis,
            "series": [{"name": s.name, "values": s.values} for s in self.series],
        }


@dataclass
class KPIMetric:
    title: str
    value: str
    unit: str
    trend: str                     # "up" | "down" | "neutral"
    description: str


@dataclass
class KPISpec:
    metrics: List[KPIMetric]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": [
                {"title": m.title, "value": m.value, "unit": m.unit,
                 "trend": m.trend, "description": m.description}
                for m in self.metrics
            ]
        }


@dataclass
class SmartArtElement:
    label: str
    level: int = 0
    children: List[str] = field(default_factory=list)


@dataclass
class SmartArtSpec:
    smartart_type: str             # "Hierarchy"|"Cycle"|"Process"|"Pyramid"|"Relationship"|"Chevron"
    elements: List[SmartArtElement]
    depth: int
    alignment: str                 # "horizontal" | "vertical"
    structure: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "smartart_type": self.smartart_type,
            "elements": [{"label": e.label, "level": e.level, "children": e.children}
                         for e in self.elements],
            "depth": self.depth,
            "alignment": self.alignment,
            "structure": self.structure,
        }


@dataclass
class MindMapBranch:
    name: str
    children: List[str] = field(default_factory=list)


@dataclass
class MindMapSpec:
    central_topic: str
    branches: List[MindMapBranch]
    depth: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "central_topic": self.central_topic,
            "branches": [{"name": b.name, "children": b.children} for b in self.branches],
            "depth": self.depth,
        }


@dataclass
class AIImageSpec:
    subject: str
    style: str
    composition: str
    camera_angle: str
    educational_objective: str
    color_palette: str
    negative_prompt: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "style": self.style,
            "composition": self.composition,
            "camera_angle": self.camera_angle,
            "educational_objective": self.educational_objective,
            "color_palette": self.color_palette,
            "negative_prompt": self.negative_prompt,
        }


@dataclass
class IconItem:
    concept: str
    icon_name: str
    placement_hint: str            # e.g. "top-left", "center", "inline"
    explanation: str


@dataclass
class IconSpec:
    items: List[IconItem]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "items": [
                {"concept": i.concept, "icon_name": i.icon_name,
                 "placement_hint": i.placement_hint, "explanation": i.explanation}
                for i in self.items
            ]
        }


# ─────────────────────────────────────────────────────────────────────────────
# Root Plan Objects
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SelectedVisual:
    """Records which visual type was chosen for a slide and why."""
    visual_type: str
    rationale: str
    priority_rank: int
    source_fields: List[str]       # e.g. ["steps", "processes"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visual_type": self.visual_type,
            "rationale": self.rationale,
            "priority_rank": self.priority_rank,
            "source_fields": self.source_fields,
        }


@dataclass
class VisualSpec:
    """A single typed visual specification."""
    visual_type: str
    spec: Dict[str, Any]           # to_dict() output of the typed spec object

    def to_dict(self) -> Dict[str, Any]:
        return {
            "visual_type": self.visual_type,
            "spec": self.spec,
        }


@dataclass
class VisualSpecificationPlan:
    """
    Root output of the VisualSpecificationEngine.

    Contains all selected visual types and their fully populated,
    structured specifications ready for downstream layout/rendering engines.

    No rendering instructions. No Mermaid. No LLM artifacts.
    """

    slide_id: int
    selected_visuals: List[SelectedVisual]
    visual_specifications: List[VisualSpec]
    estimated_visual_density: float   # 0.0–1.0
    confidence: float                 # 0.0–1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "selected_visuals": [sv.to_dict() for sv in self.selected_visuals],
            "visual_specifications": [vs.to_dict() for vs in self.visual_specifications],
            "estimated_visual_density": round(self.estimated_visual_density, 3),
            "confidence": round(self.confidence, 3),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def summary_line(self) -> str:
        types = ", ".join(sv.visual_type for sv in self.selected_visuals[:4])
        return (
            f"[VisualSpecPlan slide={self.slide_id}] "
            f"Visuals: {len(self.visual_specifications)} | "
            f"Types: {types} | "
            f"Density: {self.estimated_visual_density:.2f} | "
            f"Confidence: {self.confidence:.2f}"
        )
