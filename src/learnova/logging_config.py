"""
Centralized logging configuration for Learnova.

Writes ERROR and above to ``<project_root>/logs/error.log`` and INFO and above
to the console. Handlers are attached exactly once, so importing this module
from several places (as the whole codebase does) will not duplicate output.
"""

import logging

from learnova.config import LOG_DIR

LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "error.log"

logger = logging.getLogger("learnova")
logger.setLevel(logging.DEBUG)

# Guard against duplicate handlers on module re-import / Streamlit re-run.
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

# Do not bubble up to the root logger; Streamlit installs its own noisy one.
logger.propagate = False

__all__ = ["logger", "LOG_FILE"]
