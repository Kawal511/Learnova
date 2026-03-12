"""
PPT Parser Module for Learnova
Extracts slide content (title, bullets) from PowerPoint (.pptx) files.
"""

from pptx import Presentation

from logger import logger


def parse_ppt(file_path: str) -> list[dict]:
    """
    Parse a .pptx file and extract slide data.

    Args:
        file_path: Path to the .pptx file.

    Returns:
        List of dicts with keys: slide, title, content.
        Example: [{"slide": 1, "title": "Intro", "content": ["bullet1", "bullet2"]}, ...]
    """
    try:
        prs = Presentation(file_path)
    except Exception as e:
        logger.error("Failed to open PPT file %s: %s", file_path, e, exc_info=True)
        raise ValueError(f"Failed to open PPT file: {e}")

    slides_data = []

    for slide_num, slide in enumerate(prs.slides, start=1):
        title = ""
        bullets = []

        # Try to get the title from the slide's title shape
        if slide.shapes.title and slide.shapes.title.text.strip():
            title = slide.shapes.title.text.strip()

        # Collect bullet text from all non-title text frames
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue

            # Skip the title shape — already captured above
            if slide.shapes.title and shape.shape_id == slide.shapes.title.shape_id:
                continue

            for paragraph in shape.text_frame.paragraphs:
                text = paragraph.text.strip()
                if text:
                    bullets.append(text)

        # If no title and no bullets, mark as empty slide
        if not title and not bullets:
            slides_data.append({
                "slide": slide_num,
                "title": f"Slide {slide_num} (Empty Slide)",
                "content": []
            })
            logger.warning("Slide %d has no text content — marked as empty", slide_num)
            continue

        # If no title was found, label it as untitled
        if not title:
            title = f"Slide {slide_num} (Untitled)"

        slides_data.append({
            "slide": slide_num,
            "title": title,
            "content": bullets
        })

    return slides_data


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ppt_parser.py <path_to_pptx>")
        sys.exit(1)

    results = parse_ppt(sys.argv[1])
    for slide in results:
        print(f"\n--- Slide {slide['slide']}: {slide['title']} ---")
        for bullet in slide["content"]:
            print(f"  • {bullet}")
