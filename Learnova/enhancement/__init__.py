"""
Learnova Enhancement Layer Package
=====================================
Day 7: Educational Content Enhancement Engine.

Exports the primary entry point (ContentEnhancementEngine)
and the output schema (EnhancedSlide).
"""

from enhancement.engine import ContentEnhancementEngine
from enhancement.schema import EnhancedSlide

__all__ = [
    "ContentEnhancementEngine",
    "EnhancedSlide",
]
