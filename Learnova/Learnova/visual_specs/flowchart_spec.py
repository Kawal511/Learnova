"""
Learnova Visual Specification Engine — Flowchart & Process Diagram Builder
===========================================================================
Deterministic builder for Flowchart and Process Diagram visual specifications.
Input: SlideIntelligence (steps, processes)
Output: FlowchartSpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from intelligence.schema import SlideIntelligence
from visual_specs.schema import FlowchartEdge, FlowchartNode, FlowchartSpec

# Keywords that indicate a decision/branch node
_DECISION_KEYWORDS = frozenset([
    "if", "whether", "verify", "validate", "check", "decide", "choose",
    "compare", "evaluate", "test", "confirm", "else", "otherwise",
])

_STEP_PREFIX_RE = re.compile(
    r"^(Step\s*\d+\s*[:\-]?\s*|\d+[\.\)]\s*)", re.IGNORECASE
)


def build_flowchart_spec(intel: SlideIntelligence) -> FlowchartSpec:
    """
    Build a Flowchart or Process Diagram specification from SlideIntelligence.

    Uses `steps` first, falls back to `processes`, then key_concepts as placeholder nodes.

    Args:
        intel: SlideIntelligence object.

    Returns:
        FlowchartSpec with nodes, edges, labels, orientation, start/end node.
    """
    source_items = _pick_source(intel)

    nodes: List[FlowchartNode] = []
    edges: List[FlowchartEdge] = []
    labels: Dict[str, str] = {}
    decision_nodes: List[str] = []

    for i, item in enumerate(source_items):
        node_id = f"step_{i + 1}"
        label = _clean_label(item)
        node_type = _classify_node(label, i, len(source_items))

        nodes.append(FlowchartNode(id=node_id, label=label, node_type=node_type))
        labels[node_id] = label

        if node_type == "decision":
            decision_nodes.append(node_id)

    # Sequential edges (simple process flow)
    for i in range(len(nodes) - 1):
        condition = ""
        if nodes[i].node_type == "decision":
            condition = "Yes"
        edges.append(FlowchartEdge(
            from_node=nodes[i].id,
            to_node=nodes[i + 1].id,
            condition=condition,
        ))

    # Add "No" fallback edge from first decision node (if any)
    if decision_nodes and len(nodes) >= 3:
        edges.append(FlowchartEdge(
            from_node=decision_nodes[0],
            to_node=nodes[-1].id,
            condition="No",
        ))

    orientation = "LR" if len(nodes) <= 4 else "TB"

    return FlowchartSpec(
        nodes=nodes,
        edges=edges,
        labels=labels,
        orientation=orientation,
        start_node=nodes[0].id if nodes else "",
        end_node=nodes[-1].id if nodes else "",
        decision_nodes=decision_nodes,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_source(intel: SlideIntelligence) -> List[str]:
    """Choose the best source list for flowchart nodes."""
    if intel.steps:
        return intel.steps[:8]
    if intel.processes:
        return intel.processes[:8]
    # Fallback — key concepts as sequential nodes
    if intel.key_concepts:
        return intel.key_concepts[:6]
    return [f"Phase {i + 1}" for i in range(3)]


def _clean_label(text: str) -> str:
    """Strip step prefixes like 'Step 1:', '1.', '2)' from node labels."""
    label = _STEP_PREFIX_RE.sub("", text).strip()
    # Truncate very long labels to keep diagrams readable
    words = label.split()
    if len(words) > 8:
        label = " ".join(words[:7]) + "…"
    return label


def _classify_node(label: str, index: int, total: int) -> str:
    """Classify a node as start, end, decision, or process."""
    if index == 0:
        return "start"
    if index == total - 1:
        return "end"
    lower = label.lower()
    if any(kw in lower for kw in _DECISION_KEYWORDS):
        return "decision"
    return "process"
