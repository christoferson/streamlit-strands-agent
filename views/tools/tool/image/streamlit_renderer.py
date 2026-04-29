"""
Image Renderer for Streamlit - UI-specific rendering logic.

This module contains ALL Streamlit-specific code for displaying generated images.
"""

import logging
from pathlib import Path
from typing import Dict, Any

import streamlit as st

logger = logging.getLogger(__name__)


class ImageRenderer:
    """Streamlit-specific UI renderer for generated images."""

    def render(self, result: Dict[str, Any], container) -> None:
        """
        Render generated image from file.

        The tool saves images to disk and returns filepath in JSON.
        This prevents context window overflow from large base64 strings.

        Args:
            result: Result from generate_image tool (with filepath)
            container: Streamlit container to render in
        """
        with container:
            # Check status
            if result.get("status") == "error":
                st.error(f"Image Generation Error: {result.get('error', 'Unknown error')}")
                return

            # Extract data
            filepath = result.get("filepath")
            filename = result.get("filename")
            seed = result.get("seed")
            prompt = result.get("prompt", "")
            aspect_ratio = result.get("aspect_ratio", "1:1")
            file_size = result.get("file_size", 0)

            if not filepath:
                st.error("Image generation error: no file path returned")
                return

            try:
                # Read image from file
                image_bytes = Path(filepath).read_bytes()

                # Display success message
                st.success(f"Image Generated: **{filename}**")

                # Display the image
                st.image(image_bytes, caption=prompt[:100], width='stretch')

                # Show metadata
                col1, col2 = st.columns(2)
                with col1:
                    file_size_kb = file_size / 1024
                    size_display = f"{file_size_kb:.1f} KB"
                    st.metric("File Size", size_display)
                with col2:
                    st.metric("Seed", seed)

                with st.expander("Generation Details"):
                    st.write(f"**Prompt:** {prompt}")
                    st.write(f"**Aspect Ratio:** {aspect_ratio}")
                    st.write(f"**Saved to:** `{filepath}`")

                # Store bytes in session state for chat history replay
                if "generated_images" not in st.session_state:
                    st.session_state.generated_images = []
                st.session_state.generated_images.append(image_bytes)

                # Add image index to result for retrieval during replay
                result["image_index"] = len(st.session_state.generated_images) - 1
                # Remove filepath to keep session state clean
                del result["filepath"]

            except FileNotFoundError:
                logger.error("Image file not found: %s", filepath)
                st.error(f"Image file not found: {filepath}")
            except Exception as e:
                logger.error("Image rendering error: %s", str(e), exc_info=True)
                st.error(f"Image rendering error: {str(e)}")
