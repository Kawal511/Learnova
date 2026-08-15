"""
Learnova Visual Specification Engine — Table, Matrix, Decision Tree & Org Chart Builder
=========================================================================================
Deterministic builder for:
  - Comparison Table (comparisons, advantages/disadvantages)
  - Matrix (quadrant from key_concepts × supporting_concepts)
  - Decision Tree (steps with branching logic)
  - Organization Chart (hierarchy from information_hierarchy)

Output: TableSpec (for tables/matrices/org charts)

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from learnova.parsers.schema import SlidePageEntity
from learnova.intelligence.schema import SlideIntelligence
from learnova.visual_specs.schema import TableSpec


def build_comparison_table_spec(
    intel: SlideIntelligence,
    slide_entity: Optional[SlidePageEntity] = None,
) -> TableSpec:
    """
    Build a Comparison Table spec from SlideIntelligence.

    Priority:
    1. Use parsed table from SlidePageEntity (if available)
    2. Map intel.comparisons → Aspect / Entity A / Entity B
    3. Map advantages / disadvantages → Pros / Cons
    4. Fallback generic placeholder

    Returns:
        TableSpec with headers, rows, highlight_columns, highlighted_cells.
    """
    # 1. Use an already-parsed table
    if slide_entity and slide_entity.tables:
        tbl = slide_entity.tables[0]
        highlighted_cells = _detect_highlighted_cells(tbl.rows)
        return TableSpec(
            headers=list(tbl.headers) if tbl.headers else [],
            rows=[list(r) for r in tbl.rows] if tbl.rows else [],
            highlight_columns=[0],
            highlighted_cells=highlighted_cells,
        )

    headers: List[str] = []
    rows: List[List[str]] = []

    # 2. Structured comparisons
    if intel.comparisons:
        headers = ["Aspect", "Option A", "Option B"]
        for comp in intel.comparisons:
            aspect = comp.get("aspect", comp.get("left", "—"))[:40]
            left   = comp.get("left", "—")[:50]
            right  = comp.get("right", "—")[:50]
            rows.append([aspect, left, right])

    # 3. Advantages / Disadvantages
    elif intel.advantages or intel.disadvantages:
        headers = ["#", "Advantages (Pros)", "Disadvantages (Cons)"]
        max_len = max(len(intel.advantages), len(intel.disadvantages), 1)
        for i in range(max_len):
            adv  = intel.advantages[i]  if i < len(intel.advantages)    else "—"
            dis  = intel.disadvantages[i] if i < len(intel.disadvantages) else "—"
            rows.append([str(i + 1), adv[:60], dis[:60]])

    # 4. Fallback — key_concepts as rows
    elif intel.key_concepts:
        headers = ["Concept", "Description", "Relevance"]
        for i, concept in enumerate(intel.key_concepts[:6]):
            defn = intel.definitions.get(concept, "")[:60] or "—"
            rows.append([concept, defn, intel.complexity_level.value])

    else:
        headers = ["Feature", "Option A", "Option B"]
        rows = [
            ["Complexity", "Low", "High"],
            ["Speed", "Fast", "Slow"],
            ["Cost", "Variable", "Fixed"],
        ]

    highlighted_cells = _detect_highlighted_cells(rows)
    return TableSpec(
        headers=headers,
        rows=rows,
        highlight_columns=[0],
        highlighted_cells=highlighted_cells,
    )


def build_matrix_spec(intel: SlideIntelligence) -> TableSpec:
    """
    Build a 2×2 Matrix (quadrant) spec.
    X axis = Effort, Y axis = Impact.
    Cells sourced from key_concepts and supporting_concepts.
    """
    kc = (intel.key_concepts + ["—"] * 4)[:4]
    sc = (intel.supporting_concepts + ["—"] * 4)[:4]

    headers = ["", "Low Effort", "High Effort"]
    rows = [
        ["High Impact", kc[0], kc[1]],
        ["Low Impact",  sc[0], sc[1]],
    ]
    return TableSpec(
        headers=headers,
        rows=rows,
        highlight_columns=[],
        highlighted_cells=[{"row": 0, "col": 1}],
    )


def build_decision_tree_spec(intel: SlideIntelligence) -> TableSpec:
    """
    Build a Decision Tree as a structured table spec.
    Rows represent decision paths with conditions and outcomes.
    """
    steps = intel.steps if intel.steps else intel.processes
    if not steps:
        steps = ["Input", "Check", "Process", "Output"]

    headers = ["Step", "Condition", "Yes Path", "No Path"]
    rows: List[List[str]] = []

    for i, step in enumerate(steps[:6]):
        cond    = "Valid?" if i == 0 else "Complete?"
        yes_out = steps[i + 1][:40] if i + 1 < len(steps) else "Continue"
        no_out  = "Retry / Error handling"
        rows.append([step[:40], cond, yes_out, no_out])

    return TableSpec(
        headers=headers,
        rows=rows,
        highlight_columns=[0],
        highlighted_cells=[{"row": 0, "col": 0}],
    )


def build_org_chart_spec(intel: SlideIntelligence) -> TableSpec:
    """
    Build an Org Chart as a table spec (id, title, reports_to columns).
    Derived from information_hierarchy or key_concepts.
    """
    hierarchy = intel.information_hierarchy
    root  = hierarchy.get("level_1_topic", intel.main_topic or "Root")
    l2    = hierarchy.get("level_2_key_concepts", intel.key_concepts[:3])
    l3    = hierarchy.get("level_3_supporting", intel.supporting_concepts[:3])

    headers = ["ID", "Title", "Department", "Reports To"]
    rows: List[List[str]] = [["role_0", root[:40], "Leadership", "—"]]

    for i, concept in enumerate(l2[:4]):
        rows.append([f"role_1_{i}", concept[:40], "Core", "role_0"])

    for i, concept in enumerate(l3[:4]):
        parent_id = f"role_1_{i % max(len(l2), 1)}"
        rows.append([f"role_2_{i}", concept[:40], "Support", parent_id])

    return TableSpec(
        headers=headers,
        rows=rows,
        highlight_columns=[0],
        highlighted_cells=[{"row": 0, "col": 0}],
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _detect_highlighted_cells(rows: List[List[Any]]) -> List[Dict[str, int]]:
    """Highlight first column of each row (usually the label/aspect column)."""
    return [{"row": i, "col": 0} for i in range(min(len(rows), 10))]
