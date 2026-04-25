"""
Image Generation Tool Package - Pure business logic and framework-agnostic tool.

This package provides:
- ImageService: Image generation logic (no UI)
- generate_image: Strands @tool wrapper that returns data

NO UI DEPENDENCIES - can be used from any interface.
"""

from .service import ImageService
from .tool import generate_image

__all__ = [
    "ImageService",
    "generate_image",
]
