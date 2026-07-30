"""
Learnova Visual Specification Engine — KPI Cards Builder
=========================================================
Deterministic builder for KPI Card visual specifications.
Extracts metrics from numbers_and_statistics and cross-enriches with
EnhancedSlide.revision_points for richer metric labels.

Output: KPISpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

import re
from typing import List, Optional

from intelligence.schema import SlideIntelligence
from enhancement.schema import EnhancedSlide
from visual_specs.schema import KPIMetric, KPISpec

# Numeric value extractor (percentages, multipliers, currency, plain numbers)
_KPI_NUM_RE = re.compile(
    r"(\b\d+(?:\.\d+)?\s*%"
    r"|\b\d+(?:\.\d+)?\s*[xX]"
    r"|\$\s*\d+(?:[,\d]*)?(?:\.\d+)?(?:\s*[KMBT])?"
    r"|\b\d+(?:[,\d]*)(?:\.\d+)?\s*(?:seconds?|mins?|hours?|days?|ms|GB|TB|MB)?"
    r"|\b\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_UNIT_HINTS_RE = re.compile(
    r"\b(%|percent|seconds?|mins?|hours?|days?|x|ms|GB|TB|MB|KB|kg|km|°C|°F)\b",
    re.IGNORECASE,
)

_TREND_UP_WORDS   = frozenset(["increase", "growth", "improve", "higher", "up", "more", "gain", "rise"])
_TREND_DOWN_WORDS = frozenset(["decrease", "reduce", "drop", "lower", "down", "less", "fall", "decline"])


def build_kpi_spec(
    intel: SlideIntelligence,
    enhanced: Optional[EnhancedSlide] = None,
) -> KPISpec:
    """
    Build a KPI Cards specification from SlideIntelligence.

    Cross-enriches metric labels with EnhancedSlide.revision_points when available.

    Args:
        intel: SlideIntelligence object.
        enhanced: Optional EnhancedSlide for cross-module label enrichment.

    Returns:
        KPISpec with a list of KPIMetric objects.
    """
    stats = intel.numbers_and_statistics

    if not stats:
        return _build_placeholder_kpi(intel)

    # Build a lookup of revision point keywords for label enrichment
    revision_lookup = _build_revision_lookup(enhanced)

    metrics: List[KPIMetric] = []
    for stat in stats[:8]:
        metric = _parse_metric(stat, revision_lookup)
        if metric:
            metrics.append(metric)

    if not metrics:
        return _build_placeholder_kpi(intel)

    return KPISpec(metrics=metrics)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_metric(stat: str, revision_lookup: dict) -> Optional[KPIMetric]:
    """Extract value, unit, label, and trend from a statistics string."""
    match = _KPI_NUM_RE.search(stat)
    if not match:
        return None

    raw_value = match.group(1).strip()

    # Extract unit from raw value or surrounding text
    unit_match = _UNIT_HINTS_RE.search(raw_value)
    unit = unit_match.group(1) if unit_match else _extract_unit(stat)

    # Clean numeric value (strip unit from value string)
    value = _UNIT_HINTS_RE.sub("", raw_value).strip()
    if not value:
        value = raw_value

    # Label = stat with the matched value removed
    label = _KPI_NUM_RE.sub("", stat).strip(" -:—|")
    label = " ".join(label.split())[:40] or "Metric"

    # Enrich label from revision_points if keyword overlap
    enriched_label = _enrich_label(label, revision_lookup)

    trend = _detect_trend(stat)
    description = stat[:80]

    return KPIMetric(
        title=enriched_label,
        value=value,
        unit=unit,
        trend=trend,
        description=description,
    )


def _extract_unit(text: str) -> str:
    """Extract a unit from surrounding text."""
    match = _UNIT_HINTS_RE.search(text)
    return match.group(1) if match else ""


def _detect_trend(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in _TREND_UP_WORDS):
        return "up"
    if any(w in lower for w in _TREND_DOWN_WORDS):
        return "down"
    return "neutral"


def _build_revision_lookup(enhanced: Optional[EnhancedSlide]) -> dict:
    """Build a keyword → revision_point map for label enrichment."""
    if not enhanced or not enhanced.revision_points:
        return {}
    lookup = {}
    for rp in enhanced.revision_points:
        words = rp.lower().split()
        for w in words:
            if len(w) > 4:  # only meaningful words
                lookup[w] = rp[:40]
    return lookup


def _enrich_label(label: str, revision_lookup: dict) -> str:
    """Enrich a KPI label using revision point keywords if an overlap is found."""
    if not revision_lookup:
        return label
    lower_label = label.lower()
    for keyword, enrichment in revision_lookup.items():
        if keyword in lower_label:
            return f"{label} ({enrichment})"[:60]
    return label


def _build_placeholder_kpi(intel: SlideIntelligence) -> KPISpec:
    """Fallback KPI from key_concepts with placeholder values."""
    metrics = [
        KPIMetric(
            title=concept[:40],
            value=str((i + 1) * 10),
            unit="",
            trend="neutral",
            description=f"Key metric for: {concept}",
        )
        for i, concept in enumerate(intel.key_concepts[:4])
    ]
    if not metrics:
        metrics = [KPIMetric(title="Performance", value="100", unit="%", trend="neutral", description="Overall performance metric")]
    return KPISpec(metrics=metrics)
