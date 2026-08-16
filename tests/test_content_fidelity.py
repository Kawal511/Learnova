"""
Regressions for content fidelity — the defects visible in a real generated
deck: butchered metrics, leaked markdown, restated bullets, generic card
headings, and content deleted before the density stage could paginate it.
"""

from __future__ import annotations

import pytest

from learnova.ai.diagram_gen import _sanitise_mermaid
from learnova.ai.layout_router import _restore_dropped_points
from learnova.pipeline.density import PROFILES, _chunk
from learnova.pipeline.visual_planner import extract_quantity
from learnova.rendering.ppt_builder import _split_card_label
from learnova.textutils import (
    clean_bullet,
    dedupe_bullets,
    is_redundant,
    strip_inline_markdown,
    truncate_words,
)


class TestQuantityExtraction:
    @pytest.mark.parametrize("text,expected", [
        ("is considering investing $250,000 in a business", "$250,000"),
        ("an initial investment of ₹50,000", "₹50,000"),
        ("Initial Investment = ₹10,000", "₹10,000"),
        ("returns of 12.5% annually", "12.5%"),
        ("Expected life = 5 years", "5 years"),
    ])
    def test_keeps_the_whole_figure(self, text, expected):
        assert extract_quantity(text) == expected

    def test_thousands_separator_is_not_a_cut_point(self):
        # The old `\d+` pattern headlined "$250,000" as "250".
        assert extract_quantity("$250,000") != "250"

    @pytest.mark.parametrize("text", [
        "n/a", "The rate at which the NPV equals zero.", "", "no digits here",
    ])
    def test_no_quantity_returns_empty(self, text):
        assert extract_quantity(text) == ""


class TestMarkdownLeakage:
    def test_balanced_emphasis_removed(self):
        assert strip_inline_markdown("**Resource Allocation:** Ensures use") == \
            "Resource Allocation: Ensures use"

    def test_unbalanced_marker_removed(self):
        # Extraction cuts sentences between the opening and closing "**".
        assert "*" not in strip_inline_markdown("Expected **life = 5 years")

    def test_orphan_marker_removed(self):
        assert strip_inline_markdown("Strategic Growth:* Helps achieve") == \
            "Strategic Growth: Helps achieve"

    def test_continuation_backslash_removed(self):
        assert "\\" not in strip_inline_markdown("₹50,000.\\ Expected life")

    def test_multiplication_survives(self):
        # An intra-word asterisk is arithmetic, not markdown.
        assert strip_inline_markdown("Area = 3*4 metres") == "Area = 3*4 metres"

    def test_list_marker_and_heading_hash_removed(self):
        assert clean_bullet("### - Cash Flows") == "Cash Flows"


class TestTruncation:
    def test_cuts_on_a_word_boundary(self):
        out = truncate_words("is considering investing in a business venture", 20)
        assert not out.rstrip("…").endswith(("busine", "ventur"))

    def test_short_text_untouched(self):
        assert truncate_words("Short line", 40) == "Short line"


class TestRestatement:
    def test_title_repeat_is_redundant(self):
        assert is_redundant("Key Inputs", ["Key Inputs for Capital Budgeting"])

    def test_distinct_points_are_kept(self):
        assert not is_redundant("Cost of Capital matters", ["Project Life is long"])

    def test_dedupe_drops_title_fragments(self):
        out = dedupe_bullets([
            "Key Inputs for Capital Budgeting Decisions",
            "Key Inputs",
            "Capital Budgeting Decisions",
            "Example: Amazon's warehouse decision",
        ])
        assert len(out) == 2


class TestCardHeadings:
    @pytest.mark.parametrize("text,label", [
        ("Definition: The process of identifying projects", "DEFINITION"),
        ("Cash Flows: Estimated future inflows", "CASH FLOWS"),
        ("Strategic Growth:* Helps achieve goals", "STRATEGIC GROWTH"),
    ])
    def test_real_label_is_promoted(self, text, label):
        assert _split_card_label(text, "01")[0] == label

    def test_schema_word_is_peeled_off(self):
        # Models echo the field name: "Label: Cash Flows - Estimated inflows".
        head, body = _split_card_label("Label: Cash Flows - Estimated inflows", "01")
        assert head == "CASH FLOWS"
        assert "Estimated" in body

    def test_unlabelled_text_falls_back(self):
        head, body = _split_card_label("Capital budgeting uses scarce resources", "01")
        assert head == "01"
        assert body.startswith("Capital budgeting")

    def test_a_whole_clause_is_not_a_label(self):
        head, _ = _split_card_label(
            "Because the project runs for many years and costs a lot: plan ahead", "02")
        assert head == "02"


class TestContentPreservation:
    def test_dropped_points_are_restored(self):
        source = ("Light absorption occurs in the thylakoid membranes. "
                  "Water photolysis splits water into oxygen. "
                  "Carbon fixation happens in the stroma. "
                  "Temperature above thirty five degrees reduces efficiency.")
        summarised = ["Light absorption occurs in the thylakoid membranes"]
        out = _restore_dropped_points(summarised, source)
        assert len(out) >= 4

    def test_already_complete_output_is_unchanged(self):
        source = "Alpha covers the first idea. Beta covers the second idea."
        bullets = ["Alpha covers the first idea", "Beta covers the second idea"]
        assert _restore_dropped_points(bullets, source) == bullets

    def test_no_source_leaves_bullets_alone(self):
        assert _restore_dropped_points(["only point"], "") == ["only point"]


class TestPagination:
    def test_last_page_is_not_an_orphan(self):
        # 5 items at a budget of 4 should be 3+2, never 4+1.
        pages = _chunk(list(range(5)), 4)
        assert [len(p) for p in pages] == [3, 2]

    def test_exact_fit_stays_one_page(self):
        assert len(_chunk(list(range(4)), 4)) == 1

    def test_nothing_is_lost(self):
        for n in range(1, 20):
            pages = _chunk(list(range(n)), 4)
            assert sum(len(p) for p in pages) == n

    def test_empty_input(self):
        assert _chunk([], 4) == []


class TestMermaidRepair:
    def test_stray_arrow_head_removed(self):
        out = _sanitise_mermaid("graph TD\n  A[X] -->|Calculate|> B[Y]")
        assert "|>" not in out
        assert "-->|Calculate|" in out

    def test_newlines_preserved(self):
        out = _sanitise_mermaid("graph TD\n  A --> B\n  B --> C")
        assert out.count("\n") == 2

    def test_valid_diagram_untouched(self):
        code = "graph TD\n A[Start] --> B[End]"
        assert _sanitise_mermaid(code) == code
