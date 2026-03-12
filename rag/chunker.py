"""
Chunker Module for Learnova RAG Pipeline
Splits parsed slide/page data into smaller text chunks (max 120 words).
"""

from logger import logger

MAX_CHUNK_WORDS = 120


def chunk_parsed_data(parsed_data: list[dict]) -> list[dict]:
    """
    Convert parsed slides/pages into uniform text chunks.

    Accepts output from ppt_parser (keys: slide, title, content)
    or pdf_parser (keys: page, heading, content).

    Returns:
        [{"id": 1, "title": "...", "text": "...", "source": 1}, ...]
    """
    chunks = []
    chunk_id = 0

    for item in parsed_data:
        # Determine source number and title based on parser output format
        source = item.get("slide") or item.get("page", 0)
        title = item.get("title") or item.get("heading", "Untitled")

        # Build full text from content (list of bullets for PPT, string for PDF)
        content = item.get("content", "")
        if isinstance(content, list):
            full_text = " ".join(content)
        else:
            full_text = content

        full_text = full_text.strip()
        if not full_text:
            full_text = title  # Use title as text if body is empty

        # Split into word-bounded chunks of max 120 words
        words = full_text.split()
        for i in range(0, len(words), MAX_CHUNK_WORDS):
            chunk_id += 1
            segment = " ".join(words[i : i + MAX_CHUNK_WORDS])
            chunks.append({
                "id": chunk_id,
                "title": title,
                "text": segment,
                "source": source,
            })

    logger.info("Chunked %d items into %d chunks (max %d words each)",
                len(parsed_data), len(chunks), MAX_CHUNK_WORDS)
    return chunks
