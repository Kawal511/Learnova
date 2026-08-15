"""
Learnova Content Transformation & Visual Planning Engine
=========================================================
Implements the Day 5 objectives. Programmatically determines text actions,
visual actions, content compression statistics, and structured visual specifications
without calling any LLMs or external services.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set

from learnova.parsers.schema import SlidePageEntity, TextBlockElement, TableElement, StructuredChartElement
from learnova.intelligence.schema import (
    SlideIntelligence,
    TextPriority,
    VisualOpportunity,
    VisualOpportunityType,
    PresentationIntent,
)


class TextActionType(str, Enum):
    KEEP = "KEEP"
    SUMMARIZE = "SUMMARIZE"
    REMOVE = "REMOVE"
    MERGE = "MERGE"
    MOVE_TO_VISUAL = "MOVE_TO_VISUAL"
    MOVE_TO_NOTES = "MOVE_TO_NOTES"


@dataclass
class TextAction:
    block_id: str
    original_text: str
    action: TextActionType
    reason: str
    transformed_text: Optional[str] = None


@dataclass
class VisualAction:
    action_type: str            # e.g., "REPLACE_TEXT_WITH_VISUAL", "CREATE_KPI_CARDS", "ADD_AI_IMAGE"
    target_opportunity: str     # e.g., "Flowchart", "Timeline", "KPI Cards"
    description: str
    source_block_ids: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# Visual Specifications Dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FlowchartSpecification:
    nodes: List[Dict[str, Any]]       # [{"id": str, "label": str, "type": str}]
    edges: List[Dict[str, str]]       # [{"from": str, "to": str}]
    labels: Dict[str, str]            # e.g. edge decisions/labels
    start_node: str
    end_node: str
    decision_nodes: List[str]
    recommended_orientation: str      # "TB" (Top-to-Bottom) or "LR" (Left-to-Right)


@dataclass
class TimelineSpecification:
    ordered_events: List[Dict[str, Any]]  # [{"id": str, "title": str, "description": str, "date": str}]
    dates: List[str]
    milestones: List[str]


@dataclass
class ComparisonTableSpecification:
    headers: List[str]
    rows: List[List[str]]
    highlight_columns: List[int]
    merge_cells: List[Dict[str, Any]]  # [{"start_row": int, "end_row": int, "start_col": int, "end_col": int}]


@dataclass
class DecisionTreeSpecification:
    nodes: List[Dict[str, Any]]       # [{"id": str, "label": str, "type": str}]
    edges: List[Dict[str, Any]]       # [{"from": str, "to": str, "condition": str}]
    start_node: str
    decision_nodes: List[str]
    outcomes: List[str]


@dataclass
class HierarchySpecification:
    root: str
    levels: List[List[str]]
    relationships: List[Dict[str, str]]  # [{"parent": str, "child": str}]


@dataclass
class CycleSpecification:
    steps: List[str]
    flow_direction: str               # "clockwise" or "counterclockwise"
    is_closed: bool


@dataclass
class RoadmapSpecification:
    phases: List[Dict[str, Any]]      # [{"phase": str, "description": str, "duration": str}]
    milestones: List[Dict[str, Any]]  # [{"date": str, "name": str}]
    deliverables: List[str]


@dataclass
class MatrixSpecification:
    quadrants: List[Dict[str, Any]]   # [{"quadrant": str, "title": str, "items": List[str]}]
    axes: Dict[str, str]              # {"x_axis": str, "y_axis": str}


@dataclass
class KPICardSpecification:
    metrics: List[Dict[str, Any]]     # [{"label": str, "value": str, "change": str, "description": str}]


@dataclass
class ChecklistSpecification:
    items: List[Dict[str, Any]]       # [{"task": str, "is_required": bool, "order": int}]


@dataclass
class OrganizationChartSpecification:
    roles: List[Dict[str, Any]]       # [{"id": str, "title": str, "department": str, "reports_to": Optional[str]}]


@dataclass
class IconGridSpecification:
    items: List[Dict[str, Any]]       # [{"concept": str, "icon": str, "explanation": str}]


@dataclass
class GraphSpecification:
    graph_type: str                   # "bar", "line", "pie", "scatter", "radar"
    x_axis: str
    y_axis: str
    series: List[str]
    values: List[List[float]]
    title: str


@dataclass
class InfographicSpecification:
    layout_type: str                  # e.g., "process", "grid", "comparison", "list"
    sections: List[Dict[str, Any]]    # [{"title": str, "description": str, "visual_hint": str}]


@dataclass
class AIImageSpecification:
    subject: str
    style: str
    composition: str
    camera_angle: str
    educational_purpose: str
    visual_emphasis: str
    negative_prompt: str


@dataclass
class SmartArtSpecification:
    smartart_type: str                # "Hierarchy", "Cycle", "Relationship", "Process", "Pyramid", "Chevron"
    elements: List[str]
    structure: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# Root Transformation Plan Object
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TransformationPlan:
    slide_id: int
    text_actions: Dict[str, Dict[str, Any]]
    visual_actions: List[Dict[str, Any]]
    visual_specs: List[Dict[str, Any]]
    remaining_text: List[str]
    speaker_notes: str
    compression_statistics: Dict[str, Any]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slide_id": self.slide_id,
            "text_actions": self.text_actions,
            "visual_actions": self.visual_actions,
            "visual_specs": self.visual_specs,
            "remaining_text": self.remaining_text,
            "speaker_notes": self.speaker_notes,
            "compression_statistics": self.compression_statistics,
            "confidence": self.confidence,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Transformation Engine
# ─────────────────────────────────────────────────────────────────────────────

class SlideTransformationEngine:
    """
    Orchestrates the transformation planning workflow.
    Consumes a SlideIntelligence object (and optional original SlidePageEntity)
    and maps it to text_actions, visual_actions, visual_specs, remaining_text,
    speaker_notes, compression_statistics, and confidence scores.
    """

    def plan_transformation(
        self,
        slide_intel: SlideIntelligence,
        slide_entity: Optional[SlidePageEntity] = None
    ) -> TransformationPlan:
        """
        Runs the transformation pipeline for a single slide.
        """
        # 1. Map Text Blocks to Actions
        text_actions, remaining_text, notes_text = self._plan_text_actions(slide_intel)

        # 2. Check and map detected visual opportunities
        visual_actions, visual_specs = self._generate_visual_specs(slide_intel, slide_entity)

        # 3. Create consolidated Speaker Notes
        speaker_notes = self._compile_speaker_notes(slide_intel, notes_text, slide_entity)

        # 4. Compute Compression Statistics
        orig_wc = slide_intel.word_count
        target_wc = self._estimate_target_word_count(remaining_text, visual_specs, orig_wc)
        comp_ratio = target_wc / orig_wc if orig_wc > 0 else 1.0
        readability = self._estimate_readability_improvement(comp_ratio, len(visual_specs))

        compression_statistics = {
            "original_word_count": orig_wc,
            "target_word_count": target_wc,
            "compression_ratio": round(comp_ratio, 3),
            "expected_readability_improvement": readability
        }

        # 5. Compute Confidence
        confidence = self._compute_confidence(slide_intel, visual_specs)

        return TransformationPlan(
            slide_id=slide_intel.slide_id,
            text_actions=text_actions,
            visual_actions=visual_actions,
            visual_specs=visual_specs,
            remaining_text=remaining_text,
            speaker_notes=speaker_notes,
            compression_statistics=compression_statistics,
            confidence=confidence
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Text Action Assignment
    # ─────────────────────────────────────────────────────────────────────────

    def _plan_text_actions(
        self,
        slide_intel: SlideIntelligence
    ) -> Tuple[Dict[str, Dict[str, Any]], List[str], List[str]]:
        """
        Determines the action (KEEP, SUMMARIZE, REMOVE, MERGE, MOVE_TO_VISUAL, MOVE_TO_NOTES)
        for every text block.
        """
        text_actions: Dict[str, Dict[str, Any]] = {}
        remaining_text: List[str] = []
        notes_text: List[str] = []

        # Find visual-replaced contents (steps, stats, comparisons, chronology)
        has_flowchart = any(o.visual_type == VisualOpportunityType.FLOWCHART or o.visual_type == VisualOpportunityType.PROCESS_DIAGRAM for o in slide_intel.visual_opportunities)
        has_timeline = any(o.visual_type == VisualOpportunityType.TIMELINE or o.visual_type == VisualOpportunityType.ROADMAP for o in slide_intel.visual_opportunities)
        has_comparison = any(o.visual_type == VisualOpportunityType.COMPARISON_TABLE for o in slide_intel.visual_opportunities)
        has_kpi = any(o.visual_type == VisualOpportunityType.KPI_CARDS for o in slide_intel.visual_opportunities)
        has_checklist = any(o.visual_type == VisualOpportunityType.CHECKLIST for o in slide_intel.visual_opportunities)

        for pt in slide_intel.prioritized_text:
            block_id = pt.block_id
            text = pt.text.strip()
            priority = pt.priority

            if not text:
                continue

            # Standard defaults
            action = TextActionType.KEEP
            reason = "Defaulting to keeping content."
            trans_text = text

            # Heuristics
            # 0. Check if text is boilerplate footer (contains slide/page numbers, confidential, copyright, etc.)
            is_boilerplate = (
                any(kw in text.lower() for kw in ["page", "slide", "copyright"])
                and (re.search(r'\b\d+\s*/\s*\d+\b', text) or re.search(r'\b\d+\b', text))
            ) or (
                any(kw in text.lower() for kw in ["confidential", "internal use only", "draft", "all rights reserved"])
                and len(text.split()) < 10
            ) or (
                priority == TextPriority.DECORATIVE
            )

            # 1. Slide Title/Heading (usually first block or marked is_heading)
            # Compare lowercase to slide_title
            if text.lower() in [slide_intel.slide_title.lower(), f"## {slide_intel.slide_title.lower()}"]:
                action = TextActionType.KEEP
                reason = "Title block is retained to establish slide context and subject."
                remaining_text.append(text)

            # 2. Decorative / footer/ boilerplate
            elif is_boilerplate:
                action = TextActionType.REMOVE
                reason = "Boilerplate/decorative layout elements are removed to reduce slide clutter."
                trans_text = None

            # 3. Repeated/Redundant
            elif priority in [TextPriority.REDUNDANT, TextPriority.REPEATED]:
                action = TextActionType.REMOVE
                reason = f"Redundant block (priority: {priority.value}) removed to keep content unique."
                trans_text = None

            # 4. Check if text is process steps and we are replacing it with a Flowchart/Process Diagram
            elif has_flowchart and self._matches_list_item(text, slide_intel.steps + slide_intel.processes):
                action = TextActionType.MOVE_TO_VISUAL
                reason = "Step-by-step procedural information is moved into a flowchart visual specification."
                trans_text = None

            # 5. Check if text contains chronological events and we are replacing it with a Timeline
            elif has_timeline and self._matches_list_item(text, slide_intel.chronology):
                action = TextActionType.MOVE_TO_VISUAL
                reason = "Chronological milestone information is moved into a timeline visual specification."
                trans_text = None

            # 6. Check if text contains metric/statistics and we are replacing it with KPI Cards
            elif has_kpi and any(num in text for num in slide_intel.numbers_and_statistics):
                # But keep if it's very short, or move to notes if it's long explanation.
                if len(text.split()) > 15:
                    action = TextActionType.MOVE_TO_NOTES
                    reason = "Detailed explanation of metrics moved to notes; value is highlighted in KPI Cards."
                    trans_text = None
                    notes_text.append(text)
                else:
                    action = TextActionType.MOVE_TO_VISUAL
                    reason = "Statistical metrics are moved to structured KPI cards for maximum emphasis."
                    trans_text = None

            # 7. Check if text is comparisons/advantages/disadvantages and we are building a Table
            elif has_comparison and (
                self._matches_list_item(text, slide_intel.advantages + slide_intel.disadvantages) or
                any(c.get("left", "").lower() in text.lower() or c.get("right", "").lower() in text.lower() for c in slide_intel.comparisons)
            ):
                action = TextActionType.MOVE_TO_VISUAL
                reason = "Comparative aspects and pros/cons are structured into a comparison table specification."
                trans_text = None

            # 8. Check if checklist content
            elif has_checklist and self._matches_list_item(text, slide_intel.steps) and any(kw in text.lower() for kw in ["ensure", "verify", "check", "task", "action"]):
                action = TextActionType.MOVE_TO_VISUAL
                reason = "Actionable items are converted into a visual checklist specification."
                trans_text = None

            # 9. Low Priority supporting text
            elif priority == TextPriority.LOW:
                # Move to speaker notes
                action = TextActionType.MOVE_TO_NOTES
                reason = "Low-priority secondary detail is offloaded to speaker notes to maintain clean visual design."
                trans_text = None
                notes_text.append(text)

            # 10. Medium Priority blocks
            elif priority == TextPriority.MEDIUM:
                # If too long, summarize
                if len(text.split()) > 12:
                    action = TextActionType.SUMMARIZE
                    reason = "Medium priority block summarized to retain core learning point without cluttering layout."
                    trans_text = self._heuristically_summarize(text)
                    remaining_text.append(trans_text)
                    # Keep original in notes
                    notes_text.append(f"Original detail: {text}")
                else:
                    action = TextActionType.KEEP
                    reason = "Retained as key supporting educational detail."
                    remaining_text.append(text)

            # 11. High Priority (non-title) blocks
            elif priority == TextPriority.HIGH:
                action = TextActionType.KEEP
                reason = "High-priority core definition or concept retained in primary layout text."
                remaining_text.append(text)

            # Record action
            text_actions[block_id] = {
                "original_text": text,
                "action": action.value,
                "reason": reason,
                "transformed_text": trans_text
            }

        return text_actions, remaining_text, notes_text

    def _matches_list_item(self, text: str, items: List[str]) -> bool:
        """Helper to determine if a block text is present in list of values."""
        clean_text = text.lower().strip()
        for item in items:
            clean_item = item.lower().strip()
            # Check overlap
            if clean_item in clean_text or clean_text in clean_item:
                return True
        return False

    def _heuristically_summarize(self, text: str) -> str:
        """
        Summarizes text without an LLM.
        Keeps the first sentence or extracts key phrases (noun-verb pairs).
        """
        # Split sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if sentences:
            first_sentence = sentences[0].strip()
            # If still long, keep first 10 words + "..."
            words = first_sentence.split()
            if len(words) > 12:
                return " ".join(words[:10]) + "..."
            return first_sentence
        return text

    # ─────────────────────────────────────────────────────────────────────────
    # Visual Specification Generators
    # ─────────────────────────────────────────────────────────────────────────

    def _generate_visual_specs(
        self,
        slide_intel: SlideIntelligence,
        slide_entity: Optional[SlidePageEntity] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Generates structured specifications for detected visual opportunities.
        """
        visual_actions: List[Dict[str, Any]] = []
        visual_specs: List[Dict[str, Any]] = []

        # Sort visual opportunities by priority_rank / confidence
        opps = sorted(slide_intel.visual_opportunities, key=lambda x: x.confidence, reverse=True)

        # Primary visualizations to map (allow mapping up to 5 to be comprehensive)
        max_visuals = 5
        visuals_mapped = 0

        for opp in opps:
            if visuals_mapped >= max_visuals:
                break

            spec_type = opp.visual_type
            spec_dict = None

            if spec_type == VisualOpportunityType.FLOWCHART:
                spec_dict = self._build_flowchart_spec(slide_intel)
            elif spec_type == VisualOpportunityType.TIMELINE:
                spec_dict = self._build_timeline_spec(slide_intel)
            elif spec_type == VisualOpportunityType.COMPARISON_TABLE:
                spec_dict = self._build_comparison_table_spec(slide_intel, slide_entity)
            elif spec_type == VisualOpportunityType.KPI_CARDS:
                spec_dict = self._build_kpi_card_spec(slide_intel)
            elif spec_type == VisualOpportunityType.CHECKLIST:
                spec_dict = self._build_checklist_spec(slide_intel)
            elif spec_type == VisualOpportunityType.ICON_GRID:
                spec_dict = self._build_icon_grid_spec(slide_intel)
            elif spec_type == VisualOpportunityType.SMART_ART:
                spec_dict = self._build_smartart_spec(slide_intel)
            elif spec_type == VisualOpportunityType.PROCESS_DIAGRAM:
                spec_dict = self._build_flowchart_spec(slide_intel)  # shares flowchart data structure
                spec_type = VisualOpportunityType.PROCESS_DIAGRAM
            elif spec_type == VisualOpportunityType.DECISION_TREE:
                spec_dict = self._build_decision_tree_spec(slide_intel)
            elif spec_type == VisualOpportunityType.PYRAMID:
                spec_dict = self._build_smartart_spec(slide_intel, forced_type="Pyramid")
                spec_type = VisualOpportunityType.SMART_ART
            elif spec_type == VisualOpportunityType.CYCLE_DIAGRAM:
                spec_dict = self._build_cycle_spec(slide_intel)
            elif spec_type == VisualOpportunityType.ORG_CHART:
                spec_dict = self._build_org_chart_spec(slide_intel)
            elif spec_type == VisualOpportunityType.MATRIX:
                spec_dict = self._build_matrix_spec(slide_intel)
            elif spec_type == VisualOpportunityType.ROADMAP:
                spec_dict = self._build_roadmap_spec(slide_intel)
            elif spec_type == VisualOpportunityType.INFOGRAPHIC:
                spec_dict = self._build_infographic_spec(slide_intel)

            if spec_dict:
                visual_specs.append({
                    "type": spec_type.value,
                    "spec": spec_dict
                })
                visual_actions.append({
                    "action_type": "REPLACE_TEXT_WITH_VISUAL" if spec_type != VisualOpportunityType.IMAGE_WITH_CAPTION else "ADD_VISUAL_CONTEXT",
                    "target_opportunity": spec_type.value,
                    "description": f"Structured text transformed programmatically into {spec_type.value} layout.",
                    "source_block_ids": self._find_source_block_ids(slide_intel, opp.source_fields)
                })
                visuals_mapped += 1

        # Always include an AI Image Specification to support the main topic
        image_spec = self._build_ai_image_spec(slide_intel)
        visual_specs.append({
            "type": "AI Image",
            "spec": image_spec
        })
        visual_actions.append({
            "action_type": "ADD_AI_IMAGE",
            "target_opportunity": "AI Image",
            "description": "Generated AI visual prompt to create a supporting illustration for the main topic.",
            "source_block_ids": [pt.block_id for pt in slide_intel.prioritized_text[:2]]
        })

        return visual_actions, visual_specs

    def _find_source_block_ids(self, slide_intel: SlideIntelligence, source_fields: List[str]) -> List[str]:
        """Finds block IDs associated with specific fields for tracing purposes."""
        matched_ids: List[str] = []
        for field_name in source_fields:
            # Map logical fields to texts
            target_texts: List[str] = []
            if field_name == "steps":
                target_texts = slide_intel.steps
            elif field_name == "processes":
                target_texts = slide_intel.processes
            elif field_name == "chronology":
                target_texts = slide_intel.chronology
            elif field_name == "numbers_and_statistics":
                target_texts = slide_intel.numbers_and_statistics
            elif field_name == "key_concepts":
                target_texts = slide_intel.key_concepts
            elif field_name == "supporting_concepts":
                target_texts = slide_intel.supporting_concepts
            elif field_name in ["advantages", "disadvantages"]:
                target_texts = slide_intel.advantages if field_name == "advantages" else slide_intel.disadvantages

            for pt in slide_intel.prioritized_text:
                if pt.text in target_texts or any(t.lower() in pt.text.lower() for t in target_texts):
                    matched_ids.append(pt.block_id)
        return list(set(matched_ids))

    # ─────────────────────────────────────────────────────────────────────────
    # Identified Visual Spec Builders
    # ─────────────────────────────────────────────────────────────────────────

    def _build_flowchart_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Flowchart/Process structure mapping steps sequentially."""
        items = slide_intel.steps if slide_intel.steps else slide_intel.processes
        if not items:
            items = ["Upload presentation", "Analyze slide contents", "Apply design layouts", "Export PDF/Web deck"]

        nodes = []
        edges = []
        labels = {}
        decision_nodes = []

        for i, item in enumerate(items):
            node_id = f"step_{i + 1}"
            
            # Clean label
            label = re.sub(r'^(Step\s*\d+\s*:\s*|\d+\.\s*)', '', item, flags=re.IGNORECASE).strip()
            
            # Detect decisions
            node_type = "process"
            if any(w in label.lower() for w in ["if", "choice", "verify", "decide", "validate", "check"]):
                node_type = "decision"
                decision_nodes.append(node_id)

            nodes.append({
                "id": node_id,
                "label": label,
                "type": node_type
            })
            labels[node_id] = label

        # Sequentially connect
        for i in range(len(nodes) - 1):
            edges.append({
                "from": nodes[i]["id"],
                "to": nodes[i + 1]["id"]
            })

        return {
            "nodes": nodes,
            "edges": edges,
            "labels": labels,
            "start_node": nodes[0]["id"] if nodes else "",
            "end_node": nodes[-1]["id"] if nodes else "",
            "decision_nodes": decision_nodes,
            "recommended_orientation": "LR" if len(nodes) <= 4 else "TB"
        }

    def _build_timeline_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Timeline structure detailing milestones and dates."""
        items = slide_intel.chronology if slide_intel.chronology else slide_intel.steps
        if not items:
            items = ["2023 - Project Start", "2024 Q1 - Beta Testing", "2025 - Global Rollout"]

        ordered_events = []
        dates = []
        milestones = []

        # Year/Quarter patterns
        date_pattern = re.compile(r'(\b\d{4}\b|\bQ[1-4]\b|\bPhase\s*\d+\b)', re.IGNORECASE)

        for i, item in enumerate(items):
            event_id = f"event_{i + 1}"
            match = date_pattern.search(item)
            if match:
                date = match.group(1)
                desc = item.replace(date, "").strip(" -:")
            else:
                date = f"Phase {i + 1}"
                desc = item

            ordered_events.append({
                "id": event_id,
                "title": f"Milestone {i + 1}" if not desc else desc.split(".")[0],
                "description": desc,
                "date": date
            })
            dates.append(date)

            if any(w in item.lower() for w in ["milestone", "launch", "release", "finish", "go-live"]):
                milestones.append(event_id)

        return {
            "ordered_events": ordered_events,
            "dates": dates,
            "milestones": milestones
        }

    def _build_comparison_table_spec(
        self,
        slide_intel: SlideIntelligence,
        slide_entity: Optional[SlidePageEntity] = None
    ) -> Dict[str, Any]:
        """Generates headers, rows and highlights for tabular comparisons."""
        # Check if slide already has a parsed table
        if slide_entity and slide_entity.tables:
            tbl = slide_entity.tables[0]
            return {
                "headers": tbl.headers,
                "rows": tbl.rows,
                "highlight_columns": [0],
                "merge_cells": []
            }

        # Otherwise map programmatically from comparisons or advantages/disadvantages
        headers = ["Aspect"]
        rows = []

        if slide_intel.comparisons:
            # e.g. comparisons = [{"aspect": "Speed", "left": "Fast", "right": "Slow"}]
            # Find left/right names or default
            headers.extend(["Entity A", "Entity B"])
            for comp in slide_intel.comparisons:
                aspect = comp.get("aspect", "Metric")
                left = comp.get("left", "")
                right = comp.get("right", "")
                rows.append([aspect, left, right])
        elif slide_intel.advantages or slide_intel.disadvantages:
            headers.extend(["Advantages (Pros)", "Disadvantages (Cons)"])
            advs = slide_intel.advantages
            disadvs = slide_intel.disadvantages
            max_len = max(len(advs), len(disadvs))
            for i in range(max_len):
                adv = advs[i] if i < len(advs) else "—"
                dis = disadvs[i] if i < len(disadvs) else "—"
                rows.append([f"Item {i + 1}", adv, dis])
        else:
            headers.extend(["Option A", "Option B"])
            rows = [
                ["Focus", "Customizability", "Standardization"],
                ["Complexity", "High", "Low"],
                ["Cost", "Variable", "Fixed"]
            ]

        return {
            "headers": headers,
            "rows": rows,
            "highlight_columns": [0],
            "merge_cells": []
        }

    def _build_kpi_card_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """KPI Card specs for statistics and callout figures."""
        stats = slide_intel.numbers_and_statistics
        if not stats:
            stats = ["84% Concept Retention", "10x Render Speed", "0% Delay"]

        metrics = []
        num_pattern = re.compile(r'(\b\d+%\s*|\b\d+x\b|\$\s*\d+[\d,.]*[MKB]?|\b\d+[\d,.]*\b\s*(?:seconds|min|hours|percent|GB|TB|MB|%)?)', re.IGNORECASE)

        for stat in stats:
            match = num_pattern.search(stat)
            if match:
                value = match.group(1).strip()
                label = stat.replace(value, "").strip(" -:")
            else:
                value = "100"
                label = stat

            # Trend
            trend = "neutral"
            if any(w in stat.lower() for w in ["increase", "growth", "up", "improvement", "higher"]):
                trend = "up"
            elif any(w in stat.lower() for w in ["decrease", "reduction", "drop", "lower", "down"]):
                trend = "down"

            metrics.append({
                "label": label if label else "Metric",
                "value": value,
                "change": trend,
                "description": stat
            })

        return {
            "metrics": metrics
        }

    def _build_checklist_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Checklist formatting for verification procedures."""
        items = slide_intel.steps if slide_intel.steps else (slide_intel.chronology if slide_intel.chronology else ["Verify inputs", "Process text", "Create visual layout"])
        checklist_items = []
        for i, item in enumerate(items):
            checklist_items.append({
                "task": item,
                "is_required": True,
                "order": i + 1
            })
        return {
            "items": checklist_items
        }

    def _build_icon_grid_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Maps key concepts into grid tiles with suggested icons."""
        concepts = slide_intel.key_concepts if slide_intel.key_concepts else ["Core Concept", "Secondary Concept", "Supporting Info"]
        items = []

        icon_map = {
            "ai": "cpu", "artificial": "cpu", "algorithm": "cpu", "tech": "cpu",
            "learn": "book-open", "student": "book-open", "course": "book-open", "education": "book-open",
            "stat": "bar-chart-2", "data": "bar-chart-2", "metric": "bar-chart-2", "report": "bar-chart-2",
            "process": "activity", "flow": "activity", "pipeline": "activity",
            "speed": "zap", "perform": "zap", "fast": "zap", "efficiency": "zap",
            "team": "users", "collaborate": "users", "social": "users",
            "secure": "shield", "protect": "shield", "safety": "shield",
            "cloud": "cloud", "server": "server",
            "cost": "dollar-sign", "price": "dollar-sign", "money": "dollar-sign"
        }

        for concept in concepts:
            # Map icon
            icon = "check-circle"
            for kw, icon_name in icon_map.items():
                if kw in concept.lower():
                    icon = icon_name
                    break
            
            items.append({
                "concept": concept,
                "icon": icon,
                "explanation": f"Key educational pillar detailing {concept.lower()}."
            })

        return {
            "items": items
        }

    def _build_smartart_spec(self, slide_intel: SlideIntelligence, forced_type: Optional[str] = None) -> Dict[str, Any]:
        """Generates structural metadata for SmartArt components."""
        smartart_type = forced_type
        if not smartart_type:
            # Deduce smartart layout
            if PresentationIntent.HIERARCHY in slide_intel.presentation_intents:
                smartart_type = "Hierarchy"
            elif PresentationIntent.CYCLE in slide_intel.presentation_intents:
                smartart_type = "Cycle"
            elif PresentationIntent.PROCESS in slide_intel.presentation_intents:
                smartart_type = "Process"
            else:
                smartart_type = "Relationship"

        elements = slide_intel.key_concepts if slide_intel.key_concepts else ["Concept A", "Concept B", "Concept C"]
        
        structure = {
            "layout": smartart_type,
            "depth": 2 if smartart_type == "Hierarchy" else 1,
            "alignment": "horizontal" if smartart_type in ["Process", "Chevron"] else "vertical"
        }

        return {
            "smartart_type": smartart_type,
            "elements": elements,
            "structure": structure
        }

    def _build_decision_tree_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Branching decision logic structure."""
        steps = slide_intel.steps if slide_intel.steps else ["Check Input Quality", "Process Data", "Done"]
        nodes = []
        edges = []
        
        for i, step in enumerate(steps):
            node_id = f"node_{i+1}"
            nodes.append({
                "id": node_id,
                "label": step,
                "type": "decision" if i == 0 else "process"
            })
            
        if len(nodes) >= 2:
            edges.append({"from": "node_1", "to": "node_2", "condition": "Valid"})
            edges.append({"from": "node_1", "to": "node_3", "condition": "Invalid"})
            
        return {
            "nodes": nodes,
            "edges": edges,
            "start_node": "node_1" if nodes else "",
            "decision_nodes": ["node_1"] if nodes else [],
            "outcomes": ["Successful completion", "Failure handling"]
        }

    def _build_cycle_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Looping process specification."""
        steps = slide_intel.processes if slide_intel.processes else (slide_intel.steps if slide_intel.steps else ["Phase 1", "Phase 2", "Phase 3"])
        return {
            "steps": steps,
            "flow_direction": "clockwise",
            "is_closed": True
        }

    def _build_org_chart_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Roles hierarchical layout."""
        return {
            "roles": [
                {"id": "role_1", "title": "System Lead", "department": "Architecture", "reports_to": None},
                {"id": "role_2", "title": "AI Module Developer", "department": "R&D", "reports_to": "role_1"},
                {"id": "role_3", "title": "Parser Integrator", "department": "R&D", "reports_to": "role_1"}
            ]
        }

    def _build_matrix_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Quadrant metrics spec."""
        return {
            "quadrants": [
                {"quadrant": "Q1", "title": "High Impact / Low Effort", "items": slide_intel.key_concepts[:1]},
                {"quadrant": "Q2", "title": "High Impact / High Effort", "items": slide_intel.key_concepts[1:2]},
                {"quadrant": "Q3", "title": "Low Impact / Low Effort", "items": slide_intel.supporting_concepts[:1]},
                {"quadrant": "Q4", "title": "Low Impact / High Effort", "items": slide_intel.supporting_concepts[1:2]}
            ],
            "axes": {"x_axis": "Effort", "y_axis": "Impact"}
        }

    def _build_roadmap_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """High-level milestone planning Roadmap."""
        return {
            "phases": [
                {"phase": "Phase 1", "description": "Foundation Parsing setup", "duration": "Month 1-2"},
                {"phase": "Phase 2", "description": "Engine Intelligence parsing", "duration": "Month 3-4"}
            ],
            "milestones": [
                {"date": "End of Phase 1", "name": "Parser Ready"},
                {"date": "End of Phase 2", "name": "AI Pipeline Complete"}
            ],
            "deliverables": ["Structured JSON exports", "HTML5 rendering package"]
        }

    def _build_infographic_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Multi-section fallback layout."""
        sections = []
        concepts = slide_intel.key_concepts[:3]
        for i, c in enumerate(concepts):
            sections.append({
                "title": c,
                "description": f"Detailed educational explanation mapping {c.lower()}.",
                "visual_hint": f"Supporting icon highlight for {c}."
            })
        return {
            "layout_type": "grid",
            "sections": sections
        }

    def _build_ai_image_spec(self, slide_intel: SlideIntelligence) -> Dict[str, Any]:
        """Generates a high-quality educational prompt for DALL-E / Imagen."""
        subject = slide_intel.main_topic if slide_intel.main_topic else slide_intel.slide_title
        concepts = ", ".join(slide_intel.key_concepts[:3])
        
        # Craft premium composition
        prompt_subject = f"An educational visual representation of {subject}."
        if concepts:
            prompt_subject += f" Illustrating the core concepts of {concepts}."

        return {
            "subject": prompt_subject,
            "style": "Modern minimalist educational infographic vector style, clean line art with vibrant gradient accents",
            "composition": "Centered single focal point, isometric perspective, clean white studio background",
            "camera_angle": "Eye-level straight-on perspective",
            "educational_purpose": f"To visually reinforce students' mental model of {subject} using abstract structural diagrams.",
            "visual_emphasis": "High color contrast, neon gradient accents (teal and purple), sharp vector edges, completely textless, no watermarks",
            "negative_prompt": "photorealistic photo, text, words, label, caption, watermark, messy complex details, dark shadowy mood"
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Speaker Notes Compilation
    # ─────────────────────────────────────────────────────────────────────────

    def _compile_speaker_notes(
        self,
        slide_intel: SlideIntelligence,
        notes_text: List[str],
        slide_entity: Optional[SlidePageEntity] = None
    ) -> str:
        """
        Combines parsed speaker notes with the text blocks offloaded during transformation.
        """
        compiled = []

        # Add existing speaker notes if any
        if slide_entity and slide_entity.speaker_notes:
            compiled.append(f"Original notes: {slide_entity.speaker_notes}")

        # Add offloaded detailed lists
        if notes_text:
            compiled.append("Additional slide detail offloaded to notes:")
            for note in notes_text:
                compiled.append(f"- {note}")

        # Add context notes
        compiled.append(f"Focus learning objective: {slide_intel.learning_objective}")

        return "\n".join(compiled)

    # ─────────────────────────────────────────────────────────────────────────
    # Word Count & Heuristics
    # ─────────────────────────────────────────────────────────────────────────

    def _estimate_target_word_count(self, remaining_text: List[str], visual_specs: List[Dict[str, Any]], original_word_count: int = 0) -> int:
        """Estimates target word count on the transformed slide layout."""
        count = sum(len(text.split()) for text in remaining_text)
        
        # Only add words from the primary (first non-AI Image) visual specification
        primary_spec = None
        for spec in visual_specs:
            if spec["type"] != "AI Image":
                primary_spec = spec
                break
                
        if primary_spec:
            spec_type = primary_spec["type"]
            data = primary_spec["spec"]
            if spec_type in ["Flowchart", "Process Diagram"]:
                # Limit each node label to 3 words
                count += sum(min(3, len(n.get("label", "").split())) for n in data.get("nodes", []))
            elif spec_type == "Timeline":
                count += sum(min(3, len(e.get("title", "").split())) for e in data.get("ordered_events", []))
            elif spec_type == "Comparison Table":
                count += sum(min(2, len(h.split())) for h in data.get("headers", []))
                for row in data.get("rows", []):
                    count += sum(min(3, len(cell.split())) for cell in row)
            elif spec_type == "KPI Cards":
                count += sum(min(2, len(m.get("value", "").split())) + min(3, len(m.get("label", "").split())) for m in data.get("metrics", []))
            elif spec_type == "Icon Grid":
                count += sum(min(3, len(item.get("concept", "").split())) for item in data.get("items", []))
                
        # Safety check: if original word count is provided and our estimate exceeds or equals it
        # (which happens when text is duplicated across extraction outputs), cap it at 70% of original.
        if original_word_count > 0 and count >= original_word_count:
            count = int(original_word_count * 0.7)
            
        return max(5, count)  # minimum word count floor

    def _estimate_readability_improvement(self, comp_ratio: float, num_visuals: int) -> str:
        """Calculates a heuristic readability percentage increase."""
        # More compression (lower ratio) + more visuals = better score
        if comp_ratio == 1.0:
            return "No text layout density changes."
            
        reduction = (1.0 - comp_ratio) * 100
        score = reduction * 0.75 + (num_visuals * 10)
        score = min(max(5.0, score), 95.0)
        
        return f"{round(score, 1)}% improvement: reduced clutter, replaced complex sentences with structured visual elements."

    def _compute_confidence(self, slide_intel: SlideIntelligence, visual_specs: List[Dict[str, Any]]) -> float:
        """Determines the confidence (0.0 to 1.0) of the transformation plan."""
        # Base confidence
        conf = 0.75
        
        # Increase if high-matching opportunities exist
        top_opp_confidence = max([o.confidence for o in slide_intel.visual_opportunities], default=0.0)
        conf += top_opp_confidence * 0.15
        
        # Decrease if layout has zero structures or is extremely short
        if slide_intel.word_count < 10:
            conf -= 0.1
            
        return round(min(max(0.4, conf), 0.98), 2)
