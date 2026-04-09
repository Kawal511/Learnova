from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import os
import re
import io
from PIL import Image
from dataclasses import dataclass

@dataclass
class SlideData:
    id: int
    title: str
    text: str
    image: dict | None = None

@dataclass
class ParsedDocument:
    slide_units: list[SlideData]

def _clean_text(lines: list[str]) -> str:
    """Strips leading bullet symbols and deduplicates lines."""
    clean_lines = []
    seen = set()
    for line in lines:
        line = line.strip()
        # Remove bullet symbols
        line = re.sub(r"^[-*•>▪]\s*", "", line)
        line = re.sub(r"^[0-9A-Za-z]+[\.)]\s*", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            clean_lines.append(line)
    return "\n".join(clean_lines)

def parse_ppt(file_path: str) -> ParsedDocument:
    """Parses PPT file with AI-ready cleaned text and image extraction."""
    prs = Presentation(file_path)
    slides = []
    skipped_shapes = {"Rectangle", "Line", "Arrow"}
    
    for i, slide in enumerate(prs.slides):
        title = ""
        lines = []
        img_dict = None
        
        if slide.shapes.title:
            title = slide.shapes.title.text.strip()
            
        for shape in slide.shapes:
            # Skip decorative shapes
            shape_name_start = shape.name.split()[0] if shape.name else ""
            if any(shape_name_start.startswith(s) for s in skipped_shapes):
                continue
                
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text and text != title:
                        lines.append(text)
                        
            # Image extraction for AI Vision
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                if not img_dict:
                    try:
                        img_bytes = shape.image.blob
                        # Use PIL to verify or convert
                        with Image.open(io.BytesIO(img_bytes)) as pil_img:
                            out = io.BytesIO()
                            pil_img.convert("RGB").save(out, format="PNG")
                            img_dict = {"bytes": out.getvalue(), "ext": "png"}
                    except Exception:
                        pass
        
        cleaned_text = _clean_text(lines)
        if not cleaned_text.strip():
            cleaned_text = "(No readable text found on this slide)"
            
        slides.append(SlideData(
            id=i,
            title=title or f"Slide {i+1}",
            text=cleaned_text,
            image=img_dict
        ))
        
    return ParsedDocument(slide_units=slides)
