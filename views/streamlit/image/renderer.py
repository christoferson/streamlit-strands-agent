"""
Image Renderer for Streamlit - UI-specific rendering logic.

This module contains ALL Streamlit-specific code for displaying generated images.
"""

import base64
import logging
from typing import Dict, Any

import streamlit as st

logger = logging.getLogger(__name__)


class ImageRenderer:
    """Streamlit-specific UI renderer for generated images."""

    def render(self, result: Dict[str, Any], container) -> None:
        """
        Render generated image from prepared data.

        Args:
            result: Result from generate_image tool
            container: Streamlit container to render in
        """
        with container:
            # Check status
            if result.get("status") == "error":
                st.error(f"Image Generation Error: {result.get('error', 'Unknown error')}")
                return

            # Extract data
            image_bytes_b64 = result.get("image_bytes_b64")
            seed = result.get("seed")
            prompt = result.get("prompt", "")
            aspect_ratio = result.get("aspect_ratio", "1:1")

            if not image_bytes_b64:
                st.warning("Image error: no image data provided")
                return

            try:
                # Decode base64 image
                image_bytes = base64.b64decode(image_bytes_b64)

                # Display success message
                st.success(f"Image generated successfully! (seed: {seed})")

                # Display the image
                st.image(image_bytes, caption=prompt[:100], use_container_width=True)

                # Show metadata
                with st.expander("Generation Details"):
                    st.write(f"**Seed:** {seed}")
                    st.write(f"**Aspect Ratio:** {aspect_ratio}")
                    st.write(f"**Prompt:** {prompt}")

                # Store in session state for potential reuse
                if "generated_images" not in st.session_state:
                    st.session_state.generated_images = []
                st.session_state.generated_images.append(image_bytes)

            except Exception as e:
                logger.error("Image rendering error: %s", str(e), exc_info=True)
                st.error(f"Image rendering error: {str(e)}")
