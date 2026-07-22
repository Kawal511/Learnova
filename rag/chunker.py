"""
Smart Chunker Module for Learnova RAG Pipeline
- Preserves heading hierarchy (## lines become chunk titles)
- Splits on paragraph boundaries rather than raw word-count
- Keeps TABLE DATA blocks intact rather than splitting mid-row
- Passes through image dicts so Vision OCR context travels with chunks
"""

import re
from logger import logger

MAX_CHUNK_WORDS = 180  # increased to keep paragraphs coherent
TABLE_SENTINEL = "[TABLE DATA]"


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

    for line in text.splitlines():
        stripped = line.strip()

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
        paragraphs.append("\n".join(current_lines) if in_table else " ".join(current_lines))

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

        for para in paragraphs:
            new_chunks = _chunk_paragraph(para, title, source, chunk_id, image)
            all_chunks.extend(new_chunks)
            chunk_id += len(new_chunks)

    logger.info(
        "Chunked %d items into %d chunks (max %d words each)",
        len(parsed_data), len(all_chunks), MAX_CHUNK_WORDS,
    )
    return all_chunks
