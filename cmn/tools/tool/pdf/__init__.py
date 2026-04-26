"""
PDF tool package.

Provides:
- PdfService: Business logic for PDF report generation
- PdfTool: BaseTool wrapper with JSON responses and @tool decorator
"""

from .service import PdfService
from .tool import PdfTool

__all__ = [
    "PdfService",
    "PdfTool",
]
