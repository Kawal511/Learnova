"""
AI Improver Module for Learnova
Uses Groq to transform raw slide text into structured educational content.
"""

import json
import os
import re
import time
from dotenv import load_dotenv
from groq import Groq
from logger import logger

load_dotenv()

MAX_CHUNKS = 60
DELAY_BETWEEN_CALLS = 0.3

SYSTEM_PROMPT = (
    "You are an expert educational content designer. "
    "Transform the given raw slide text into clean engaging teaching content. "
    "Return ONLY valid JSON: "
    '{"title": "...", "bullets": ["bullet 1","bullet 2","bullet 3","bullet 4","bullet 5"], "takeaway": "..."}'
)

def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    return Groq(api_key=api_key)

def _clean_bullet(b: str) -> str:
    # Strip leading symbols/numbers
    b = re.sub(r"^[0-9A-Za-z]+[\.)]\s*", "", b.strip())
    b = re.sub(r"^[-*•>▪]\s*", "", b).strip()
    return b[:200] if len(b) > 200 else b

def _parse_llm_json(raw_response: str) -> dict | None:
    text = raw_response.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
        if "bullets" in data and isinstance(data["bullets"], list):
            seen = set()
            clean_bullets = []
            for b in data["bullets"]:
                cb = _clean_bullet(str(b))
                if cb and cb not in seen:
                    seen.add(cb)
                    clean_bullets.append(cb)
            data["bullets"] = clean_bullets[:5]
            while len(data["bullets"]) < 5:
                data["bullets"].append("(Additional content needed here)")
        return data
    except json.JSONDecodeError:
        return None

def _fallback_improvement(chunk: dict) -> dict:
    text = (chunk.get("text") or "").strip()
    title = (chunk.get("title") or "Untitled").strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    bullets = []
    if sentences:
        bullets = [_clean_bullet(s) for s in sentences[:5]]
    else:
        words = text.split()
        for i in range(0, min(len(words), 70), 14):
            bullets.append(" ".join(words[i : i + 14]))
    dedup = list(dict.fromkeys(bullets))
    while len(dedup) < 5:
        dedup.append("(Additional content needed here)")
    return {"title": title, "bullets": dedup[:5], "takeaway": dedup[0][:100] if dedup else "Review carefully."}

def improve_chunks(chunks: list[dict]) -> list[dict]:
    client = _get_client()
    capped = chunks[:MAX_CHUNKS]
    results = []

    for i, chunk in enumerate(capped):
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": chunk["text"]},
                ],
                temperature=0.4,
                max_tokens=1200,
            )
            raw_content = (completion.choices[0].message.content or "").strip()
            parsed = _parse_llm_json(raw_content)

            if parsed and "title" in parsed and "bullets" in parsed:
                improved = parsed
            else:
                logger.warning("Chunk %d: Groq returned non-JSON, using fallback", chunk.get("id", i))
                improved = _fallback_improvement({**chunk, "text": raw_content or chunk.get("text", "")})
        except Exception as e:
            logger.error("Groq call failed for chunk %d: %s", chunk.get("id", i), e)
            improved = _fallback_improvement(chunk)

        results.append({"original": chunk, "improved": improved})
        if i < len(capped) - 1:
            time.sleep(DELAY_BETWEEN_CALLS)

    logger.info("Improved %d / %d chunks via Groq", len(results), len(chunks))
    return results
