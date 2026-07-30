"""
Build Worker – runs build_pptx / build_web_deck in a subprocess
isolated from FAISS/OpenMP C-library threads that cause macOS segfaults.

Called by utils/subprocess_builder.py via multiprocessing with spawn context.
DO NOT import FAISS-dependent modules here.
"""

import os
# Disable any threading that might conflict with lxml/python-pptx
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["PYDANTIC_DISABLE_PLUGINS"] = "1"
# macOS: prevent segfault when Objective-C runtime re-initializes in forked process
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import sys
import json
import pickle
import base64

# Add project root to sys.path (this script lives in utils/, root is one level up)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)



def _build_pptx_worker(deck_b64: str, topic_title: str, theme_id: str) -> str:
    """Build PPTX and return base64-encoded bytes."""
    deck = pickle.loads(base64.b64decode(deck_b64))
    from utils.ppt_builder import build_pptx
    result = build_pptx(deck, topic_title=topic_title, theme_id=theme_id)
    return base64.b64encode(result).decode("utf-8")


def _build_html_worker(deck_b64: str, topic_title: str, theme_id: str) -> str:
    """Build HTML and return base64-encoded utf-8 bytes."""
    deck = pickle.loads(base64.b64decode(deck_b64))
    from utils.web_deck_builder import build_web_deck
    result = build_web_deck(deck, topic_title=topic_title, theme_id=theme_id)
    return base64.b64encode(result.encode("utf-8")).decode("utf-8")


if __name__ == "__main__":
    """
    Entry point when called as a subprocess.
    Args (via command line or stdin):
      sys.argv[1]: path to input JSON file
      sys.argv[2]: path to output JSON file
    """
    in_file = sys.argv[1] if len(sys.argv) > 1 else None
    out_file = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        if in_file and os.path.exists(in_file):
            with open(in_file, "r") as f:
                payload = json.load(f)
        else:
            payload = json.loads(sys.stdin.read())

        mode = payload["mode"]
        deck_b64 = payload["deck_b64"]
        topic_title = payload.get("topic_title", "presentation")
        theme_id = payload.get("theme_id", "auto")

        if mode == "pptx":
            result_b64 = _build_pptx_worker(deck_b64, topic_title, theme_id)
        elif mode == "html":
            result_b64 = _build_html_worker(deck_b64, topic_title, theme_id)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        out_data = {"result_b64": result_b64, "error": None}
        if out_file:
            with open(out_file, "w") as f:
                json.dump(out_data, f)
        else:
            print(json.dumps(out_data))
        sys.exit(0)

    except Exception as e:
        import traceback
        err_data = {"result_b64": None, "error": str(e), "traceback": traceback.format_exc()}
        if out_file:
            with open(out_file, "w") as f:
                json.dump(err_data, f)
        else:
            print(json.dumps(err_data))
        sys.exit(1)
