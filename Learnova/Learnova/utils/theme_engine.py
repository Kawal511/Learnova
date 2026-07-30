"""
Learnova Presentation Theme Engine
Provides 10 Curated Color Schemes and 10 Slide Design Layout Styles (100+ Template Variations)
for PPTX Decks and HTML5 Web Presentations.
"""

from dataclasses import dataclass
from pptx.dml.color import RGBColor

@dataclass
class ColorPalette:
    id: str
    name: str
    description: str
    bg_hex: str
    bg_rgb: RGBColor
    primary_hex: str
    primary_rgb: RGBColor
    accent_hex: str
    accent_rgb: RGBColor
    card_bg_hex: str
    card_bg_rgb: RGBColor
    text_hex: str
    text_rgb: RGBColor
    subtext_hex: str
    subtext_rgb: RGBColor

# ── 10 Curated Professional Color Palettes ────────────────────────────────────
THEMES = {
    "brutalist_neon": ColorPalette(
        id="brutalist_neon",
        name="Brutalist Neon (Default)",
        description="High-contrast black & neon lime accent for modern tech presentations.",
        bg_hex="#ffffff",
        bg_rgb=RGBColor(255, 255, 255),
        primary_hex="#000000",
        primary_rgb=RGBColor(0, 0, 0),
        accent_hex="#ccff00",
        accent_rgb=RGBColor(204, 255, 0),
        card_bg_hex="#f7f9fa",
        card_bg_rgb=RGBColor(247, 249, 250),
        text_hex="#1a1a1a",
        text_rgb=RGBColor(26, 26, 26),
        subtext_hex="#555555",
        subtext_rgb=RGBColor(85, 85, 85),
    ),
    "midnight_cyber": ColorPalette(
        id="midnight_cyber",
        name="Midnight Cyber",
        description="Dark slate backdrop with luminous cyan and deep navy cards.",
        bg_hex="#0f172a",
        bg_rgb=RGBColor(15, 23, 42),
        primary_hex="#1e293b",
        primary_rgb=RGBColor(30, 41, 59),
        accent_hex="#38bdf8",
        accent_rgb=RGBColor(56, 189, 248),
        card_bg_hex="#1e293b",
        card_bg_rgb=RGBColor(30, 41, 59),
        text_hex="#f8fafc",
        text_rgb=RGBColor(248, 250, 252),
        subtext_hex="#94a3b8",
        subtext_rgb=RGBColor(148, 163, 184),
    ),
    "emerald_academic": ColorPalette(
        id="emerald_academic",
        name="Emerald Academic",
        description="Rich forest emerald and mint green for science & research lectures.",
        bg_hex="#064e3b",
        bg_rgb=RGBColor(6, 78, 59),
        primary_hex="#047857",
        primary_rgb=RGBColor(4, 120, 87),
        accent_hex="#6ee7b7",
        accent_rgb=RGBColor(110, 231, 183),
        card_bg_hex="#065f46",
        card_bg_rgb=RGBColor(6, 95, 70),
        text_hex="#ecfdf5",
        text_rgb=RGBColor(236, 253, 245),
        subtext_hex="#a7f3d0",
        subtext_rgb=RGBColor(167, 243, 208),
    ),
    "swiss_corporate": ColorPalette(
        id="swiss_corporate",
        name="Swiss Corporate Minimalist",
        description="Clean white canvas with bold charcoal typography and red Swiss accents.",
        bg_hex="#ffffff",
        bg_rgb=RGBColor(255, 255, 255),
        primary_hex="#18181b",
        primary_rgb=RGBColor(24, 24, 27),
        accent_hex="#ef4444",
        accent_rgb=RGBColor(239, 68, 68),
        card_bg_hex="#f4f4f5",
        card_bg_rgb=RGBColor(244, 244, 245),
        text_hex="#18181b",
        text_rgb=RGBColor(24, 24, 27),
        subtext_hex="#71717a",
        subtext_rgb=RGBColor(113, 113, 122),
    ),
    "sunset_editorial": ColorPalette(
        id="sunset_editorial",
        name="Sunset Pastel Editorial",
        description="Warm lavender & deep violet tones with gold highlights for humanities.",
        bg_hex="#fff7ed",
        bg_rgb=RGBColor(255, 247, 237),
        primary_hex="#4c1d95",
        primary_rgb=RGBColor(76, 29, 149),
        accent_hex="#f59e0b",
        accent_rgb=RGBColor(245, 158, 11),
        card_bg_hex="#ffedd5",
        card_bg_rgb=RGBColor(255, 237, 213),
        text_hex="#292524",
        text_rgb=RGBColor(41, 37, 36),
        subtext_hex="#78716c",
        subtext_rgb=RGBColor(120, 113, 108),
    ),
    "ocean_tech": ColorPalette(
        id="ocean_tech",
        name="Deep Ocean Tech",
        description="Marine blue background with ice-blue metric containers.",
        bg_hex="#0c4a6e",
        bg_rgb=RGBColor(12, 74, 110),
        primary_hex="#0369a1",
        primary_rgb=RGBColor(3, 105, 161),
        accent_hex="#38bdf8",
        accent_rgb=RGBColor(56, 189, 248),
        card_bg_hex="#075985",
        card_bg_rgb=RGBColor(7, 89, 133),
        text_hex="#f0f9ff",
        text_rgb=RGBColor(240, 249, 255),
        subtext_hex="#bae6fd",
        subtext_rgb=RGBColor(186, 230, 253),
    ),
    "charcoal_gold": ColorPalette(
        id="charcoal_gold",
        name="Charcoal Gold Luxury",
        description="Matte dark charcoal with warm metallic gold accents for executive decks.",
        bg_hex="#1c1917",
        bg_rgb=RGBColor(28, 25, 23),
        primary_hex="#292524",
        primary_rgb=RGBColor(41, 37, 36),
        accent_hex="#eab308",
        accent_rgb=RGBColor(234, 179, 8),
        card_bg_hex="#292524",
        card_bg_rgb=RGBColor(41, 37, 36),
        text_hex="#fef08a",
        text_rgb=RGBColor(254, 240, 138),
        subtext_hex="#d6d3d1",
        subtext_rgb=RGBColor(214, 211, 209),
    ),
    "nordic_slate": ColorPalette(
        id="nordic_slate",
        name="Nordic Clean Slate",
        description="Minimalist cool slate and soft grey tones with crisp typography.",
        bg_hex="#f8fafc",
        bg_rgb=RGBColor(248, 250, 252),
        primary_hex="#1e293b",
        primary_rgb=RGBColor(30, 41, 59),
        accent_hex="#0284c7",
        accent_rgb=RGBColor(2, 132, 199),
        card_bg_hex="#e2e8f0",
        card_bg_rgb=RGBColor(226, 232, 240),
        text_hex="#0f172a",
        text_rgb=RGBColor(15, 23, 42),
        subtext_hex="#475569",
        subtext_rgb=RGBColor(71, 85, 105),
    ),
    "warm_terracotta": ColorPalette(
        id="warm_terracotta",
        name="Warm Terracotta Earth",
        description="Earthy clay, rust red, and cream tones for design & architecture.",
        bg_hex="#fff7ed",
        bg_rgb=RGBColor(255, 247, 237),
        primary_hex="#7c2d12",
        primary_rgb=RGBColor(124, 45, 18),
        accent_hex="#ea580c",
        accent_rgb=RGBColor(234, 88, 12),
        card_bg_hex="#ffedd5",
        card_bg_rgb=RGBColor(255, 237, 213),
        text_hex="#431407",
        text_rgb=RGBColor(67, 20, 7),
        subtext_hex="#9a3412",
        subtext_rgb=RGBColor(154, 52, 18),
    ),
    "glass_indigo": ColorPalette(
        id="glass_indigo",
        name="Glassmorphism Indigo",
        description="Deep indigo with semi-transparent frosted card containers.",
        bg_hex="#1e1b4b",
        bg_rgb=RGBColor(30, 27, 75),
        primary_hex="#312e81",
        primary_rgb=RGBColor(49, 46, 129),
        accent_hex="#818cf8",
        accent_rgb=RGBColor(129, 140, 248),
        card_bg_hex="#3730a3",
        card_bg_rgb=RGBColor(55, 48, 163),
        text_hex="#e0e7ff",
        text_rgb=RGBColor(224, 231, 255),
        subtext_hex="#a5b4fc",
        subtext_rgb=RGBColor(165, 180, 252),
    ),
}

