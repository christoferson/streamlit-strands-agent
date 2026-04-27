"""
Base renderer class for tool architecture.

Renderers contain ALL UI-specific code for displaying tool results.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .service import BaseService


class BaseRenderer(ABC):
    """
    Base class for UI renderers.

    Renderers contain ALL UI-specific code for a tool.
    They receive payloads from tools and render the output in the UI framework.

    Different UI frameworks will have different renderer implementations:
    - StreamlitRenderer (for Streamlit)
    - ReactRenderer (for React/Next.js)
    - CLIRenderer (for command-line output)
    """

    def __init__(self, service: Optional[BaseService] = None):
        """
        Initialize renderer.

        Args:
            service: Optional service instance for direct rendering
                    (when not using tool payloads)
        """
        self.service = service

    @abstractmethod
    def render(self, payload: Dict[str, Any], container: Any) -> None:
        """
        Render the payload in the UI.

        Args:
            payload: Result payload from tool (parsed JSON)
            container: UI container to render in (framework-specific)

        Raises:
            Should handle errors internally and display error UI
        """
        pass

    def render_error(self, error_message: str, container: Any) -> None:
        """
        Render an error message.

        Subclasses can override for framework-specific error display.

        Args:
            error_message: Error message to display
            container: UI container
        """
        print(f"ERROR: {error_message}")
