"""Deck rendering: themes, PPTX generation, HTML web decks, subprocess isolation."""

from learnova.rendering.theme_engine import (
    DEFAULT_FONT_ID,
    FONT_CHOICES,
    THEMES,
    ColorPalette,
    apply_font,
    auto_detect_theme,
    build_custom_theme,
    get_theme,
    readable_text_hex,
    select_slide_layout,
)

__all__ = [
    "THEMES",
    "FONT_CHOICES",
    "DEFAULT_FONT_ID",
    "ColorPalette",
    "auto_detect_theme",
    "build_custom_theme",
    "apply_font",
    "readable_text_hex",
    "get_theme",
    "select_slide_layout",
]