# ── 50 Distinct Slide Layout Variation Patterns ──────────────────────────────
LAYOUT_STYLES = [
    "header_banner",          # 1. Top header banner with crisp content cards
    "floating_cards",         # 2. Floating elevated cards with thick accent left borders
    "split_column",           # 3. Dual panel side-by-side split layout
    "gradient_frame",         # 4. Full outer accent frame border
    "left_pillar",            # 5. Solid colored left sidebar pillar
    "hero_centered",          # 6. Large center stage focus callout block
    "grid_matrix",            # 7. 2x2 grid container boxes
    "minimal_line",           # 8. Clean ultra-thin outline minimal cards
    "pill_header",            # 9. Pill badge tags and rounded pill containers
    "glass_floating",         # 10. Frosted glass look containers
    "timeline_stepper",       # 11. Horizontal numbered timeline flow
    "asymmetric_split",       # 12. 60/40 weighted split column layout
    "triple_pillar_hero",     # 13. 3 tall vertical pillar cards
    "diagonal_accent",        # 14. Diagonal accent header geometry
    "framed_takeaway",        # 15. Central takeaway box with outer highlight frame
    "stat_banner_top",        # 16. Top numeric stat callout banner
    "checkerboard_grid",      # 17. Alternating card background grid
    "floating_glass_stack",   # 18. Stacked vertical cards with drop shadows
    "badge_pill_grid",        # 19. Pill-shaped badge header with grid cards
    "bottom_bar_footer",      # 20. Bottom accent takeaway footer strip
    "vertical_stepper",       # 21. Vertical step-by-step progress cards
    "bento_grid_3col",        # 22. Modern Bento-box 3 column grid
    "dual_tone_cards",        # 23. Alternating high-contrast dual tone cards
    "subtle_shadow_card",     # 24. Soft shadow floating cards
    "accent_left_border",     # 25. Thick 6px left border callout panels
    "accent_top_stripe",      # 26. Top colored stripe accent cards
    "highlight_box_center",   # 27. Highlighted central box focus
    "two_tone_split",         # 28. Top half dark, bottom half light split
    "timeline_horizontal",    # 29. Horizontal process node line
    "quote_hero_box",         # 30. Large quote style key insight hero
    "numbered_list_cards",    # 31. Numbered index badge cards 1, 2, 3
    "full_bleed_accent",      # 32. Full bleed accent background for key slides
    "compact_dense_table",    # 33. Structured compact grid table
    "giant_stat_left",        # 34. Giant stat number on left, text on right
    "giant_stat_right",       # 35. Text on left, giant stat number on right
    "comparison_dual_card",   # 36. Side-by-side vs comparison cards
    "step_flow_horizontal",   # 37. 4 horizontal arrow step cards
    "step_flow_vertical",     # 38. 4 vertical arrow step cards
    "bento_box_large",        # 39. Bento-box main hero + 2 sub cards
    "header_pill_floating",   # 40. Floating top pill header bar
    "left_accent_ribbon",     # 41. Vertical ribbon stripe on left
    "dark_contrast_card",     # 42. Inverted high-contrast dark card
    "light_minimal_card",     # 43. Clean ultra-light minimal container
    "floating_shadow_grid",   # 44. Grid of soft-shadow floating cards
    "pill_stepper_row",       # 45. Row of connected pill step badges
    "top_accent_bar",         # 46. Top header bar with accent line
    "bottom_accent_bar",      # 47. Bottom footer bar with accent line
    "framed_card_matrix",     # 48. Framed matrix container with 4 cards
    "dual_badge_header",      # 49. Header with dual layout and category badges
    "hero_stat_split",        # 50. Split hero stat number + key takeaway box
]

