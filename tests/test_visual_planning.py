"""
Tests for AnyDoc conversion, image anchoring, and deterministic visual planning.

Covers the three behaviours added on top of the markdown IR:
  * AnyDoc drives text extraction, native parsers supply image bytes
  * images anchor to the section that discusses them, not to a list index
  * flowcharts / tables / KPI cards are derived from text with no LLM
"""

from __future__ import annotations

import pathlib

import pytest

from learnova.parsers.markdown_converter import (
    anchor_assets,
    anydoc_available,
    attach_assets_to_units,
    convert_to_markdown,
    from_typed_text,
    sections_to_parsed_dicts,
    split_sections,
    strip_asset_placeholders,
)
from learnova.pipeline.visual_planner import plan_visual
from learnova.rag.chunker import chunk_parsed_data

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
IMAGE_DECK = FIXTURES / "sample_with_images.pptx"

STEPS_MD = """## Learnova Processing Pipeline
- Step 1: Upload raw PPTX or PDF textbook
- Step 2: Parse document layout and embedded diagrams
- Step 3: Route content through the AI Layout Router
- Step 4: Generate quizzes and export the deck
"""

STATS_MD = """## Engagement Benchmark Metrics
- Student retention improved by 47% after redesign
- Average attention span increased 2.3x
- Quiz completion rate reached 88%
"""


# ── AnyDoc placeholder stripping ──────────────────────────────────────────────
class TestAssetPlaceholderStripping:
    def test_bare_image_filename_is_removed(self):
        md = "## Title\n\nSome body text.\n\nimage.png\n"
        assert "image.png" not in strip_asset_placeholders(md)
        assert "Some body text." in strip_asset_placeholders(md)

    def test_markdown_image_syntax_is_removed(self):
        md = "## T\n\n![diagram](asset://0)\n\nreal text\n"
        out = strip_asset_placeholders(md)
        assert "![diagram]" not in out
        assert "real text" in out

    def test_prose_mentioning_a_filename_is_kept(self):
        """Only whole-line placeholders go; a sentence must survive."""
        md = "## T\n\nExport the chart as image.png before printing.\n"
        assert "image.png" in strip_asset_placeholders(md)

    def test_blank_runs_are_collapsed(self):
        md = "## T\n\nbody\n\nimage.png\n\n\n\nmore\n"
        assert "\n\n\n" not in strip_asset_placeholders(md)


# ── Image anchoring ───────────────────────────────────────────────────────────
class TestImageAnchoring:
    @staticmethod
    def _sections():
        return [
            {"title": "Photosynthesis Overview", "level": 2, "text": "Light to energy."},
            {"title": "Chloroplast Structure", "level": 2, "text": "Thylakoid grana stacks."},
            {"title": "Carbon Cycle", "level": 2, "text": "Carbon moves through oceans."},
        ]

    def test_exact_title_match_wins(self):
        assets = [{"unit_index": 99, "unit_title": "Carbon Cycle", "unit_text": ""}]
        assert anchor_assets(self._sections(), assets)[0][0] == 2

    def test_survives_reordering(self):
        """Position must not decide the anchor — content must."""
        sections = list(reversed(self._sections()))
        assets = [{"unit_index": 1, "unit_title": "Chloroplast Structure", "unit_text": ""}]
        index = anchor_assets(sections, assets)[0][0]
        assert sections[index]["title"] == "Chloroplast Structure"

    def test_text_similarity_when_title_was_edited(self):
        assets = [{
            "unit_index": 0,
            "unit_title": "Slide 3 (renamed by user)",
            "unit_text": "Carbon moves through oceans and the atmosphere.",
        }]
        assert anchor_assets(self._sections(), assets)[0][0] == 2

    def test_positional_fallback_when_nothing_matches(self):
        assets = [{"unit_index": 1, "unit_title": "zzz", "unit_text": "qqq www eee"}]
        assert anchor_assets(self._sections(), assets)[0][0] == 1

    def test_no_sections_or_no_assets_is_safe(self):
        assert anchor_assets([], [{"unit_title": "x"}]) == []
        assert anchor_assets(self._sections(), []) == []

    def test_attach_sets_image_and_images(self):
        sections = self._sections()
        units = sections_to_parsed_dicts(sections)
        assets = [
            {"unit_index": 1, "unit_title": "Chloroplast Structure", "unit_text": "", "bytes": b"a"},
            {"unit_index": 1, "unit_title": "Chloroplast Structure", "unit_text": "", "bytes": b"b"},
        ]
        assert attach_assets_to_units(units, sections, assets) == 2
        assert units[1]["image"]["bytes"] == b"a"
        assert len(units[1]["images"]) == 2
        assert "image" not in units[0]


