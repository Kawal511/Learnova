"""
Subprocess Builder – spawns build_worker.py in a clean subprocess.

This avoids macOS segfaults (exit 139) caused by lxml/python-pptx
C-extensions conflicting with FAISS/OpenMP threads in the parent process.
"""

import os
import sys
import json
import pickle
import base64
import subprocess
import logging

logger = logging.getLogger(__name__)

# Path to the worker script
_WORKER_SCRIPT = os.path.join(os.path.dirname(__file__), "build_worker.py")
# Use the same Python interpreter as the current process
_PYTHON = sys.executable


def _run_worker(mode: str, deck: list, topic_title: str, theme_id: str) -> bytes:
    """
    Serialize the deck, spawn build_worker.py in a fresh subprocess,
    and return the raw output bytes (PPTX bytes or HTML utf-8 bytes).
    """
    deck_b64 = base64.b64encode(pickle.dumps(deck)).decode("utf-8")
    payload = json.dumps({
        "mode": mode,
        "deck_b64": deck_b64,
        "topic_title": topic_title,
        "theme_id": theme_id,
    })

    try:
        result = subprocess.run(
            [_PYTHON, _WORKER_SCRIPT],
            input=payload,
            capture_output=True,
            text=True,
            timeout=120,  # 2 min max for large decks
            env={**os.environ, "PYDANTIC_DISABLE_PLUGINS": "1"},
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Build worker ({mode}) timed out after 120 seconds")

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0 or not stdout:
        logger.error("Build worker stderr: %s", stderr)
        raise RuntimeError(f"Build worker ({mode}) failed (exit {result.returncode}): {stderr[:500]}")

    try:
        output = json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error("Build worker stdout: %s", stdout[:200])
        raise RuntimeError(f"Build worker returned invalid JSON: {e}")

    if output.get("error"):
        logger.error("Build worker error: %s", output.get("traceback", ""))
        raise RuntimeError(f"Build worker ({mode}) error: {output['error']}")

    return base64.b64decode(output["result_b64"])


def build_pptx_safe(deck: list, topic_title: str = "presentation", theme_id: str = "auto") -> bytes:
    """Build PPTX in isolated subprocess. Returns raw bytes."""
    return _run_worker("pptx", deck, topic_title, theme_id)


def build_html_safe(deck: list, topic_title: str = "presentation", theme_id: str = "auto") -> bytes:
    """Build HTML in isolated subprocess. Returns utf-8 encoded bytes."""
    return _run_worker("html", deck, topic_title, theme_id)