# Map layout types to compatible style candidate pools
LAYOUT_TYPE_POOLS = {
    "FLOWCHART": [
        "step_flow_horizontal", "step_flow_vertical", "timeline_stepper", "vertical_stepper",
        "pill_stepper_row", "timeline_horizontal", "header_banner", "left_pillar", "badge_pill_grid", "accent_top_stripe"
    ],
    "TABLE": [
        "compact_dense_table", "comparison_dual_card", "grid_matrix", "bento_grid_3col",
        "checkerboard_grid", "two_tone_split", "split_column", "framed_card_matrix", "minimal_line", "dual_badge_header"
    ],
    "METRIC": [
        "giant_stat_left", "giant_stat_right", "hero_stat_split", "stat_banner_top",
        "hero_centered", "quote_hero_box", "full_bleed_accent", "dark_contrast_card", "highlight_box_center", "floating_cards"
    ],
    "CARD_GRID": [
        "bento_grid_3col", "bento_box_large", "triple_pillar_hero", "numbered_list_cards",
        "grid_matrix", "checkerboard_grid", "floating_glass_stack", "framed_card_matrix", "floating_shadow_grid", "dual_tone_cards"
    ],
    "MINIMAL_TEXT": [
        "accent_left_border", "light_minimal_card", "pill_header", "glass_floating",
        "asymmetric_split", "diagonal_accent", "framed_takeaway", "bottom_bar_footer", "subtle_shadow_card", "header_pill_floating"
    ],
}

