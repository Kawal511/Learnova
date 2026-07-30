"""
AI Diagram Generator Module for Learnova
Generates valid Mermaid.js code for flowcharts, sequence diagrams, and process workflows.
"""

import json
import os
import re
import time
from dotenv import load_dotenv
from providers import GroqProvider
from logger import logger
from typing import Optional

load_dotenv()

# Module-level singleton – reuse one httpx connection pool for all diagram calls.
_groq_provider: Optional[GroqProvider] = None


def _get_groq_provider(timeout: float = 10.0) -> Optional[GroqProvider]:
    """Return a cached GroqProvider, or None if GROQ_API_KEY is missing."""
    global _groq_provider
    if _groq_provider is None:
        try:
            _groq_provider = GroqProvider(timeout=timeout)
        except Exception as e:
            logger.warning("Could not initialise GroqProvider for diagrams: %s", e)
            return None
    return _groq_provider

SYSTEM_PROMPT = (
    "You are an expert educational visual designer. "
    "Convert the raw educational content into a valid, concise Mermaid.js diagram definition. "
    "Choose graph TD or graph LR for flowcharts, or sequenceDiagram for sequential interactions. "
    "Keep node labels brief (max 5-7 words per node). "
    "Do NOT use special characters or unescaped quotes in node labels. "
    "Return ONLY valid JSON in this format: "
    '{"mermaid_code": "graph TD\\n  A[Step 1] --> B[Step 2]", "diagram_title": "..."}'
)

def generate_mermaid_diagram(text: str, title: str = "") -> dict:
    """
    Generate Mermaid.js code for process/workflow text.
    """
    try:
        provider = _get_groq_provider(timeout=10.0)
        if provider is None:
            raise ValueError("GroqProvider not available")
        raw_content = provider.generate(
            prompt=f"Title: {title}\nContent:\n{text}",
            system_prompt=SYSTEM_PROMPT,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=600,
            timeout=10.0,
        )
        if not raw_content or not raw_content.strip():
            raise ValueError("Empty Groq response for diagram")
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
