"""
Learnova Base Document Parser Interface
Defines the standard abstract contract for all document parser implementations.
"""

from abc import ABC, abstractmethod
import os
from learnova.parsers.schema import DocumentEntity


class BaseDocumentParser(ABC):
    """
    Abstract Base Class for Learnova document parsers (PPTX, PDF, etc.).
    Guarantees a unified parsing contract across all document types.
    """

    @abstractmethod
    def parse(self, file_path: str) -> DocumentEntity:
        """
        Parses a document file and returns a unified DocumentEntity graph.

        Args:
            file_path: Absolute path to the target PPTX or PDF file.

        Returns:
            DocumentEntity containing strongly-typed SlidePageEntity units and elements.
        """
        pass

    @abstractmethod
    def supports(self, file_path_or_extension: str) -> bool:
        """
        Checks whether this parser implementation supports the specified file format.

        Args:
            file_path_or_extension: File path or file extension (e.g. '.pptx', '.pdf').

        Returns:
            True if supported, False otherwise.
        """
        pass

    def validate(self, file_path: str) -> bool:
        """
        Validates that the target file exists, is accessible, and is non-empty.

        Args:
            file_path: Absolute path to the target file.

        Returns:
            True if valid, False otherwise.
        """
        if not file_path or not isinstance(file_path, str):
            return False
        if not os.path.exists(file_path):
            return False
        if not os.path.isfile(file_path):
            return False
        try:
            if os.path.getsize(file_path) == 0:
                return False
        except OSError:
            return False

        return self.supports(file_path)