def select_slide_layout(slide_idx: int, layout_type: str, prev_layout_style: str = None) -> str:
    """
    Intelligent layout router algorithm:
    1. Selects candidate pool based on slide content layout_type.
    2. Ensures consecutive slides never reuse the exact same layout style.
    3. Rotates deterministically using slide_idx for reproducible decks.
    """
    l_type = (layout_type or "MINIMAL_TEXT").upper()
    pool = LAYOUT_TYPE_POOLS.get(l_type, LAYOUT_TYPE_POOLS["MINIMAL_TEXT"])
    
    # Pick style based on slide index offset
    chosen_style = pool[slide_idx % len(pool)]
    
    # Avoid exact repetition with previous slide
    if chosen_style == prev_layout_style and len(pool) > 1:
        chosen_style = pool[(slide_idx + 1) % len(pool)]
        
    return chosen_style

def get_theme(theme_id: str) -> ColorPalette:
    """Retrieve theme color palette by ID, defaulting to brutalist_neon."""
    return THEMES.get(theme_id, THEMES["brutalist_neon"])

def auto_detect_theme(topic_title: str) -> ColorPalette:
    """
    Intelligently select matching theme palette based on title keywords.
    """
    title_lower = (topic_title or "").lower()
    
    if any(k in title_lower for k in ["medical", "health", "biology", "science", "nature", "green", "environment"]):
        return THEMES["emerald_academic"]
    elif any(k in title_lower for k in ["cyber", "code", "programming", "software", "tech", "data", "ai", "machine"]):
        return THEMES["midnight_cyber"]
    elif any(k in title_lower for k in ["business", "finance", "corporate", "swiss", "market", "management", "report"]):
        return THEMES["swiss_corporate"]
    elif any(k in title_lower for k in ["history", "art", "literature", "education", "humanities", "editorial"]):
        return THEMES["sunset_editorial"]
    elif any(k in title_lower for k in ["ocean", "water", "cloud", "network", "system", "database"]):
        return THEMES["ocean_tech"]
    elif any(k in title_lower for k in ["executive", "luxury", "gold", "premium", "strategic", "lead"]):
        return THEMES["charcoal_gold"]
    elif any(k in title_lower for k in ["architecture", "design", "warm", "terracotta", "craft"]):
        return THEMES["warm_terracotta"]
    elif any(k in title_lower for k in ["nordic", "clean", "slate", "simple", "minimal"]):
        return THEMES["nordic_slate"]
    elif any(k in title_lower for k in ["glass", "indigo", "modern", "future"]):
        return THEMES["glass_indigo"]
    
    return THEMES["brutalist_neon"]
