"""
Engagement Scorer Module for Learnova
Computes a 0-100 engagement score per improved slide based on content quality heuristics.
"""


def _text_density_score(text: str) -> float:
    """25 pts max — reward 40-80 words, penalize >100."""
    word_count = len(text.split())
    if 40 <= word_count <= 80:
        return 25.0
    elif word_count < 40:
        return max(0.0, 25.0 * (word_count / 40))
    elif word_count <= 100:
        return max(0.0, 25.0 * (1 - (word_count - 80) / 20))
    else:
        return 5.0  # floor for very long text


def _bullet_count_score(bullets: list) -> float:
    """20 pts max — reward 3-5 bullets, penalize >7 or <2."""
    n = len(bullets)
    if 3 <= n <= 5:
        return 20.0
    elif n == 2:
        return 14.0
    elif n == 6:
        return 16.0
    elif n == 7:
        return 12.0
    elif n < 2:
        return max(0.0, 10.0 * n)
    else:
        return max(4.0, 20.0 - (n - 5) * 3)


def _title_quality_score(title: str) -> float:
    """15 pts max — reward 4-8 words, penalize >12."""
    word_count = len(title.split())
    if 4 <= word_count <= 8:
        return 15.0
    elif word_count < 4:
        return max(0.0, 15.0 * (word_count / 4))
    elif word_count <= 12:
        return max(0.0, 15.0 * (1 - (word_count - 8) / 4))
    else:
        return 3.0


def _has_takeaway_score(takeaway: str) -> float:
    """20 pts max — 20 if takeaway exists and is meaningful, 0 otherwise."""
    if takeaway and len(takeaway.strip()) > 5:
        return 20.0
    return 0.0


def _readability_score(text: str) -> float:
    """20 pts max — avg word length < 6 chars = full marks."""
    words = text.split()
    if not words:
        return 0.0
    avg_len = sum(len(w) for w in words) / len(words)
    if avg_len < 6:
        return 20.0
    elif avg_len < 8:
        return max(0.0, 20.0 * (1 - (avg_len - 6) / 2))
    else:
        return 4.0


def score_slide(improved: dict) -> dict:
    """
    Compute engagement score for a single improved slide.

    Args:
        improved: Dict with keys title, bullets, takeaway.

    Returns:
        {"score": int, "breakdown": {"text_density": ..., ...}}
    """
    title = improved.get("title", "")
    bullets = improved.get("bullets", [])
    takeaway = improved.get("takeaway", "")
    full_text = " ".join(bullets)

    breakdown = {
        "text_density": round(_text_density_score(full_text), 1),
        "bullet_count": round(_bullet_count_score(bullets), 1),
        "title_quality": round(_title_quality_score(title), 1),
        "has_takeaway": round(_has_takeaway_score(takeaway), 1),
        "readability": round(_readability_score(full_text), 1),
    }

    total = sum(breakdown.values())
    return {"score": round(total), "breakdown": breakdown}


def score_all_slides(improved_results: list[dict]) -> dict:
    """
    Score every improved slide and compute the overall average.

    Args:
        improved_results: List of {"original": ..., "improved": ...} dicts.

    Returns:
        {
            "scores": [{"slide_title": ..., "score": ..., "breakdown": ...}, ...],
            "average": float
        }
    """
    scores = []
    for entry in improved_results:
        imp = entry["improved"]
        result = score_slide(imp)
        result["slide_title"] = imp.get("title", "Untitled")
        scores.append(result)

    avg = sum(s["score"] for s in scores) / len(scores) if scores else 0
    return {"scores": scores, "average": round(avg, 1)}