# ── Chunker: one image per unit ───────────────────────────────────────────────
class TestImageNotDuplicatedAcrossChunks:
    def test_image_attaches_to_first_chunk_only(self):
        """Otherwise the renderer emits one duplicate figure slide per paragraph."""
        units = [{
            "id": 0, "slide": 1, "title": "T",
            "text": "First paragraph here.\n\nSecond paragraph here.",
            "image": {"bytes": b"img", "ext": "png"},
        }]
        chunks = chunk_parsed_data(units)
        assert len(chunks) >= 2
        with_image = [c for c in chunks if c.get("image")]
        assert len(with_image) == 1


# ── Deterministic visual planning ─────────────────────────────────────────────
class TestVisualPlanner:
    def test_ordered_steps_become_a_flowchart(self):
        planned = plan_visual("Learnova Processing Pipeline", STEPS_MD.split("\n", 1)[1])
        assert planned is not None
        assert planned["layout_type"] == "FLOWCHART"
        assert planned["visual_source"] == "intelligence"
        assert len(planned["bullets"]) >= 3

    def test_flowchart_mermaid_is_derived_from_real_steps(self):
        planned = plan_visual("Learnova Processing Pipeline", STEPS_MD.split("\n", 1)[1])
        mermaid = planned["mermaid_code"]
        assert mermaid.startswith("graph ")
        assert "-->" in mermaid
        assert "Upload" in mermaid, "nodes must come from the content, not a placeholder"
        assert "Execute Steps" not in mermaid, "old hardcoded placeholder must be gone"

    def test_mermaid_labels_are_bracket_safe(self):
        planned = plan_visual("P", "- Step 1: Use [brackets] and (parens)\n"
                                   "- Step 2: Pipe | char\n- Step 3: Done\n")
        mermaid = planned["mermaid_code"]
        body = mermaid.split("\n", 1)[1]
        for forbidden in ("[brackets]", "(parens)"):
            assert forbidden not in body

    def test_statistics_become_a_metric_with_a_real_number(self):
        planned = plan_visual("Engagement Benchmark Metrics", STATS_MD.split("\n", 1)[1])
        assert planned is not None
        assert planned["layout_type"] == "METRIC"
        assert planned["metric_value"] != "Key Stat"
        assert any(ch.isdigit() for ch in planned["metric_value"])

    def test_metric_description_is_single_line(self):
        planned = plan_visual("Engagement Benchmark Metrics", STATS_MD.split("\n", 1)[1])
        assert "\n" not in planned["metric_desc"]

    def test_empty_text_returns_none(self):
        assert plan_visual("Title", "") is None
        assert plan_visual("Title", "   \n  ") is None

    def test_unstructured_prose_is_not_forced_into_a_visual(self):
        planned = plan_visual("Musing", "This is a single sentence with no structure.")
        assert planned is None or planned["layout_type"] in {
            "MINIMAL_TEXT", "CARD_GRID", "METRIC", "FLOWCHART", "TABLE"
        }


# ── AnyDoc integration ────────────────────────────────────────────────────────
@pytest.mark.skipif(not anydoc_available(), reason="firecrawl-anydoc not installed")
class TestAnyDocIntegration:
    @pytest.mark.skipif(not IMAGE_DECK.exists(), reason="image fixture missing")
    def test_anydoc_supplies_text_and_native_parsers_supply_images(self):
        doc = convert_to_markdown(str(IMAGE_DECK), use_cache=False)
        assert doc.converter.startswith("anydoc")
        assert doc.assets, "images must come from the native parser"
        for asset in doc.assets:
            assert asset["bytes"]
            assert "unit_title" in asset

    @pytest.mark.skipif(not IMAGE_DECK.exists(), reason="image fixture missing")
    def test_no_placeholder_lines_survive_into_sections(self):
        doc = convert_to_markdown(str(IMAGE_DECK), use_cache=False)
        for section in split_sections(doc.markdown, max_level=2):
            for line in section["text"].splitlines():
                assert not line.strip().lower().endswith(".png")

    @pytest.mark.skipif(not IMAGE_DECK.exists(), reason="image fixture missing")
    def test_images_land_on_their_own_slides(self):
        doc = convert_to_markdown(str(IMAGE_DECK), use_cache=False)
        sections = split_sections(doc.markdown, max_level=2)
        units = sections_to_parsed_dicts(sections)
        attach_assets_to_units(units, sections, doc.assets)

        for unit in units:
            image = unit.get("image")
            if image:
                assert image["unit_title"].lower() in unit["title"].lower()


class TestTypedSyllabusGetsVisuals:
    """A typed syllabus has no images, so structure is its only visual source."""

    def test_typed_steps_reach_a_flowchart_through_the_planner(self):
        from learnova.pipeline.visual_planner import enrich_deck

        doc = from_typed_text(STEPS_MD, "Syllabus")
        sections = split_sections(doc.markdown, max_level=2)
        units = sections_to_parsed_dicts(sections)
        chunks = chunk_parsed_data(units)

        deck = [
            {"original": c, "improved": {"layout_type": "MINIMAL_TEXT",
                                         "title": c["title"], "bullets": []}}
            for c in chunks
        ]
        assert enrich_deck(deck) >= 1
        assert any(e["improved"]["layout_type"] == "FLOWCHART" for e in deck)
