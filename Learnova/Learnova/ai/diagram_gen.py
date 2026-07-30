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

load_dotenv()

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
        provider = GroqProvider(timeout=10.0)
        raw_content = provider.generate(
            prompt=f"Title: {title}\nContent:\n{text}",
            system_prompt=SYSTEM_PROMPT,
            model="llama-3.1-8b-instant",
            temperature=0.3,
            max_tokens=600,
            timeout=10.0,
        )
        match = re.search(r"\{.*\}", raw_content, re.DOTALL)
        if match:
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
