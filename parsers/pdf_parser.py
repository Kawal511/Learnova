"""
PDF Parser Module for Learnova
Extracts page content (headings, text) from PDF files using PyMuPDF.
"""

import fitz  # PyMuPDF

from logger import logger


def parse_pdf(file_path: str) -> list[dict]:
    """
    Parse a PDF file and extract page-wise content.

    Args:
        file_path: Path to the .pdf file.

    Returns:
        List of dicts with keys: page, heading, content.
        Example: [{"page": 1, "heading": "Chapter 1", "content": "paragraph text..."}, ...]
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        logger.error("Failed to open PDF file %s: %s", file_path, e, exc_info=True)
        raise ValueError(f"Failed to open PDF file: {e}")

    # ── First pass: detect running headers (text repeated on many pages) ────
    large_text_counts: dict[str, int] = {}
    total_pages = len(doc)

    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        seen_on_page: set[str] = set()
        for block in blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                max_fs = max((sp.get("size", 0) for sp in line.get("spans", [])), default=0)
                if max_fs >= 14:
                    txt = "".join(sp.get("text", "") for sp in line.get("spans", [])).strip()
                    if txt and txt not in seen_on_page:
                        seen_on_page.add(txt)
                        large_text_counts[txt] = large_text_counts.get(txt, 0) + 1

    # Text appearing on >40% of pages is likely a running header/footer
    repeat_threshold = max(3, int(total_pages * 0.4))
    running_headers = {txt for txt, cnt in large_text_counts.items() if cnt >= repeat_threshold}

    # ── Second pass: extract content per page ────────────────────────────
    pages_data = []

    for page_num in range(total_pages):
        page = doc[page_num]

        # Extract text blocks with positional and font info
        blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        # Detect image-only pages (has image blocks but no text blocks)
        has_text_block = any(b.get("type") == 0 for b in blocks)
        has_image_block = any(b.get("type") == 1 for b in blocks)
        if not has_text_block and has_image_block:
            logger.warning("Page %d appears to be image-only — limited text extraction", page_num + 1)

        heading = ""
        content_lines = []

        for block in blocks:
            # Skip image blocks
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                line_text = ""
                max_font_size = 0

                for span in line.get("spans", []):
                    line_text += span.get("text", "")
                    font_size = span.get("size", 0)
                    if font_size > max_font_size:
                        max_font_size = font_size

                line_text = line_text.strip()
                if not line_text:
                    continue

                # Skip running headers/footers (e.g. author name on every page)
                if line_text in running_headers:
                    continue

                # Heuristic: treat the first large-font line as heading
                if not heading and max_font_size >= 14:
                    heading = line_text
                else:
                    content_lines.append(line_text)

        # Fallback heading: use first content line, otherwise generic label
        if not heading and content_lines:
            heading = content_lines.pop(0)
        if not heading:
            heading = f"Page {page_num + 1}"

        content = "\n".join(content_lines).strip()

        # Skip completely blank pages (no text, no images)
        if not content and not has_image_block:
            logger.warning("Page %d is blank — skipping", page_num + 1)
            pages_data.append({
                "page": page_num + 1,
                "heading": heading,
                "content": "(Blank page)"
            })
            continue

        pages_data.append({
            "page": page_num + 1,
            "heading": heading,
            "content": content if content else "(Image-only page — no extractable text)"
        })

    doc.close()
    return pages_data


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_parser.py <path_to_pdf>")
        sys.exit(1)

    results = parse_pdf(sys.argv[1])
    for page in results:
        print(f"\n--- Page {page['page']}: {page['heading']} ---")
        print(page["content"][:300])
