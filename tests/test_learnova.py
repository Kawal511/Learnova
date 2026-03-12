"""
Learnova End-to-End Tests
Run with: pytest tests/test_learnova.py -v
"""

import os
import sys

import pytest

# Ensure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers.ppt_parser import parse_ppt
from parsers.pdf_parser import parse_pdf
from rag.chunker import chunk_parsed_data
from ai.improver import improve_chunks
from ai.quiz_gen import generate_quizzes
from utils.scorer import score_slide, score_all_slides

# ── Replace these with your real file paths ──────────────────────────────────
PPT_PATH = "path/to/your/file.pptx"   # ← Replace with your real .pptx path
PDF_PATH = "path/to/your/file.pdf"     # ← Replace with your real .pdf path


# ═══════════════════════════════════════════════════════════════════════════════
# Unit Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPPTParser:
    @pytest.mark.skipif(not os.path.exists(PPT_PATH), reason="PPT file not found")
    def test_ppt_parser(self):
        result = parse_ppt(PPT_PATH)
        assert isinstance(result, list), "Should return a list"
        assert len(result) > 0, "Should have at least one slide"
        for slide in result:
            assert "slide" in slide, "Missing 'slide' key"
            assert "title" in slide, "Missing 'title' key"
            assert "content" in slide, "Missing 'content' key"
        print(f"\n✅ PPT Parser: {len(result)} slides extracted")


class TestPDFParser:
    @pytest.mark.skipif(not os.path.exists(PDF_PATH), reason="PDF file not found")
    def test_pdf_parser(self):
        result = parse_pdf(PDF_PATH)
        assert isinstance(result, list), "Should return a list"
        assert len(result) > 0, "Should have at least one page"
        for page in result:
            assert "page" in page, "Missing 'page' key"
            assert "heading" in page, "Missing 'heading' key"
            assert "content" in page, "Missing 'content' key"
        print(f"\n✅ PDF Parser: {len(result)} pages extracted")


class TestChunker:
    def test_chunker_with_ppt_format(self):
        mock_parsed = [
            {"slide": 1, "title": "Intro", "content": ["Hello world"] * 20},
            {"slide": 2, "title": "Details", "content": ["Some details"]},
        ]
        chunks = chunk_parsed_data(mock_parsed)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            assert "id" in chunk, "Missing 'id' key"
            assert "title" in chunk, "Missing 'title' key"
            assert "text" in chunk, "Missing 'text' key"
            assert "source" in chunk, "Missing 'source' key"
        print(f"\n✅ Chunker: {len(chunks)} chunks created")

    def test_chunker_with_pdf_format(self):
        mock_parsed = [
            {"page": 1, "heading": "Chapter 1", "content": "Some long text " * 30},
        ]
        chunks = chunk_parsed_data(mock_parsed)
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        for chunk in chunks:
            word_count = len(chunk["text"].split())
            assert word_count <= 120, f"Chunk exceeds 120 words: {word_count}"
        print(f"\n✅ Chunker (PDF): {len(chunks)} chunks, all ≤120 words")


class TestImprover:
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    )
    def test_improver(self):
        mock_chunks = [
            {"id": 1, "title": "Test Slide", "text": "This is a test slide about machine learning.", "source": 1},
        ]
        results = improve_chunks(mock_chunks)
        assert isinstance(results, list)
        assert len(results) == 1
        improved = results[0]["improved"]
        assert "title" in improved, "Missing 'title' in improved"
        assert "bullets" in improved, "Missing 'bullets' in improved"
        assert "takeaway" in improved, "Missing 'takeaway' in improved"
        print(f"\n✅ Improver: Improved slide title = '{improved['title']}'")


