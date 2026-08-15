"""
Learnova Unified Extraction Engine Schema
Defines the 8 core production dataclasses for multimodal document representation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class VisualAssetType(str, Enum):
    PICTURE = "picture"
    DIAGRAM = "diagram"
    ICON = "icon"
    LOGO = "logo"
    SCANNED_PAGE = "scanned_page"


class ChartType(str, Enum):
    BAR = "bar"
    PIE = "pie"
    LINE = "line"
    SCATTER = "scatter"
    RADAR = "radar"
    OTHER = "other"


class DiagramType(str, Enum):
    FLOWCHART = "flowchart"
    SMARTART = "smartart"
    MINDMAP = "mindmap"
    ARCHITECTURE = "architecture"
    GENERIC = "generic"


class DocumentType(str, Enum):
    PPTX = "pptx"
    PDF = "pdf"


@dataclass
class TextBlockElement:
    """Represents paragraphs, headings, bullet list nodes, and text runs."""

    id: str
    text: str
    is_heading: bool = False
    heading_level: int = 0
    bullet_level: int = 0  # 0 = normal text/top-level, 1 = sub-bullet, 2 = nested...
    is_speaker_note: bool = False
    font_size: Optional[float] = None
    is_bold: bool = False
    is_italic: bool = False
    bbox: Optional[Tuple[float, float, float, float]] = None  # (x0, y0, x1, y1)
    reading_order: int = 0


@dataclass
class TableElement:
    """Represents structured tables with header and row grid matrices."""

    id: str
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0
    has_merged_cells: bool = False
    caption: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    reading_order: int = 0


@dataclass
class VisualAssetElement:
    """Represents embedded images, crop figures, icons, and scanned page renders."""

    id: str
    image_bytes: Optional[bytes] = None
    file_path: Optional[str] = None
    format: str = "png"
    width_px: int = 0
    height_px: int = 0
    asset_type: VisualAssetType = VisualAssetType.PICTURE
    sha256_hash: str = ""
    ocr_text: Optional[str] = None
    vision_description: Optional[str] = None
    caption: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    reading_order: int = 0


@dataclass
class StructuredChartElement:
    """Represents data-driven charts with category labels and numerical data series."""

    id: str
    title: str = ""
    chart_type: ChartType = ChartType.OTHER
    categories: List[str] = field(default_factory=list)
    series_data: List[Dict[str, Any]] = field(default_factory=list)
    alt_text: Optional[str] = None
    summary_description: Optional[str] = None
    bbox: Optional[Tuple[float, float, float, float]] = None
    reading_order: int = 0


@dataclass
class DiagramElement:
    """Represents process flowcharts, SmartArt graphics, and visual diagrams."""

    id: str
    title: str = ""
    diagram_type: DiagramType = DiagramType.GENERIC
    mermaid_code: Optional[str] = None
    vision_description: Optional[str] = None
    raw_xml_text: List[str] = field(default_factory=list)
    bbox: Optional[Tuple[float, float, float, float]] = None
    reading_order: int = 0


@dataclass
class EquationElement:
    """Represents mathematical and scientific formulas (OMML, MathML, LaTeX)."""

    id: str
    latex_expression: str
    ascii_fallback: str = ""
    raw_omml: Optional[str] = None
    is_inline: bool = False
    bbox: Optional[Tuple[float, float, float, float]] = None
    reading_order: int = 0


@dataclass
class SlidePageEntity:
    """Represents an individual slide (PPTX) or page (PDF) container unit."""

    id: int
    unit_number: int
    title: str = ""
    text_blocks: List[TextBlockElement] = field(default_factory=list)
    tables: List[TableElement] = field(default_factory=list)
    visual_assets: List[VisualAssetElement] = field(default_factory=list)
    charts: List[StructuredChartElement] = field(default_factory=list)
    diagrams: List[DiagramElement] = field(default_factory=list)
    equations: List[EquationElement] = field(default_factory=list)
    rendered_page_image: Optional[VisualAssetElement] = None
    speaker_notes: Optional[str] = None
    reading_order_elements: List[str] = field(default_factory=list)
    takeaway: Optional[str] = None

    def get_full_text(self) -> str:
        """Returns consolidated text representation maintaining reading order."""
        lines = []
        for tb in self.text_blocks:
            if tb.text:
                if tb.is_heading:
                    lines.append(f"## {tb.text}")
                elif tb.bullet_level > 0:
                    indent = "  " * (tb.bullet_level - 1)
                    lines.append(f"{indent}- {tb.text}")
                else:
                    lines.append(tb.text)
        for tbl in self.tables:
            if tbl.headers:
                lines.append("[TABLE DATA]")
                lines.append(" | ".join(tbl.headers))
                for row in tbl.rows:
                    lines.append(" | ".join(row))
        if self.speaker_notes:
            lines.append(f"[Speaker Notes: {self.speaker_notes}]")
        return "\n".join(lines)

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Provides backward compatibility with the existing ParsedDocument / SlideData dictionary format."""
        primary_image = None
        all_images = []
        for va in self.visual_assets:
            img_dict = {"bytes": va.image_bytes, "ext": va.format}
            all_images.append(img_dict)
            if primary_image is None and va.image_bytes:
                primary_image = img_dict

        if not primary_image and self.rendered_page_image and self.rendered_page_image.image_bytes:
            primary_image = {"bytes": self.rendered_page_image.image_bytes, "ext": self.rendered_page_image.format}
            all_images.append(primary_image)

        full_text = self.get_full_text()
        return {
            "id": self.id,
            "slide": self.unit_number,
            "page": self.unit_number,
            "title": self.title or f"Slide {self.unit_number}",
            "text": full_text if full_text.strip() else "(No readable text on this slide)",
            "content": full_text.splitlines(),
            "image": primary_image,
            "images": all_images,
        }


@dataclass
class DocumentEntity:
    """Root container representing an ingested educational document."""

    id: str
    filename: str
    doc_type: DocumentType
    total_units: int
    slides: List[SlidePageEntity] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_legacy_parsed_dicts(self) -> List[Dict[str, Any]]:
        """Converts DocumentEntity into legacy slide dictionaries for seamless app.py compatibility."""
        return [slide.to_legacy_dict() for slide in self.slides]
