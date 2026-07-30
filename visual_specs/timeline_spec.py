"""
Learnova Visual Specification Engine — Timeline & Roadmap Builder
==================================================================
Deterministic builder for Timeline and Roadmap visual specifications.
Input: SlideIntelligence (chronology, steps)
Output: TimelineSpec

No LLMs. No rendering. No Mermaid.
"""

from __future__ import annotations

import re
from typing import List

from intelligence.schema import SlideIntelligence
from visual_specs.schema import TimelineEvent, TimelineSpec

# Regex patterns for extracting date/phase tokens
_DATE_PATTERN = re.compile(
    r"(\b\d{4}\b|\bQ[1-4]\b|\bPhase\s*\d+\b|\bStep\s*\d+\b"
    r"|\bWeek\s*\d+\b|\bMonth\s*\d+\b|\bDay\s*\d+\b)",
    re.IGNORECASE,
)

_MILESTONE_KEYWORDS = frozenset([
    "launch", "release", "finish", "complete", "go-live", "milestone",
    "deploy", "ship", "publish", "final", "deadline", "due",
])


def build_timeline_spec(intel: SlideIntelligence) -> TimelineSpec:
    """
    Build a Timeline or Roadmap specification from SlideIntelligence.

    Uses `chronology` first, falls back to `steps`, then `processes`.

    Args:
        intel: SlideIntelligence object.

    Returns:
        TimelineSpec with ordered_events, milestones, sequence, dates.
    """
    source_items = _pick_source(intel)

    ordered_events: List[TimelineEvent] = []
    milestone_ids: List[str] = []
    dates: List[str] = []

    for i, item in enumerate(source_items):
        event_id = f"event_{i + 1}"
        date, description = _extract_date_and_description(item, i)

        # Build a short title from first meaningful phrase
        title = _build_title(description, i)

        is_milestone = any(kw in item.lower() for kw in _MILESTONE_KEYWORDS)

        event = TimelineEvent(
            id=event_id,
            title=title,
            description=description,
            date=date,
            is_milestone=is_milestone,
        )
        ordered_events.append(event)
        dates.append(date)
        if is_milestone:
            milestone_ids.append(event_id)

    # sequence = ordered list of titles
    sequence = [e.title for e in ordered_events]

    return TimelineSpec(
        ordered_events=ordered_events,
        milestones=milestone_ids,
        sequence=sequence,
        dates=dates,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _pick_source(intel: SlideIntelligence) -> List[str]:
    if intel.chronology:
        return intel.chronology[:10]
    if intel.steps:
        return intel.steps[:8]
    if intel.processes:
        return intel.processes[:6]
    return [f"Phase {i + 1}" for i in range(4)]


def _extract_date_and_description(item: str, index: int):
    """Extract a date token and remaining description from an item string."""
    match = _DATE_PATTERN.search(item)
    if match:
        date = match.group(1)
        desc = item.replace(date, "").strip(" -:—|")
    else:
        date = f"Phase {index + 1}"
        desc = item.strip()
    return date, desc or item.strip()


def _build_title(description: str, index: int) -> str:
    """Create a short title from the first sentence or first 6 words."""
    # First sentence
    parts = re.split(r"[.!?;]", description)
    title = parts[0].strip() if parts else description
    words = title.split()
    if len(words) > 6:
        title = " ".join(words[:5]) + "…"
    return title or f"Event {index + 1}"
