"""
AI Improver Module for Learnova
Uses Groq and Layout Router to transform raw slide text into structured, visual educational content.
"""

import time
from ai.layout_router import classify_and_structure_chunk
from logger import logger

MAX_CHUNKS = 60
DELAY_BETWEEN_CALLS = 0.3

def improve_chunks(chunks: list[dict]) -> list[dict]:
    """
    Transform raw text chunks into visually classified slide items.
    """
    capped = chunks[:MAX_CHUNKS]
    results = []

    for i, chunk in enumerate(capped):
        chunk_text = (chunk.get("text") or "").strip()
        chunk_title = (chunk.get("title") or "").strip()

        try:
            improved = classify_and_structure_chunk(chunk_text, chunk_title)
        except Exception as e:
            logger.error("Error structuring chunk %d: %s", chunk.get("id", i), e)
            improved = {
                "layout_type": "MINIMAL_TEXT",
                "title": chunk_title or "Overview",
                "bullets": [chunk_text[:150]],
                "takeaway": "Review details carefully.",
            }

        results.append({
            "original": chunk,
            "improved": improved,
        })

        if i < len(capped) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    logger.info("Improved and visually routed %d / %d chunks", len(results), len(chunks))
    return results
