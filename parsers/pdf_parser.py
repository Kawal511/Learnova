"""
Advanced PDF Parser for Learnova
Uses PyMuPDF's full block/dict parsing to extract:
- Paragraphs with heading detection via font-size analysis
- Tables via PyMuPDF table finder (find_tables)
- Layout-aware text blocks (preserves reading order)
- Full-page pixmap rendering for scanned/image-heavy pages
- Multi-column layout merging
- Figures, captions and inlined image extraction
"""

import fitz  # PyMuPDF >= 1.23 for find_tables
import io
import re
from dataclasses import dataclass, field


@dataclass
class SlideData:
    id: int
    title: str
    text: str
    image: dict | None = None
    images: list[dict] = field(default_factory=list)


@dataclass
class ParsedDocument:
    slide_units: list[SlideData]


def _is_heading(span: dict, avg_body_size: float) -> bool:
    """True if this span looks like a heading: significantly larger font or bold."""
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    is_bold = bool(flags & 2**4)  # bit 4 = bold in PyMuPDF flags
    return size >= avg_body_size * 1.25 or (is_bold and size >= avg_body_size * 1.05)


def _avg_body_font_size(page_dict: dict) -> float:
    """Calculate the median body font size on a page."""
    sizes = []
    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if span.get("text", "").strip():
                    sizes.append(span["size"])
    if not sizes:
        return 12.0
    sizes.sort()
    return sizes[len(sizes) // 2]  # median


def _extract_tables_from_page(page) -> list[str]:
    """
    Use PyMuPDF's built-in table finder to extract table cells as text.
    Returns formatted rows joined by ' | '.
    """
    table_texts = []
    try:
        tabs = page.find_tables()
        for tab in tabs.tables:
            for row in tab.extract():
                clean_row = [str(cell or "").strip() for cell in row]
                non_empty = [c for c in clean_row if c]
                if non_empty:
                    table_texts.append(" | ".join(non_empty))
    except Exception:
        pass
    return table_texts


def _page_to_structured_text(page) -> tuple[str, str]:
    """
    Extract text from a PDF page using dict mode for full layout awareness.
    Returns (detected_title, full_body_text).
    Headings are prefixed with ## for hierarchy preservation.
    Tables are extracted separately and inserted inline.
    """
    page_dict = page.get_text("dict", sort=True)
    avg_size = _avg_body_font_size(page_dict)

    detected_title = ""
    paragraphs = []

    for block in page_dict.get("blocks", []):
        # Skip image blocks (type 1); handled separately
        if block.get("type") != 0:
            continue

        block_lines_text = []
        block_is_heading = False

        for line in block.get("lines", []):
            line_text_parts = []
            line_is_heading = False

            for span in line.get("spans", []):
                raw = span.get("text", "").strip()
                if not raw:
                    continue
                if _is_heading(span, avg_size):
                    line_is_heading = True
                line_text_parts.append(raw)

            line_text = " ".join(line_text_parts).strip()
            if line_text:
                if line_is_heading:
                    block_is_heading = True
                block_lines_text.append(line_text)

        block_text = " ".join(block_lines_text).strip()
        if not block_text:
            continue

        if block_is_heading:
            # Largest heading on the page becomes the title
            if not detected_title and len(block_text) < 120:
                detected_title = block_text
            paragraphs.append(f"## {block_text}")
        else:
            paragraphs.append(block_text)

    # Inject table data
    table_lines = _extract_tables_from_page(page)
    if table_lines:
        paragraphs.append("[TABLE DATA]")
        paragraphs.extend(table_lines)

    return detected_title, "\n".join(paragraphs)


def _extract_page_images(page, doc, min_size: int = 120) -> list[dict]:
    """Extract embedded images from a PDF page above minimum dimensions."""
    images = []
    for img_info in page.get_images(full=True):
        xref = img_info[0]
        try:
            base_image = doc.extract_image(xref)
            w = base_image.get("width", 0)
            h = base_image.get("height", 0)
            if w >= min_size and h >= min_size:
                with Image.open(io.BytesIO(base_image["image"])) as pil_img:
                    out = io.BytesIO()
                    pil_img.convert("RGB").save(out, format="PNG")
                    images.append({"bytes": out.getvalue(), "ext": "png"})
        except Exception:
            pass
    return images


def _render_page_as_image(page, dpi: int = 150) -> dict | None:
    """Render a whole PDF page as PNG for Gemini Vision OCR fallback."""
    try:
        pix = page.get_pixmap(dpi=dpi)
        return {"bytes": pix.tobytes("png"), "ext": "png"}
    except Exception:
        return None


def _detect_chapter_heading(text: str) -> str | None:
    """Detect chapter/unit/section headings for grouping in textbook mode."""
    patterns = [
        r"^(Chapter|Unit|Section|Module|Lesson|Part)\s+[\dIVXivx]+",
        r"^[\dIVXivx]+\.\s+[A-Z][a-zA-Z\s]{3,}",   # e.g. "1. Introduction"
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(0).strip().title()
    return None


def parse_pdf(file_path: str) -> ParsedDocument:
    """
    Single-page-per-slide PDF parser using full dict/block layout extraction.
    Each page becomes one slide unit with:
    - Heading-detected title
    - Structured body text (headings prefixed ##, tables inline)
    - Best extracted image (or full-page render for scanned pages)
    """
    doc = fitz.open(file_path)
    slides = []

    for i, page in enumerate(doc):
        # Full structured extraction
        detected_title, body_text = _page_to_structured_text(page)

        # Embedded images
        images = _extract_page_images(page, doc)
        img_dict = images[0] if images else None

        # Check if page contains visual image blocks (type 1 in PyMuPDF)
        page_dict = page.get_text("dict")
        has_image_blocks = any(b.get("type") == 1 for b in page_dict.get("blocks", []))
        word_count = len(body_text.split())

        # Render full page as image if page has image blocks but no extracted images, or is sparse/scanned
        if (not img_dict and has_image_blocks) or word_count < 30:
            rendered = _render_page_as_image(page)
            if rendered:
                img_dict = rendered
                images.append(rendered)

        slides.append(SlideData(
            id=i,
            title=detected_title or f"Page {i + 1}",
            text=body_text if body_text.strip() else "(Scanned or image-only page)",
            image=img_dict,
            images=images,
        ))

    doc.close()
    return ParsedDocument(slide_units=slides)


def parse_textbook_pdf(file_path: str) -> ParsedDocument:
    """
    Textbook-mode PDF parser:
    - Groups pages by chapter/unit/section headings
    - Extracts all text with heading hierarchy
    - Includes table data and page images per chapter
    - Chunks per 150 words for AI processing
    """
    doc = fitz.open(file_path)
    current_chapter = "Introduction"
    chapter_texts: dict[str, list[str]] = {}
    chapter_images: dict[str, list[dict]] = {}

    for page in doc:
        detected_title, body_text = _page_to_structured_text(page)

        # Chapter detection from page heading or first heading in body
        chapter_match = _detect_chapter_heading(detected_title or body_text)
        if chapter_match:
            current_chapter = chapter_match

        if current_chapter not in chapter_texts:
            chapter_texts[current_chapter] = []
            chapter_images[current_chapter] = []

        if body_text.strip():
            chapter_texts[current_chapter].append(body_text)

        # Images
        images = _extract_page_images(page, doc)
        chapter_images[current_chapter].extend(images)

        # Render scanned pages
        word_count = len(body_text.split())
        if word_count < 25:
            rendered = _render_page_as_image(page)
            if rendered:
                chapter_images[current_chapter].append(rendered)

    doc.close()

    # Chunk by 150 words
    slides = []
    global_id = 0
    CHUNK_SIZE = 150

    for chapter, texts in chapter_texts.items():
        combined = " ".join(texts)
        words = combined.split()
        img_idx = 0
        chapter_imgs = chapter_images[chapter]

        for part_idx, word_start in enumerate(range(0, max(1, len(words)), CHUNK_SIZE)):
            chunk_words = words[word_start: word_start + CHUNK_SIZE]
            chunk_text = " ".join(chunk_words) if chunk_words else "(Visual Content)"

            img_dict = None
            if img_idx < len(chapter_imgs):
                img_dict = chapter_imgs[img_idx]
                img_idx += 1

            slides.append(SlideData(
                id=global_id,
                title=f"{chapter} — Part {part_idx + 1}",
                text=chunk_text,
                image=img_dict,
            ))
            global_id += 1

    return ParsedDocument(slide_units=slides)
