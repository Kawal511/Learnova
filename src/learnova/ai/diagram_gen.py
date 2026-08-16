"""
AI Diagram Generator Module for Learnova
Generates valid Mermaid.js code for flowcharts, sequence diagrams, and process workflows.
"""

import json
import os
import re
import time
from dotenv import load_dotenv
from learnova.providers.base import LLMProvider
from learnova.providers.router import TASK_DIAGRAM, get_router
from learnova.logging_config import logger
from typing import Optional

load_dotenv()

# Module-level singleton – reuse one httpx connection pool for all diagram calls.
_llm_provider: Optional[LLMProvider] = None


def _get_llm_provider() -> Optional[LLMProvider]:
    """Return the cached router, or None when no API key is configured."""
    global _llm_provider
    if _llm_provider is None:
        router = get_router()
        if not router.available:
            logger.warning("No LLM provider configured — using fallback diagrams.")
            return None
        _llm_provider = router
    return _llm_provider

SYSTEM_PROMPT = (
    "You are an expert educational visual designer. "
    "Convert the raw educational content into a valid, concise Mermaid.js diagram definition. "
    "Choose graph TD or graph LR for flowcharts, or sequenceDiagram for sequential interactions. "
    "Keep node labels brief (max 5-7 words per node). "
    "Do NOT use special characters or unescaped quotes in node labels. "
    "Return ONLY valid JSON in this format: "
    '{"mermaid_code": "graph TD\\n  A[Step 1] --> B[Step 2]", "diagram_title": "..."}'
)

def _sanitise_mermaid(code: str) -> str:
    """
    Repair the malformed edge syntax models keep emitting.

    Observed in real output: ``A -->|Calculate|> B``. The trailing ``>`` after
    a closing edge label is invalid and makes mermaid refuse to draw the whole
    diagram, so the slide rendered empty.
    """
    if not code:
        return code
    # `-->|label|>` and `--|label|>` lose the stray arrow head.
    code = re.sub(r"(\|[^|\n]*\|)\s*>\s*", r"\1 ", code)
    # `-- >` / `- ->` split arrows.
    code = re.sub(r"--\s+>", "-->", code)
    # Collapse runs of spaces without touching the newlines mermaid needs.
    code = re.sub(r"[ \t]{2,}", " ", code)
    return code.strip()


def generate_mermaid_diagram(text: str, title: str = "") -> dict:
    """
    Generate Mermaid.js code for process/workflow text.
    """
    try:
        provider = _get_llm_provider()
        if provider is None:
            raise ValueError("No LLM provider available")
        raw_content = provider.generate(
            prompt=f"Title: {title}\nContent:\n{text}",
            system_prompt=SYSTEM_PROMPT,
            task=TASK_DIAGRAM,       # router picks the model per provider
            temperature=0.3,
            max_tokens=600,
            timeout=15.0,
        )
        if not raw_content or not raw_content.strip():
            raise ValueError("Empty LLM response for diagram")
        match = re.search(r"\{[\s\S]*\}", raw_content)
        if not match:
            raise ValueError("No JSON object found in diagram response")
        raw_content = match.group(0)
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_content)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        data = json.loads(cleaned)
        
        mermaid_code = data.get("mermaid_code", "")
        # Basic cleanup for mermaid formatting
        mermaid_code = mermaid_code.replace("\\n", "\n").strip()
        mermaid_code = _sanitise_mermaid(mermaid_code)
        
        if not mermaid_code.startswith(("graph", "flowchart", "sequenceDiagram", "stateDiagram", "classDiagram")):
            mermaid_code = f"graph TD\n  A[{title or 'Start'}] --> B[Process Content]"

        return {
            "mermaid_code": mermaid_code,
            "diagram_title": data.get("diagram_title", title or "Process Diagram"),
        }
    except Exception as e:
        logger.error("Failed to generate Mermaid diagram: %s", e)
        # Fallback simple diagram
        safe_title = re.sub(r"[^\w\s]", "", title[:30]) or "Start"
        return {
            "mermaid_code": f"graph TD\n  A[{safe_title}] --> B[Analyze Details] --> C[Key Outcome]",
            "diagram_title": title or "Process Diagram",
        }
