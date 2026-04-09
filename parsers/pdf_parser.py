import fitz  # PyMuPDF
import io
import re
from dataclasses import dataclass
from PIL import Image

@dataclass
class SlideData:
    id: int
    title: str
    text: str
    image: dict | None = None

@dataclass
class ParsedDocument:
    slide_units: list[SlideData]

def parse_pdf(file_path: str) -> ParsedDocument:
    """Legacy parser - returns 1 slide unit per page."""
    doc = fitz.open(file_path)
    slides = []
    
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        img_dict = None
        
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            ext = base_image["ext"]
            w = base_image.get("width", 0)
            h = base_image.get("height", 0)
            if w >= 120 and h >= 120:
                try:
                    with Image.open(io.BytesIO(img_bytes)) as pil_img:
                        out = io.BytesIO()
                        pil_img.convert("RGB").save(out, format="PNG")
                        img_dict = {"bytes": out.getvalue(), "ext": "png"}
                        break
                except Exception:
                    pass
        
        slides.append(SlideData(
            id=i, 
            title=f"Page {i+1}", 
            text=text,
            image=img_dict
        ))
    return ParsedDocument(slide_units=slides)

def parse_textbook_pdf(file_path: str) -> ParsedDocument:
    """
    Advanced parser for textbooks. Groups pages by chapter,
    then chunks text into ~120-word units per slide.
    Extracts images >= 120px and attaches one to chunks if available.
    """
    doc = fitz.open(file_path)
    current_chapter = "Introduction"
    blocks_by_chapter = {}
    images_by_chapter = {}
    
    for page in doc:
        # Detect simple chapter headings (e.g. "Chapter 1", "Unit 2")
        text = page.get_text("text")
        m = re.search(r'^(Chapter|Unit)\s+\d+', text, re.IGNORECASE | re.MULTILINE)
        if m:
            current_chapter = m.group(0).strip().title()
            
        if current_chapter not in blocks_by_chapter:
            blocks_by_chapter[current_chapter] = []
            images_by_chapter[current_chapter] = []
            
        blocks_by_chapter[current_chapter].append(text)
        
        # Images for this chapter
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            w = base_image.get("width", 0)
            h = base_image.get("height", 0)
            if w >= 120 and h >= 120:
                try:
                    with Image.open(io.BytesIO(base_image["image"])) as pil_img:
                        out = io.BytesIO()
                        pil_img.convert("RGB").save(out, format="PNG")
                        images_by_chapter[current_chapter].append({"bytes": out.getvalue(), "ext": "png"})
                except Exception:
                    pass
                
    # Chunking
    slides = []
    global_id = 0
    for chapter, texts in blocks_by_chapter.items():
        combined = " ".join(texts)
        words = combined.split()
        
        # Split into 120-word chunks
        chunk_size = 120
        idx = 0
        img_idx = 0
        chapter_imgs = images_by_chapter[chapter]
        
        for i in range(0, len(words), chunk_size):
            chunk_words = words[i:i+chunk_size]
            chunk_text = " ".join(chunk_words)
            
            img_dict = None
            if img_idx < len(chapter_imgs):
                img_dict = chapter_imgs[img_idx]
                img_idx += 1
            
            slides.append(SlideData(
                id=global_id,
                title=f"{chapter} - Part {idx+1}",
                text=chunk_text,
                image=img_dict
            ))
            global_id += 1
            idx += 1
            
    return ParsedDocument(slide_units=slides)
