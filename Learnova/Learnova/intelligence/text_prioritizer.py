"""
Learnova Intelligence Layer — Text Prioritizer
===============================================
Assigns a TextPriority tag to every TextBlockElement in a SlidePageEntity.

No LLM calls. Uses heuristic rule evaluation based on typography, reading order,
semantic role, and redundancy/repetition across slides.

Priority levels:
  - HIGH: Titles, main headings, key concepts, bold emphasis, definitions
  - MEDIUM: Factual body content, supporting concepts, steps, important facts
  - LOW: Fine print, deep nested bullets, filler text, long citations
  - DECORATIVE: Non-semantic labels, slide numbers, copyright footers, page numbers
  - REDUNDANT: Near-duplicate text block on the SAME slide (>80% word overlap with a higher priority block)
  - REPEATED: Text block appearing verbatim across MULTIPLE slides in the document
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

from parsers.schema import SlidePageEntity, TextBlockElement
from intelligence.schema import PrioritizedTextBlock, TextPriority

# Patterns for decorative/boilerplate slide text
_RE_DECORATIVE = re.compile(
    r"""
    ^\s*
    (?:
        slide\s+\d+(?:\s*/\s*\d+)?             | # "Slide 1" or "Slide 1 / 10"
        page\s+\d+(?:\s*/\s*\d+)?              | # "Page 2" or "Page 1 / 10"
        \d+\s*/\s*\d+                          | # "1 / 10" or "1/10"
        copyright\s+.*                         | # "Copyright 2026..."
        all\s+rights\s+reserved                | # "All rights reserved"
        confidential                           | # "Confidential"
        draft                                  | # "DRAFT"
        www\.[a-z0-9\.\-]+\.[a-z]{2,}          | # Web URLs in footer
        https?://[^\s]+                        | # HTTP URLs
        [\d]{1,2}[\/\-\.][\d]{1,2}[\/\-\.][\d]{2,4} # Plain dates in corner
    )
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_FILLER_PHRASES = [
    "as mentioned earlier", "please note that", "it is important to remember",
    "as shown in the figure", "refer to the next slide", "for more information",
    "click here to learn more", "this slide shows", "in this section we will",
    "as stated above", "continue to the next page",
]


def _words(text: str) -> Set[str]:
    return set(re.findall(r"[a-zA-Z']+", text.lower()))


def _word_overlap(text1: str, text2: str) -> float:
    w1 = _words(text1)
    w2 = _words(text2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def prioritize_text_blocks(
    slide: SlidePageEntity,
    concepts: Dict[str, Any],
    doc_repeated_texts: Set[str] = None,
) -> List[PrioritizedTextBlock]:
    """
    Prioritizes text blocks for a slide.

    Args:
        slide: Target SlidePageEntity
        concepts: Extracted concepts dictionary from concept_extractor
        doc_repeated_texts: Global set of text strings occurring across multiple slides

    Returns:
        List of PrioritizedTextBlock objects corresponding to slide.text_blocks
    """
    if doc_repeated_texts is None:
        doc_repeated_texts = set()

    key_concepts = [c.lower() for c in concepts.get("key_concepts", [])]
    definitions = [d.lower() for d in concepts.get("definitions", {}).keys()]
    important_facts = [f.lower() for f in concepts.get("important_facts", [])]

    prioritized_list: List[PrioritizedTextBlock] = []
    seen_high_texts: List[str] = []

    for tb in slide.text_blocks:
        raw_text = tb.text.strip()
        if not raw_text:
            continue

        text_lower = raw_text.lower()
        word_count = len(raw_text.split())

        # Rule 1: Repeated footer / header across slides
        if text_lower in doc_repeated_texts and not tb.is_heading:
            prioritized_list.append(
                PrioritizedTextBlock(
                    block_id=tb.id,
                    text=raw_text,
                    priority=TextPriority.REPEATED,
                    reason="Boilerplate or repeated text across multiple slides",
                    word_count=word_count,
                )
            )
            continue

        # Rule 2: Decorative text (slide numbers, copyrights, standalone numbers, multi-part footers)
        def _is_decorative(text: str) -> bool:
            if not text:
                return False
            if text.isdigit():
                return True
            if _RE_DECORATIVE.match(text):
                return True
            # Multi-part pipe or dash separated footers (e.g. "Page 1 / 10 | Confidential")
            parts = [p.strip() for p in re.split(r"[|–—]", text) if p.strip()]
            if len(parts) >= 2:
                if all(
                    _RE_DECORATIVE.match(p)
                    or p.isdigit()
                    or p.lower() in ("confidential", "draft", "all rights reserved", "internal use only")
                    for p in parts
                ):
                    return True
            return False

        if _is_decorative(raw_text):
            prioritized_list.append(
                PrioritizedTextBlock(
                    block_id=tb.id,
                    text=raw_text,
                    priority=TextPriority.DECORATIVE,
                    reason="Slide boilerplate or decorative metadata",
                    word_count=word_count,
                )
            )
            continue

        # Rule 3: Redundant text check against existing HIGH priority blocks on this slide
        is_redundant = False
        for high_text in seen_high_texts:
            if _word_overlap(raw_text, high_text) > 0.8 and word_count >= 4:
                is_redundant = True
                break

        if is_redundant:
            prioritized_list.append(
                PrioritizedTextBlock(
                    block_id=tb.id,
                    text=raw_text,
                    priority=TextPriority.REDUNDANT,
                    reason="Semantically redundant with higher-priority text block",
                    word_count=word_count,
                )
            )
            continue

        # Rule 4: HIGH priority triggers
        is_high = False
        high_reason = ""

        if tb.is_heading or tb.heading_level > 0:
            is_high = True
            high_reason = "Slide title or main heading"
        elif tb.font_size and tb.font_size >= 20:
            is_high = True
            high_reason = "Large font size indicator (>= 20pt)"
        elif tb.is_bold and word_count <= 15:
            is_high = True
            high_reason = "Bold emphasis on concise concept block"
        elif any(kc in text_lower for kc in key_concepts):
            is_high = True
            high_reason = "Contains identified key concept"
        elif any(defn in text_lower for defn in definitions):
            is_high = True
            high_reason = "Contains term definition"

        if is_high:
            seen_high_texts.append(raw_text)
            prioritized_list.append(
                PrioritizedTextBlock(
                    block_id=tb.id,
                    text=raw_text,
                    priority=TextPriority.HIGH,
                    reason=high_reason,
                    word_count=word_count,
                )
            )
            continue

        # Rule 5: LOW priority triggers
        is_low = False
        low_reason = ""

        if tb.bullet_level >= 2:
            is_low = True
            low_reason = "Deep nested sub-bullet (level 2+)"
        elif any(filler in text_lower for filler in _FILLER_PHRASES):
            is_low = True
            low_reason = "Contains low-yield filler phrase"
        elif word_count > 45:
            is_low = True
            low_reason = "Dense narrative paragraph (> 45 words)"

        if is_low:
            prioritized_list.append(
                PrioritizedTextBlock(
                    block_id=tb.id,
                    text=raw_text,
                    priority=TextPriority.LOW,
                    reason=low_reason,
                    word_count=word_count,
                )
            )
            continue

        # Rule 6: Default to MEDIUM priority
        prioritized_list.append(
            PrioritizedTextBlock(
                block_id=tb.id,
                text=raw_text,
                priority=TextPriority.MEDIUM,
                reason="Standard supporting body content",
                word_count=word_count,
            )
        )

    return prioritized_list
