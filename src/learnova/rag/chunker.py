"""
Smart Chunker Module for Learnova RAG Pipeline
- Preserves heading hierarchy (## lines become chunk titles)
- Splits on paragraph boundaries rather than raw word-count
- Keeps TABLE DATA blocks intact rather than splitting mid-row
- Keeps markdown list items as discrete lines instead of flattening them
- Passes through image dicts so Vision OCR context travels with chunks
"""

import re
from learnova.logging_config import logger

MAX_CHUNK_WORDS = 180  # increased to keep paragraphs coherent
TABLE_SENTINEL = "[TABLE DATA]"

# Markdown list item: "- x", "* x", "+ x", "1. x", "2) x"
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")


def _strip_list_marker(line: str) -> tuple[bool, str]:
    """Return (is_list_item, text_without_marker)."""
    match = _LIST_ITEM_RE.match(line)
    if match:
        return True, match.group(1).strip()
    return False, line.strip()


def _split_into_paragraphs(text: str) -> list[str]:
    """
    Split structured text into logical paragraphs:
    - Each ## heading starts a new paragraph
    - Each TABLE DATA block is kept intact
    - Blank lines separate regular paragraphs
    """
    paragraphs = []
    current_lines: list[str] = []
    in_table = False
    in_list = False

    def _flush() -> None:
        """Close the current run: list items keep their line breaks."""
        nonlocal current_lines, in_list
        if current_lines:
            joiner = "\n" if in_list else " "
            paragraphs.append(joiner.join(current_lines))
            current_lines = []
        in_list = False

    for line in text.splitlines():
        stripped = line.strip()

        # Markdown list runs are held together but stay line-separated, so a
        # bulleted list survives as N bullets instead of one run-on sentence.
        if not in_table:
            is_item, item_text = _strip_list_marker(line)
            if is_item:
                if not in_list:
                    _flush()
                    in_list = True
                if item_text:
                    current_lines.append(item_text)
                continue
            if in_list and stripped:
                # Continuation line belonging to the previous bullet.
                if current_lines:
                    current_lines[-1] = f"{current_lines[-1]} {stripped}"
                continue
            if in_list:
                _flush()

        # Start of table block
        if stripped == TABLE_SENTINEL:
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            in_table = True
            current_lines = [stripped]
            continue

        # Inside table: accumulate until empty line or new heading
        if in_table:
            if stripped.startswith("##") or (not stripped and current_lines):
                paragraphs.append("\n".join(current_lines))
                current_lines = []
                in_table = False
                if stripped.startswith("##"):
                    current_lines = [stripped]
            else:
                if stripped:
                    current_lines.append(stripped)
            continue

        # Heading → flush previous, start new paragraph
        if stripped.startswith("## "):
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            current_lines = [stripped.lstrip("# ").strip()]
            continue

        # Empty line → paragraph boundary
        if not stripped:
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            continue

        current_lines.append(stripped)

    if current_lines:
        # Tables and list runs keep their line breaks; prose is joined.
        joiner = "\n" if (in_table or in_list) else " "
        paragraphs.append(joiner.join(current_lines))

    return [p for p in paragraphs if p.strip()]


def _chunk_paragraph(para: str, title: str, source: int,
                      chunk_id_start: int, image: dict | None) -> list[dict]:
    """
    Chunk a single paragraph into MAX_CHUNK_WORDS sized pieces.
    Table blocks are never split — returned as one chunk.
    """
    chunks = []
    cid = chunk_id_start

    # Keep table blocks intact
    if para.startswith(TABLE_SENTINEL) or " | " in para:
        chunks.append({
            "id": cid,
            "title": title,
            "text": para,
            "source": source,
            **({"image": image} if image else {}),
        })
        return chunks

    words = para.split()

    # A paragraph that already fits is emitted verbatim, so multi-line list
    # runs keep their line breaks instead of being flattened into prose.
    if len(words) <= MAX_CHUNK_WORDS:
        chunk = {
            "id": cid,
            "title": title,
            "text": para,
            "source": source,
        }
        if image:
            chunk["image"] = image
        return [chunk]

    for i in range(0, max(1, len(words)), MAX_CHUNK_WORDS):
        segment = " ".join(words[i: i + MAX_CHUNK_WORDS])
        chunk: dict = {
            "id": cid,
            "title": title,
            "text": segment,
            "source": source,
        }
        if image:
            chunk["image"] = image
        chunks.append(chunk)
        cid += 1

    return chunks


def merge_chunks_by_section(chunks: list[dict]) -> list[dict]:
    """
    Collapse the chunks of one source section back into a single chunk.

    Chunking splits a section into paragraph-sized pieces for retrieval, but
    the renderer makes **one slide per chunk** — so a section with 22
    paragraphs became 22 near-empty slides all sharing the same title.

    A section is one topic and should therefore be one slide. The density
    stage then decides how much fits and paginates the remainder onto
    numbered continuation slides, which is where that decision belongs.
    """
    merged: dict = {}
    order: list = []

    for chunk in chunks:
        key = chunk.get("source")
        if key is None:
            key = chunk.get("title", "")
        if key not in merged:
            merged[key] = dict(chunk)
            order.append(key)
            continue

        target = merged[key]
        extra = (chunk.get("text") or "").strip()
        if extra:
            target["text"] = f"{(target.get('text') or '').rstrip()}\n{extra}"
        # Keep the first image seen for the section.
        if "image" not in target and chunk.get("image"):
            target["image"] = chunk["image"]

    out = []
    for index, key in enumerate(order):
        item = merged[key]
        item["id"] = index
        out.append(item)

    if len(out) != len(chunks):
        logger.info("merged %d chunk(s) into %d section slide(s)", len(chunks), len(out))
    return out


def chunk_parsed_data(parsed_data: list[dict]) -> list[dict]:
    """
    Convert parsed slides/pages into structured text chunks.

    Accepts:
      - ppt_parser output  (keys: slide, title, text, image?)
      - pdf_parser output  (keys: page, title, text, image?)

    Returns:
        [{id, title, text, source, image?}, ...]
    """
    all_chunks: list[dict] = []
    chunk_id = 0

    for item in parsed_data:
        source = item.get("slide") or item.get("page", 0)
        title = (item.get("title") or item.get("heading") or "Untitled").strip()
        image = item.get("image")

        # Prefer structured 'text' field; fallback to joining 'content' list
        raw_text = item.get("text", "")
        if not raw_text:
            content = item.get("content", "")
            if isinstance(content, list):
                raw_text = "\n".join(str(c) for c in content if c)
            else:
                raw_text = str(content or "")

        raw_text = raw_text.strip()
        if not raw_text:
            raw_text = title  # absolute fallback

        # Split into heading-aware paragraphs
        paragraphs = _split_into_paragraphs(raw_text)
        if not paragraphs:
            paragraphs = [raw_text]

        # The image belongs to the unit, not to each of its paragraphs. Passing
        # it to every chunk makes the renderer emit one duplicate figure slide
        # per paragraph, so only the first chunk of a unit carries it.
        image_for_next = image
        for para in paragraphs:
            new_chunks = _chunk_paragraph(para, title, source, chunk_id, image_for_next)
            if new_chunks and image_for_next:
                image_for_next = None
            all_chunks.extend(new_chunks)
            chunk_id += len(new_chunks)

    logger.info(
        "Chunked %d items into %d chunks (max %d words each)",
        len(parsed_data), len(all_chunks), MAX_CHUNK_WORDS,
    )
    return all_chunks
