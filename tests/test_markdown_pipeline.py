"""
Tests for the markdown IR, the chunker's markdown handling, and the
UI-agnostic pipeline orchestrator.

These cover the restructure: markdown as the single intermediate
representation, and a pipeline that runs with no frontend attached.
"""

from __future__ import annotations

import pytest

from learnova.parsers.markdown_converter import (
    MarkdownDocument,
    from_typed_text,
    sections_to_parsed_dicts,
    split_sections,
)
from learnova.pipeline.orchestrator import (
    STAGES,
    PipelineConfig,
    PipelineResult,
    generate,
)
from learnova.rag.chunker import _split_into_paragraphs, chunk_parsed_data

SAMPLE_MD = """## Chapter 1: Photosynthesis
- Step 1: Light absorption by chlorophyll
- Step 2: Water photolysis splits H2O
- Step 3: Carbon fixation in the Calvin cycle

Research shows 84% efficiency at 25 degrees C.

## Chapter 2: Comparison of Stages
- Light reactions occur in thylakoid membranes
- Dark reactions occur in the stroma
"""


class TestSectionSplitting:
    def test_splits_on_h2_boundaries(self):
        sections = split_sections(SAMPLE_MD, max_level=2)
        assert len(sections) == 2
        assert sections[0]["title"] == "Chapter 1: Photosynthesis"
        assert sections[1]["title"] == "Chapter 2: Comparison of Stages"

    def test_deeper_headings_stay_inside_their_section(self):
        """A sub-heading stays in its parent section, but loses its '#' markers.

        Left in, the literal "### Nested" rendered as bullet text on the slide.
        """
        md = "## Top\n### Nested\n- a\n## Second\n- b\n"
        sections = split_sections(md, max_level=2)
        assert len(sections) == 2
        assert "Nested" in sections[0]["text"]
        assert "###" not in sections[0]["text"]

    def test_content_before_first_heading_is_kept(self):
        sections = split_sections("intro prose\n\n## Real Heading\n- x\n", max_level=2)
        assert any("intro prose" in s["text"] for s in sections)

    def test_empty_markdown_yields_no_sections(self):
        assert split_sections("   \n\n  \n") == []

    def test_sections_to_parsed_dicts_shape(self):
        dicts = sections_to_parsed_dicts(split_sections(SAMPLE_MD))
        assert len(dicts) == 2
        for i, d in enumerate(dicts):
            assert d["id"] == i
            assert d["slide"] == i + 1
            assert d["page"] == i + 1
            assert isinstance(d["content"], list)
            assert d["title"]


class TestTypedInput:
    def test_typed_text_becomes_markdown_document(self):
        doc = from_typed_text("Just some prose.", source_name="My Syllabus")
        assert isinstance(doc, MarkdownDocument)
        assert doc.converter == "typed"
        assert doc.source_type == "typed"
        # A heading is injected so section splitting has an anchor.
        assert doc.markdown.startswith("## My Syllabus")

    def test_existing_headings_are_not_double_wrapped(self):
        doc = from_typed_text("## Already Has One\n- a\n")
        assert doc.markdown.count("## Already Has One") == 1
        assert not doc.markdown.startswith("## Typed Syllabus")


class TestChunkerMarkdownHandling:
    def test_list_items_stay_separate_lines(self):
        paragraphs = _split_into_paragraphs(SAMPLE_MD)
        list_para = next(p for p in paragraphs if "Step 1" in p)
        assert list_para.count("\n") == 2, "three bullets should remain three lines"

    def test_list_markers_are_stripped(self):
        paragraphs = _split_into_paragraphs(SAMPLE_MD)
        for para in paragraphs:
            for line in para.splitlines():
                assert not line.lstrip().startswith("- ")
                assert not line.lstrip().startswith("* ")

    def test_numbered_lists_are_handled(self):
        paragraphs = _split_into_paragraphs("## T\n1. first\n2. second\n")
        joined = "\n".join(paragraphs)
        assert "first" in joined and "second" in joined
        assert "1." not in joined

    def test_prose_is_still_joined_into_one_paragraph(self):
        """Consecutive prose lines collapse; a heading opens the paragraph."""
        paragraphs = _split_into_paragraphs("## T\nline one\nline two\n")
        prose = [p for p in paragraphs if "line one" in p][0]
        assert "\n" not in prose, "prose must not keep line breaks"
        assert prose == "T line one line two"

    def test_short_paragraph_preserves_newlines_through_chunking(self):
        dicts = sections_to_parsed_dicts(split_sections(SAMPLE_MD))
        chunks = chunk_parsed_data(dicts)
        steps = [c for c in chunks if "Step 1" in c["text"]]
        assert steps, "expected a chunk containing the step list"
        assert "\n" in steps[0]["text"], "newlines must survive chunking"


class TestPipeline:
    def test_stage_list_is_stable(self):
        assert STAGES[0] == "convert"
        assert "layout" in STAGES
        assert STAGES[-1] == "build_html"

    def test_generate_runs_without_any_api_key(self):
        """The pipeline must degrade to heuristics, not crash, with no LLM."""
        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        config = PipelineConfig(
            enable_vision_ocr=False, build_pptx=False, build_html=False
        )
        result = generate(doc, config=config)

        assert isinstance(result, PipelineResult)
        assert result.final_deck, "a deck must be produced even with no LLM"
        for entry in result.final_deck:
            assert "improved" in entry
            assert entry["improved"].get("title")

    def test_progress_callback_receives_every_stage(self):
        seen: list[tuple[str, str]] = []

        def progress(stage, status, fraction, detail):
            seen.append((stage, status))
            assert 0.0 <= fraction <= 1.0

        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        generate(
            doc,
            config=PipelineConfig(
                enable_vision_ocr=False, build_pptx=False, build_html=False
            ),
            progress=progress,
        )

        reported = {name for name, _ in seen}
        assert reported == set(STAGES), f"missing stages: {set(STAGES) - reported}"

    def test_broken_progress_callback_does_not_kill_the_run(self):
        def exploding(*_args):
            raise RuntimeError("UI blew up")

        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        result = generate(
            doc,
            config=PipelineConfig(
                enable_vision_ocr=False, build_pptx=False, build_html=False
            ),
            progress=exploding,
        )
        assert result.final_deck

    def test_disabled_builders_are_reported_as_skipped(self):
        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        result = generate(
            doc,
            config=PipelineConfig(
                enable_vision_ocr=False, build_pptx=False, build_html=False
            ),
        )
        by_name = {s.name: s for s in result.stages}
        assert by_name["build_pptx"].status == "skipped"
        assert by_name["build_html"].status == "skipped"
        assert result.pptx_bytes is None

    def test_summary_is_json_safe(self):
        import json

        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        result = generate(
            doc,
            config=PipelineConfig(
                enable_vision_ocr=False, build_pptx=False, build_html=False
            ),
        )
        # Must not raise: the summary deliberately excludes raw bytes.
        json.dumps(result.summary())


class TestArtifactBuilding:
    """The PPTX/HTML builders run in a separate interpreter; verify the hop."""

    @pytest.mark.slow
    def test_builders_produce_real_artifacts(self):
        doc = from_typed_text(SAMPLE_MD, source_name="Test Doc")
        result = generate(
            doc,
            config=PipelineConfig(
                enable_vision_ocr=False,
                build_pptx=True,
                build_html=True,
                theme_id="brutalist_neon",
            ),
        )
        assert result.pptx_bytes and result.pptx_bytes[:2] == b"PK"
        assert result.html_bytes and b"reveal" in result.html_bytes.lower()