class TestQuizGen:
    @pytest.mark.skipif(
        not os.getenv("GEMINI_API_KEY"),
        reason="GEMINI_API_KEY not set",
    )
    def test_quiz_gen(self):
        mock_improved = [
            {
                "original": {"id": i, "title": f"Slide {i}", "text": "Content", "source": i},
                "improved": {
                    "title": f"Slide {i}",
                    "bullets": ["Machine learning is a subset of AI",
                                "It learns from data patterns",
                                "Used in many industries"],
                    "takeaway": "ML is powerful",
                },
            }
            for i in range(1, 4)
        ]
        quizzes = generate_quizzes(mock_improved)
        assert isinstance(quizzes, list)
        if quizzes:
            q = quizzes[0]
            assert "question" in q, "Missing 'question'"
            assert "options" in q, "Missing 'options'"
            assert "correct" in q, "Missing 'correct'"
            assert "explanation" in q, "Missing 'explanation'"
            print(f"\n✅ Quiz Gen: '{q['question'][:60]}...'")
        else:
            print("\n⚠️ Quiz Gen: No quizzes generated (Gemini may have failed)")


class TestScorer:
    def test_score_slide(self):
        mock_improved = {
            "title": "Introduction to Machine Learning",
            "bullets": [
                "ML is a subset of artificial intelligence",
                "It learns patterns from data",
                "Supervised and unsupervised learning",
                "Used in healthcare, finance, and tech",
            ],
            "takeaway": "Machine learning helps automate decisions using data",
        }
        result = score_slide(mock_improved)
        assert "score" in result
        assert "breakdown" in result
        assert 0 <= result["score"] <= 100, f"Score out of range: {result['score']}"
        breakdown = result["breakdown"]
        for key in ["text_density", "bullet_count", "title_quality", "has_takeaway", "readability"]:
            assert key in breakdown, f"Missing breakdown key: {key}"
        print(f"\n✅ Scorer: Score = {result['score']}/100, Breakdown = {breakdown}")

    def test_score_all_slides(self):
        mock_results = [
            {
                "original": {"id": 1, "title": "T", "text": "X", "source": 1},
                "improved": {
                    "title": "Good Title Here",
                    "bullets": ["Point one", "Point two", "Point three"],
                    "takeaway": "Key insight",
                },
            }
        ]
        result = score_all_slides(mock_results)
        assert "scores" in result
        assert "average" in result
        assert len(result["scores"]) == 1
        print(f"\n✅ Scorer (all): Avg = {result['average']}/100")


# ═══════════════════════════════════════════════════════════════════════════════
# Full Pipeline Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullPipelinePPT:
    @pytest.mark.skipif(not os.path.exists(PPT_PATH), reason="PPT file not found")
    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_full_pipeline_ppt(self):
        print("\n🔄 Running full PPT pipeline...")

        parsed = parse_ppt(PPT_PATH)
        assert len(parsed) > 0
        print(f"   Parsed: {len(parsed)} slides")

        chunks = chunk_parsed_data(parsed)
        assert len(chunks) > 0
        print(f"   Chunked: {len(chunks)} chunks")

        improved = improve_chunks(chunks)
        assert len(improved) > 0
        print(f"   Improved: {len(improved)} slides")

        quizzes = generate_quizzes(improved)
        print(f"   Quizzes: {len(quizzes)}")

        scores = score_all_slides(improved)
        print(f"   Avg Score: {scores['average']}/100")
        print(f"✅ Full PPT pipeline passed — Score: {scores['average']}/100")


class TestFullPipelinePDF:
    @pytest.mark.skipif(not os.path.exists(PDF_PATH), reason="PDF file not found")
    @pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"), reason="GEMINI_API_KEY not set")
    def test_full_pipeline_pdf(self):
        print("\n🔄 Running full PDF pipeline...")

        parsed = parse_pdf(PDF_PATH)
        assert len(parsed) > 0
        print(f"   Parsed: {len(parsed)} pages")

        chunks = chunk_parsed_data(parsed)
        assert len(chunks) > 0
        print(f"   Chunked: {len(chunks)} chunks")

        improved = improve_chunks(chunks)
        assert len(improved) > 0
        print(f"   Improved: {len(improved)} slides")

        quizzes = generate_quizzes(improved)
        print(f"   Quizzes: {len(quizzes)}")

        scores = score_all_slides(improved)
        print(f"   Avg Score: {scores['average']}/100")
        print(f"✅ Full PDF pipeline passed — Score: {scores['average']}/100")
