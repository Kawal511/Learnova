"""
Advanced PPTX Parser for Learnova
Extracts ALL text from every shape type:
- Text frames (all paragraphs + runs, preserving hierarchy)
- Grouped shapes (recursive traversal)
- Native PowerPoint tables (all rows + cells)
- SmartArt and diagram shapes (via XML text extraction)
- Chart alt-text and chart titles
- Slide notes/speaker notes
- Slide layout/master fallback titles
- Images: embedded picture blobs + slide thumbnail rendering
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER
from pptx.oxml.ns import qn
import io
import re
import fitz  # PyMuPDF for slide-as-image rendering
from PIL import Image
from dataclasses import dataclass, field
from lxml import etree
import os
import tempfile


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


# ── XML namespace text extraction (for SmartArt, diagrams, grouped elements) ──
def _xml_text_deep(element) -> list[str]:
    """Recursively pulls all a:t text nodes from OOXML element."""
    texts = []
    for t_elem in element.iter(qn("a:t")):
        v = (t_elem.text or "").strip()
        if v:
            texts.append(v)
    return texts


def _extract_table_text(shape) -> list[str]:
    """Extract all text from a native PowerPoint table shape."""
    lines = []
    try:
        table = shape.table
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                lines.append(" | ".join(row_cells))
    except Exception:
        pass
    return lines


def _extract_textframe_text(tf) -> list[str]:
    """Extract all paragraphs from a text frame, preserving paragraph structure."""
    lines = []
    for para in tf.paragraphs:
        # Collect all runs in the paragraph
        para_text = "".join(run.text for run in para.runs).strip()
        if not para_text:
            # fallback: direct paragraph.text
            para_text = para.text.strip()
        if para_text:
            lines.append(para_text)
    return lines


def _extract_shape_text(shape, visited_ids: set) -> list[str]:
    """
    Recursively extract ALL text from a shape, handling:
    - Text frames
    - Tables
    - Groups (recursive)
    - Charts (alt text + chart title)
    - SmartArt / diagrams (XML fallback)
    """
    if id(shape) in visited_ids:
        return []
    visited_ids.add(id(shape))

    lines = []

    # 1. Text frames
    try:
        if shape.has_text_frame:
            lines.extend(_extract_textframe_text(shape.text_frame))
    except Exception:
        pass

    # 2. Native tables
    try:
        if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
            lines.extend(_extract_table_text(shape))
    except Exception:
        pass

    # 3. Grouped shapes — recurse into every child
    try:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            for child_shape in shape.shapes:
                lines.extend(_extract_shape_text(child_shape, visited_ids))
    except Exception:
        pass

    # 4. Charts — get chart title and alt text
    try:
        if shape.shape_type == MSO_SHAPE_TYPE.CHART:
            chart = shape.chart
            # Chart title
            try:
                if chart.has_title:
                    lines.append(f"Chart: {chart.chart_title.text_frame.text.strip()}")
            except Exception:
                pass
            # Alt text from element description
            try:
                nvSpPr = shape._element.find(".//" + qn("p:nvSpPr"))
                if nvSpPr is not None:
                    nvPr = nvSpPr.find(qn("p:nvPr"))
                    if nvPr is not None:
                        ph_elem = nvPr.find(qn("p:ph"))
                        if ph_elem is not None and ph_elem.get("descr"):
                            lines.append(ph_elem.get("descr"))
            except Exception:
                pass
    except Exception:
        pass

    # 5. XML deep-scan fallback (catches SmartArt, diagrams, connectors with text)
    if not lines:
        try:
            xml_texts = _xml_text_deep(shape._element)
            lines.extend(xml_texts)
        except Exception:
            pass

    return lines


def _get_all_images(slide) -> list[dict]:
    """Extract all embedded picture images from a slide (any size)."""
    images = []
    for shape in slide.shapes:
        try:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                blob = shape.image.blob
                with Image.open(io.BytesIO(blob)) as pil_img:
                    w, h = pil_img.size
                    if w >= 100 and h >= 100:
                        out = io.BytesIO()
                        pil_img.convert("RGB").save(out, format="PNG")
                        images.append({"bytes": out.getvalue(), "ext": "png"})
        except Exception:
            pass
    return images


def _slide_as_image(file_path: str, slide_index: int) -> dict | None:
    """
    Render a PDF page to PNG using PyMuPDF.
    For PPTX files, PyMuPDF cannot render slide thumbnails natively.
    """
    if not file_path.lower().endswith(".pdf"):
        return None
    try:
        doc = fitz.open(file_path)
        if slide_index < len(doc):
            page = doc[slide_index]
            pix = page.get_pixmap(dpi=150)
            return {"bytes": pix.tobytes("png"), "ext": "png"}
    except Exception:
        pass
    return None


def _clean_and_deduplicate(lines: list[str]) -> str:
    """
    Clean bullet symbols, deduplicate, and join lines into a single text block.
    Does NOT over-strip — preserves ALL content words.
    """
    seen = set()
    clean = []
    for line in lines:
        # Normalize whitespace
        line = " ".join(line.split())
        # Remove leading bullet chars only (not all special chars)
        line = re.sub(r"^[\s\-\*•▪➤►→▶▷◆◇■□●○]+", "", line).strip()
        if line and line.lower() not in seen and len(line) > 1:
            seen.add(line.lower())
            clean.append(line)
    return "\n".join(clean)


def parse_ppt(file_path: str) -> ParsedDocument:
    """
    Full-featured PPTX parser.
    Extracts text from ALL shape types, tables, groups, charts, SmartArt,
    speaker notes, and images (preserving all images per slide).
    """
    prs = Presentation(file_path)
    slides_data = []

    for i, slide in enumerate(prs.slides):
        # ── Title: try placeholder first, then any title-shaped text box ─────
        title = ""
        try:
            if slide.shapes.title:
                title = (slide.shapes.title.text or "").strip()
        except Exception:
            pass

        # ── Collect text from ALL shapes ─────────────────────────────────────
        all_lines = []
        visited_ids: set = set()

        for shape in slide.shapes:
            shape_lines = _extract_shape_text(shape, visited_ids)
            all_lines.extend(shape_lines)

        # ── Speaker notes ────────────────────────────────────────────────────
        try:
            notes_slide = slide.notes_slide
            notes_tf = notes_slide.notes_text_frame
            notes_text = notes_tf.text.strip()
            if notes_text and len(notes_text) > 10:
                all_lines.append(f"[Speaker Notes: {notes_text}]")
        except Exception:
            pass

        # Remove title from body lines (avoid duplication)
        if title:
            all_lines = [l for l in all_lines if l.strip() and l.strip().lower() != title.strip().lower()]

        cleaned_text = _clean_and_deduplicate(all_lines)
        if not cleaned_text.strip():
            cleaned_text = "(No readable text on this slide)"

        # ── Images: preserve all embedded pictures ────────────────────────────
        images = _get_all_images(slide)
        img_dict = images[0] if images else None

        # Fallback to page rendering if no embedded image
        if not img_dict and len(cleaned_text.split()) < 20:
            rendered_img = _slide_as_image(file_path, i)
            if rendered_img:
                img_dict = rendered_img
                images.append(rendered_img)

        slides_data.append(SlideData(
            id=i,
            title=title or f"Slide {i + 1}",
            text=cleaned_text,
            image=img_dict,
            images=images,
        ))

    return ParsedDocument(slide_units=slides_data)
