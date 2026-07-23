"""
AI Layout Router Module for Learnova
Analyzes educational text chunks to classify content into dynamic visual layout types
and extracts visual attributes (Mermaid diagrams, Tables, Metric Stat Cards).
"""

import json
import os
import re
import time
from dotenv import load_dotenv
from groq import Groq
from ai.diagram_gen import generate_mermaid_diagram
from logger import logger

load_dotenv()

SYSTEM_PROMPT = """
You are a Senior Master Instructional Designer and Educational Content Editor.
Your job is to transform raw presentation text, lecture notes, and OCR diagram descriptions into structured, visually engaging teaching material.

CRITICAL INSTRUCTIONS FOR CONTENT IMPROVEMENT:
1. IMPORTANT TEXT SELECTION: Extract ONLY the top 3 to 4 most critical educational concepts. Strip away verbal fluff, filler words, and repetitive sentences.
2. CONCISE REPHRASING: Rephrase dense paragraphs into punchy, high-impact bullet points (max 12-15 words per bullet).
3. HIGH-YIELD TAKEAWAY: Formulate a single, high-yield summary sentence ("takeaway") that captures the core lesson.
4. DIAGRAM SYNTHESIS: If the input text contains visual diagram OCR (e.g., arrows, steps, flowcharts, architectures), extract the step-by-step node sequence accurately.

SELECT THE BEST VISUAL LAYOUT TYPE:
- "FLOWCHART": For process steps, workflows, cycles, algorithms, chemical/biological mechanisms.
- "TABLE": For comparisons, feature vs feature breakdowns, pros & cons, vs lists.
- "METRIC": For statistical callouts, numerical performance data, percentages, key metrics.
- "CARD_GRID": For 3 to 4 distinct conceptual pillars, key categories, or core principles.
- "MINIMAL_TEXT": For general descriptive text (max 3-4 concise bullets).

Return ONLY valid JSON matching this exact schema:
{
  "layout_type": "FLOWCHART" | "TABLE" | "METRIC" | "CARD_GRID" | "MINIMAL_TEXT",
  "title": "Clean High-Impact Slide Title",
  "takeaway": "Single high-yield key takeaway sentence.",
  "bullets": ["Point 1", "Point 2", "Point 3"],
  "table_data": {
    "headers": ["Feature / Aspect", "Category A", "Category B"],
    "rows": [
      ["Aspect 1", "Detail A1", "Detail B1"],
      ["Aspect 2", "Detail A2", "Detail B2"]
    ]
  },
  "metric_data": {
    "value": "95%",
    "label": "Key Benchmark Metric",
    "description": "Short explanation of why this metric matters."
  }
}
"""

_groq_rate_limited = False  # module-level flag; skip API once quota is hit

def _get_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    return Groq(api_key=api_key, timeout=8.0)

def _heuristic_layout_type(text: str) -> str:
    lower = text.lower()

    # Flowchart signals
    process_kw = ["step 1", "first,", "second,", "process", "workflow", "cycle", "algorithm", "sequence", "pipeline", "stage", "mechanism", "flow"]
    if any(kw in lower for kw in process_kw):
        return "FLOWCHART"

    # Table signals
    table_kw = ["vs", "versus", "comparison", "compare", "pros and cons", "difference", "advantages", "table", "feature"]
    if any(kw in lower for kw in table_kw):
        return "TABLE"

    # Metric signals
    if re.search(r"\b\d+(?:\.\d+)?%|\b\d+\s*(?:percent|million|billion|k|x)\b", lower):
        return "METRIC"

    return "MINIMAL_TEXT"

def classify_and_structure_chunk(text: str, current_title: str = "") -> dict:
    """
    Classifies content chunk into a layout type.
    Falls back instantly to local heuristic when Groq TPM quota is exceeded.
    """
    global _groq_rate_limited
    try:
        # If we already hit the rate limit earlier, skip API call entirely
        if _groq_rate_limited:
            raise ValueError("Groq TPM quota previously exhausted; using local fallback")

        client = _get_client()
        completion = None
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Title: {current_title}\nText:\n{text[:1200]}"},
                ],
                temperature=0.3,
                max_tokens=300,
                timeout=8.0,
            )
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate_limit" in err_str or "quota" in err_str or "tokens" in err_str:
                _groq_rate_limited = True  # Skip all future API calls in this run
                logger.warning("Groq TPM quota hit; switching to local heuristic for all remaining chunks")
                raise ValueError("rate_limit")  # Triggers heuristic fallback below
            raise e

        if not completion or not completion.choices:
            raise ValueError("Failed Groq completion")

        raw_content = (completion.choices[0].message.content or "").strip()
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
            raw_content = match.group(0)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        
        layout_type = data.get("layout_type", "MINIMAL_TEXT").upper()
        if layout_type not in ["FLOWCHART", "TABLE", "METRIC", "CARD_GRID", "MINIMAL_TEXT"]:
            layout_type = _heuristic_layout_type(text)
            
        result = {
            "layout_type": layout_type,
            "title": data.get("title", current_title or "Key Concept"),
            "takeaway": data.get("takeaway", "Review carefully."),
            "bullets": [str(b).strip() for b in data.get("bullets", []) if str(b).strip()][:4],
        }

        # If FLOWCHART, generate Mermaid diagram
        if layout_type == "FLOWCHART":
            diag = generate_mermaid_diagram(text, result["title"])
            result["mermaid_code"] = diag["mermaid_code"]

        # If TABLE, ensure headers and rows exist
        elif layout_type == "TABLE":
            tbl = data.get("table_data", {})
            result["table_headers"] = tbl.get("headers", ["Category", "Details"])
            result["table_rows"] = tbl.get("rows", [["Aspect 1", "Detail 1"], ["Aspect 2", "Detail 2"]])

        # If METRIC, ensure metric value and label
        elif layout_type == "METRIC":
            met = data.get("metric_data", {})
            result["metric_value"] = met.get("value", "100%")
            result["metric_label"] = met.get("label", result["title"])
            result["metric_desc"] = met.get("description", result["takeaway"])

        return result

    except Exception as e:
        logger.error("Layout router LLM call failed: %s", e)
        h_layout = _heuristic_layout_type(text)
        fallback = {
            "layout_type": h_layout,
            "title": current_title or "Overview",
            "takeaway": "Review key details.",
            "bullets": [s.strip() for s in text.split(".") if s.strip()][:3],
        }
        if h_layout == "FLOWCHART":
            safe_t = re.sub(r"[^\w\s]", "", (current_title or "Process")[:30]) or "Start"
            fallback["mermaid_code"] = f"graph TD\n  A[{safe_t}] --> B[Execute Steps] --> C[Key Outcome]"
        elif h_layout == "TABLE":
            fallback["table_headers"] = ["Item", "Description"]
            fallback["table_rows"] = [["Key Concept", text[:80]]]
        elif h_layout == "METRIC":
            fallback["metric_value"] = "Key Stat"
            fallback["metric_label"] = current_title or "Metric"
            fallback["metric_desc"] = text[:100]
        return fallback
