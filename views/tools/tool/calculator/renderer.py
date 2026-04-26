"""
Streamlit renderer for calculator tool.

Displays calculator results in Streamlit UI.
"""

from typing import Any, Dict
import streamlit as st
from cmn.tools.tool.base.renderer import BaseRenderer


class CalculatorRendererStreamlit(BaseRenderer):
    """
    Streamlit renderer for calculator results.

    Displays mathematical expression evaluation results with appropriate
    success/error styling.
    """

    def __init__(self):
        """Initialize calculator renderer (no service needed)."""
        super().__init__(service=None)

    def render(self, payload: Dict[str, Any], container: Any) -> None:
        """
        Render calculator result in Streamlit.

        Args:
            payload: Calculator result payload with structure:
                {
                    "status": "success" | "error",
                    "expression": str,
                    "result": number (if success),
                    "error": str (if error)
                }
            container: Streamlit container to render in
        """
        if not isinstance(payload, dict):
            self.render_error("Invalid payload format", container)
            return

        status = payload.get("status")
        expression = payload.get("expression", "")

        if status == "success":
            result = payload.get("result")
            with container:
                st.success("Calculation Complete")
                st.markdown(f"**Expression:** `{expression}`")
                st.markdown(f"**Result:** `{result}`")

        elif status == "error":
            error = payload.get("error", "Unknown error")
            with container:
                st.error("Calculation Error")
                st.markdown(f"**Expression:** `{expression}`")
                st.markdown(f"**Error:** {error}")

        else:
            self.render_error(f"Unknown status: {status}", container)

    def render_error(self, error_message: str, container: Any) -> None:
        """
        Render an error message in Streamlit.

        Args:
            error_message: Error message to display
            container: Streamlit container
        """
        with container:
            st.error(f"Calculator Renderer Error: {error_message}")
