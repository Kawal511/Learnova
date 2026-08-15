"""
Flat slide/page representation shared by every parser.

This is the narrow, dict-friendly view that the RAG chunker and the
rendering layer consume. The rich, structured view lives in
``learnova.parsers.schema`` (``DocumentEntity`` / ``SlidePageEntity``);
each parser builds that first and then flattens it down to these types.

Previously both ``ppt_parser`` and ``pdf_parser`` declared byte-identical
copies of these two dataclasses, so ``isinstance`` checks across parsers
silently failed. There is now exactly one definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SlideData:
    """One slide (PPTX) or one page/chapter (PDF), flattened to plain text."""

    id: int
    title: str
    text: str
    image: Optional[dict] = None
    images: List[dict] = field(default_factory=list)


@dataclass
class ParsedDocument:
    """A whole parsed document as an ordered list of slide units."""

    slide_units: List[SlideData]


__all__ = ["SlideData", "ParsedDocument"]
