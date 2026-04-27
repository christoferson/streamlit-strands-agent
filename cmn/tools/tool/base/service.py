"""
Base service class for tool architecture.

Services contain pure business logic with no UI dependencies.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class BaseService(ABC):
    """
    Base class for all service implementations.

    Services contain pure business logic with no UI dependencies.
    They perform the actual work (data processing, API calls, file I/O).
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize service.

        Args:
            output_dir: Optional output directory for generated files
        """
        self.output_dir = output_dir
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute the service's primary operation.

        Returns:
            Dict with at minimum:
            {
                "status": "success" | "error",
                "error": str (if status == "error"),
                ... other fields depend on service type
            }
        """
        pass

    def _sanitize_filename(self, text: str) -> str:
        """
        Sanitize text for use as filename.

        Args:
            text: Input text to sanitize

        Returns:
            Safe filename string
        """
        safe = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_'))
        return safe.strip().replace(' ', '_') or "file"
