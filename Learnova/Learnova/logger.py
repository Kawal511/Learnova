"""
Centralized logging configuration for Learnova.
Writes error-level (and above) messages to logs/error.log.
"""

import logging
import os

# Ensure the logs directory exists
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "error.log")

# ── Configure root logger ────────────────────────────────────────────────────
logger = logging.getLogger("learnova")
logger.setLevel(logging.DEBUG)

# File handler — captures ERROR and above into error.log
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
)

# Console handler — INFO and above for dev visibility
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(
    logging.Formatter("%(levelname)s: %(message)s")
)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
