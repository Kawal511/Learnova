"""
Slide geometry and text fitting.

Every position in the deck used to be a hardcoded inch value, so a card held
the same box whether it carried three words or forty — short text floated in
a mostly empty rectangle, long text overflowed its edges.

This module computes geometry from the content instead:

* ``fit_font_size`` picks the largest point size at which the text still fits.
* ``grid_cells`` lays N cards out in a wrapping grid, sized to the area.
* ``content_band`` shrinks the body area when a takeaway or an inline quiz
  band is present, so nothing is drawn on top of anything else.

The measurement is an estimate, not a real text engine — PowerPoint does the
final shaping. It is deliberately conservative (assumes slightly wider glyphs
than average) so the error lands on "a bit small" rather than "overflowing".
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

# ── Canvas ────────────────────────────────────────────────────────────────────
SLIDE_W = 13.33
SLIDE_H = 7.5

MARGIN_X = 0.5
HEADER_H = 1.1
CONTENT_TOP = 1.35
BOTTOM_MARGIN = 0.35

TAKEAWAY_H = 1.05
QUIZ_BAND_H = 2.05          # question line + a row of four options
GAP = 0.2

# Typography bounds. Below MIN_PT text stops being readable from the back of a
# room, so we paginate instead of shrinking further.
MAX_BODY_PT = 22.0
MIN_BODY_PT = 11.0
MAX_CARD_PT = 18.0
MIN_CARD_PT = 9.0

# Average glyph width as a fraction of point size, and line height multiplier.
_GLYPH_RATIO = 0.52
_LINE_HEIGHT = 1.28


@dataclass(frozen=True)
class Box:
    left: float
    top: float
    width: float
    height: float


def content_band(has_takeaway: bool = True, has_quiz: bool = False) -> Box:
    """The usable body area, after the header, takeaway and quiz bands."""
    top = CONTENT_TOP
    bottom = SLIDE_H - BOTTOM_MARGIN
    if has_quiz:
        bottom -= QUIZ_BAND_H + GAP
    if has_takeaway:
        bottom -= TAKEAWAY_H + GAP
    return Box(MARGIN_X, top, SLIDE_W - 2 * MARGIN_X, max(1.0, bottom - top))


def quiz_band(has_takeaway: bool = True) -> Box:
    """Where the inline quiz sits: directly above the takeaway bar."""
    bottom = SLIDE_H - BOTTOM_MARGIN
    if has_takeaway:
        bottom -= TAKEAWAY_H + GAP
    return Box(MARGIN_X, bottom - QUIZ_BAND_H, SLIDE_W - 2 * MARGIN_X, QUIZ_BAND_H)


def takeaway_band() -> Box:
    bottom = SLIDE_H - BOTTOM_MARGIN
    return Box(MARGIN_X, bottom - TAKEAWAY_H, SLIDE_W - 2 * MARGIN_X, TAKEAWAY_H)


# ── Measurement ───────────────────────────────────────────────────────────────
def estimate_lines(text: str, width_in: float, font_pt: float) -> int:
    """How many wrapped lines a string needs in a box of the given width."""
    if not text:
        return 0
    chars_per_line = max(1, int((width_in * 72.0) / (font_pt * _GLYPH_RATIO)))
    lines = 0
    for paragraph in str(text).splitlines() or [""]:
        lines += max(1, math.ceil(len(paragraph) / chars_per_line))
    return max(1, lines)


def block_height(texts: Sequence[str], width_in: float, font_pt: float,
                 spacing_pt: float = 8.0) -> float:
    """Height in inches needed to render these paragraphs at this size."""
    total_lines = sum(estimate_lines(t, width_in, font_pt) for t in texts)
    line_in = (font_pt * _LINE_HEIGHT) / 72.0
    gaps_in = (max(0, len(texts) - 1) * spacing_pt) / 72.0
    return total_lines * line_in + gaps_in


def fit_font_size(texts: Sequence[str], width_in: float, height_in: float,
                  max_pt: float = MAX_BODY_PT, min_pt: float = MIN_BODY_PT,
                  spacing_pt: float = 8.0) -> float:
    """
    Largest point size at which ``texts`` fit inside the given box.

    Steps down in half points and stops at ``min_pt`` — the caller has already
    decided this much content belongs on one slide, so we never go smaller
    than legible.
    """
    items = [t for t in texts if str(t).strip()]
    if not items:
        return max_pt

    size = max_pt
    while size > min_pt:
        if block_height(items, width_in, size, spacing_pt) <= height_in:
            return round(size, 1)
        size -= 0.5
    return min_pt


# ── Card grids ────────────────────────────────────────────────────────────────
def grid_cells(count: int, area: Box, gap: float = 0.22,
               max_per_row: int = 4) -> List[Box]:
    """
    Lay out ``count`` cards inside ``area``, wrapping into rows.

    A single row of six cards leaves each one too narrow to read, so past
    ``max_per_row`` the grid wraps and uses the vertical space instead.
    """
    if count <= 0:
        return []

    columns = min(count, max_per_row)
    rows = math.ceil(count / columns)
    # Balance the last row: 5 items become 3+2, not 4+1.
    if rows > 1:
        columns = math.ceil(count / rows)

    cell_w = (area.width - gap * (columns - 1)) / columns
    cell_h = (area.height - gap * (rows - 1)) / rows

    cells: List[Box] = []
    for index in range(count):
        row, col = divmod(index, columns)
        cells.append(Box(
            left=area.left + col * (cell_w + gap),
            top=area.top + row * (cell_h + gap),
            width=cell_w,
            height=cell_h,
        ))
    return cells


def split_text_image(area: Box, has_image: bool,
                     image_fraction: float = 0.38) -> Tuple[Box, Box]:
    """Split the body into a text column and an image column."""
    if not has_image:
        return area, Box(0, 0, 0, 0)
    image_w = area.width * image_fraction
    text_w = area.width - image_w - GAP
    return (
        Box(area.left, area.top, text_w, area.height),
        Box(area.left + text_w + GAP, area.top, image_w, area.height),
    )


__all__ = [
    "SLIDE_W", "SLIDE_H", "MARGIN_X", "HEADER_H", "CONTENT_TOP",
    "TAKEAWAY_H", "QUIZ_BAND_H", "GAP",
    "MAX_BODY_PT", "MIN_BODY_PT", "MAX_CARD_PT", "MIN_CARD_PT",
    "Box", "content_band", "quiz_band", "takeaway_band",
    "estimate_lines", "block_height", "fit_font_size",
    "grid_cells", "split_text_image",
]
