"""
Learnova Visual Specification Engine — Graph / Chart Builder
=============================================================
Deterministic builder for Graph visual specifications.
Extracts numeric values and labels from numbers_and_statistics and formulas.

Supported chart types: bar, line, pie, scatter, radar
Output: GraphSpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from learnova.intelligence.schema import SlideIntelligence
from learnova.visual_specs.schema import GraphSeries, GraphSpec

# Regex to find numeric values (integers, decimals, percentages)
_NUM_RE = re.compile(
    r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*%)?|\d+\.\d+|\d+)",
    re.IGNORECASE,
)

# Regex to strip units for clean labels
_UNIT_RE = re.compile(
    r"\b(percent|%|seconds|sec|ms|GB|TB|MB|KB|kg|km|m|°C|°F|USD|\$|€|£|x)\b",
    re.IGNORECASE,
)

_CHART_TYPE_SIGNALS = {
    "bar":     ["distribution", "comparison", "count", "frequency", "volume"],
    "line":    ["trend", "growth", "over time", "change", "rate", "timeline"],
    "pie":     ["proportion", "share", "percentage", "breakdown", "composition"],
    "radar":   ["performance", "skills", "attributes", "score", "dimensions"],
    "scatter": ["correlation", "relationship", "vs", "against", "plot"],
}


def build_graph_spec(intel: SlideIntelligence) -> GraphSpec:
    """
    Build a Graph specification from SlideIntelligence.

    Extracts numeric values from numbers_and_statistics.
    Infers chart type from content signals.
    Falls back to a bar chart of key_concepts with placeholder values.

    Args:
        intel: SlideIntelligence object.

    Returns:
        GraphSpec with chart_type, title, axes, and series.
    """
    stats = intel.numbers_and_statistics

    chart_type = _infer_chart_type(intel)
    title      = _build_title(intel)
    x_axis, y_axis = _infer_axes(intel, chart_type)

    if stats:
        series = _extract_series_from_stats(stats)
    else:
        series = _build_placeholder_series(intel)

    return GraphSpec(
        chart_type=chart_type,
        title=title,
        x_axis=x_axis,
        y_axis=y_axis,
        series=series,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _infer_chart_type(intel: SlideIntelligence) -> str:
    """Infer the most appropriate chart type from content signals."""
    combined = " ".join([
        intel.main_topic,
        intel.learning_objective,
        " ".join(intel.key_concepts),
        " ".join(intel.numbers_and_statistics),
        " ".join(intel.chronology),
    ]).lower()

    # Score each chart type
    scores = {ct: 0 for ct in _CHART_TYPE_SIGNALS}
    for ct, signals in _CHART_TYPE_SIGNALS.items():
        for sig in signals:
            if sig in combined:
                scores[ct] += 1

    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "bar"


def _build_title(intel: SlideIntelligence) -> str:
    topic = intel.main_topic or intel.slide_title
    return f"Statistical Overview: {topic}" if topic else "Data Summary"


def _infer_axes(intel: SlideIntelligence, chart_type: str) -> Tuple[str, str]:
    """Infer axis labels from content and chart type."""
    if chart_type == "line":
        x = "Time Period"
        y = "Value"
        if intel.chronology:
            x = "Timeline"
    elif chart_type == "pie":
        x = "Category"
        y = "Proportion (%)"
    elif chart_type == "scatter":
        x = "Variable A"
        y = "Variable B"
    elif chart_type == "radar":
        x = "Dimension"
        y = "Score"
    else:
        x = "Category"
        y = "Value"

    return x, y


def _extract_series_from_stats(stats: List[str]) -> List[GraphSeries]:
    """Parse numeric values from statistics strings into series data."""
    labels: List[str] = []
    values: List[float] = []

    for stat in stats[:10]:
        nums = _NUM_RE.findall(stat)
        if not nums:
            continue
        # Use last numeric match as the value (most specific)
        raw_val = nums[-1].replace(",", "").replace("%", "").strip()
        try:
            val = float(raw_val)
        except ValueError:
            continue

        # Label = stat with numeric stripped
        label = _NUM_RE.sub("", stat).strip(" -:—|")
        label = _UNIT_RE.sub("", label).strip()
        label = " ".join(label.split())[:30] or f"Metric {len(values) + 1}"

        labels.append(label)
        values.append(val)

    if not values:
        return [GraphSeries(name="Data", values=[0.0])]

    return [GraphSeries(name="Series 1", values=values)]


def _build_placeholder_series(intel: SlideIntelligence) -> List[GraphSeries]:
    """Build placeholder series from key_concepts when no stats are available."""
    concepts = intel.key_concepts[:6] if intel.key_concepts else ["A", "B", "C"]
    # Generate deterministic placeholder values (1-based index)
    values = [float(i + 1) * 10.0 for i in range(len(concepts))]
    return [GraphSeries(name=intel.main_topic or "Metric", values=values)]
