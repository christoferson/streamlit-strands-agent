"""
Renderer registry for managing BaseRenderer instances.

Similar to ToolRegistry but for the view layer.
"""

from typing import Dict, Optional
from cmn.tools.tool.base.renderer import BaseRenderer


class RendererRegistry:
    """
    Registry for managing BaseRenderer instances.

    Maintains a dictionary of renderers keyed by name for lookup and coordination.
    """

    def __init__(self):
        """Initialize empty renderer registry."""
        self._renderers: Dict[str, BaseRenderer] = {}

    def register(self, name: str, renderer: BaseRenderer) -> None:
        """
        Register a renderer instance.

        Args:
            name: Renderer name (e.g., "calculator", "chart", "pdf")
            renderer: BaseRenderer instance to register

        Raises:
            ValueError: If renderer name already registered
        """
        if name in self._renderers:
            raise ValueError(f"Renderer '{name}' is already registered")
        self._renderers[name] = renderer

    def get(self, name: str) -> Optional[BaseRenderer]:
        """
        Get a registered renderer by name.

        Args:
            name: Renderer name

        Returns:
            BaseRenderer instance or None if not found
        """
        return self._renderers.get(name)

    def has(self, name: str) -> bool:
        """
        Check if a renderer is registered.

        Args:
            name: Renderer name

        Returns:
            True if renderer is registered
        """
        return name in self._renderers

    def list_renderers(self) -> list[str]:
        """
        Get list of registered renderer names.

        Returns:
            List of renderer names
        """
        return list(self._renderers.keys())
