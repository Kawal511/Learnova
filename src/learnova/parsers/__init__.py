"""Learnova Parsers Package."""

from learnova.parsers.base import BaseDocumentParser
from learnova.parsers.legacy import ParsedDocument, SlideData
from learnova.parsers.schema import (
    ChartType,
    DiagramElement,
    DiagramType,
    DocumentEntity,
    DocumentType,
    EquationElement,
    SlidePageEntity,
    StructuredChartElement,
    TableElement,
    TextBlockElement,
    VisualAssetElement,
    VisualAssetType,
)

__all__ = [
    "DocumentEntity",
    "SlidePageEntity",
    "TextBlockElement",
    "TableElement",
    "VisualAssetElement",
    "StructuredChartElement",
    "DiagramElement",
    "EquationElement",
    "VisualAssetType",
    "ChartType",
    "DiagramType",
    "DocumentType",
    "BaseDocumentParser",
    "SlideData",
    "ParsedDocument",
]
