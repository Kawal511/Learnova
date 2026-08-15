"""
Subprocess Builder – spawns build_worker.py in a clean subprocess.

Uses subprocess.run() (which exec()s a fresh Python interpreter) — this avoids
the macOS segfault (exit 139) that occurs when multiprocessing fork() copies
live httpx/Groq connection-pool threads from the parent into the child.

Key fix: start_new_session=True fully isolates the child's process group from
the parent, so any signal in the child cannot propagate back and crash Streamlit.
"""

import os
import sys
import json
import pickle
import base64
import subprocess
import logging

logger = logging.getLogger(__name__)

# Path to the worker script (same directory as this file)
_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build_worker.py")
# Use the same Python interpreter that is running the app
_PYTHON = sys.executable


def _clean_env() -> dict:
    """
    Return a copy of the current environment with all threading/plugin safety
    flags set. This prevents the child process from inheriting broken state.
    """
    return {
        **os.environ,
        # Pydantic: disable plugin scanning (prevents Anaconda metadata timeout)
        "PYDANTIC_DISABLE_PLUGINS": "1",
        # Threading: single thread per library to avoid OpenMP conflicts
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "KMP_DUPLICATE_LIB_OK": "TRUE",
        # macOS: prevent Obj-C runtime re-init crash in forked processes
        "OBJC_DISABLE_INITIALIZE_FORK_SAFETY": "YES",
        # HuggingFace tokenizers: prevent parallel tokenizer warnings
        "TOKENIZERS_PARALLELISM": "false",
    }


import tempfile

def _run_worker(mode: str, deck: list, topic_title: str, theme_id: str,
                theme_spec: dict | None = None) -> bytes:
    """
    Serialize the deck to a temporary disk file, spawn build_worker.py,
    and read output from a temporary disk file.

    Using disk temporary files instead of OS pipes avoids pipe buffer memory
    exhaustion on macOS, which causes zsh: segmentation fault (exit 139)
    when passing large deck payloads with raw image bytes.
    """
    deck_b64 = base64.b64encode(pickle.dumps(deck)).decode("utf-8")
    payload = {
        "mode": mode,
        "deck_b64": deck_b64,
        "topic_title": topic_title,
        "theme_id": theme_id,
        "theme_spec": theme_spec,
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix="_in.json", delete=False) as in_tmp:
        json.dump(payload, in_tmp)
        in_path = in_tmp.name

    with tempfile.NamedTemporaryFile(mode="w", suffix="_out.json", delete=False) as out_tmp:
        out_path = out_tmp.name

    try:
        result = subprocess.run(
            [_PYTHON, _WORKER_SCRIPT, in_path, out_path],
            capture_output=True,
            text=True,
            timeout=180,  # 3 min max for large decks
            env=_clean_env(),
            start_new_session=True,  # isolate child's process group – prevents signal propagation back to Streamlit
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Build worker ({mode}) timed out after 180 seconds")
    except FileNotFoundError:
        raise RuntimeError(
            f"Build worker script not found: {_WORKER_SCRIPT}. "
            "Ensure utils/build_worker.py exists."
        )
    finally:
        if os.path.exists(in_path):
            try:
                os.unlink(in_path)
            except OSError:
                pass

    try:
        stderr = result.stderr.strip()
        if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
            logger.error("Build worker stderr: %s", stderr)
            raise RuntimeError(f"Build worker ({mode}) failed (exit {result.returncode}): {stderr[:600]}")

        with open(out_path, "r") as f:
            output = json.load(f)
    finally:
        if os.path.exists(out_path):
            try:
                os.unlink(out_path)
            except OSError:
                pass

    if output.get("error"):
        tb = output.get("traceback", "")
        logger.error("Build worker error traceback:\n%s", tb)
        raise RuntimeError(f"Build worker ({mode}) error: {output['error']}")

    raw_b64 = output.get("result_b64")
    if not raw_b64:
        raise RuntimeError(f"Build worker ({mode}) returned empty result_b64")

    return base64.b64decode(raw_b64)


def build_pptx_safe(deck: list, topic_title: str = "presentation", theme_id: str = "auto",
                    theme_spec: dict | None = None) -> bytes:
    """Build PPTX deck safely via worker subprocess to isolate C-extensions and prevent macOS segfaults (exit 139)."""
    try:
        return _run_worker("pptx", deck, topic_title, theme_id, theme_spec)
    except Exception as e:
        logger.error("Subprocess build_pptx failed: %s — falling back to in-process builder", e)
        from learnova.rendering.ppt_builder import build_pptx
        return build_pptx(deck, topic_title=topic_title, theme_id=theme_id, theme_spec=theme_spec)


def build_html_safe(deck: list, topic_title: str = "presentation", theme_id: str = "auto",
                    theme_spec: dict | None = None) -> bytes:
    """Build interactive HTML deck safely via worker subprocess to isolate C-extensions and prevent macOS segfaults (exit 139)."""
    try:
        return _run_worker("html", deck, topic_title, theme_id, theme_spec)
    except Exception as e:
        logger.error("Subprocess build_html failed: %s — falling back to in-process builder", e)
        from learnova.rendering.web_deck_builder import build_web_deck
        html_str = build_web_deck(deck, topic_title=topic_title, theme_id=theme_id, theme_spec=theme_spec)
        return html_str.encode("utf-8")
