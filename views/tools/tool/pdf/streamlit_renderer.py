"""
PDF Renderer for Streamlit - UI-specific rendering logic.

This module contains ALL Streamlit-specific code for displaying PDFs.
Completely separated from business logic.
"""

import hashlib
import logging
import time
from pathlib import Path
from typing import Dict, Any

import streamlit as st

logger = logging.getLogger(__name__)


class PdfRenderer:
    """Streamlit-specific UI renderer for PDF reports."""

    def render(self, result: Dict[str, Any], container) -> None:
        """
        Render PDF generation result with progress and download button.

        Args:
            result: Result from generate_pdf_report tool
            container: Streamlit container to render in
        """
        with container:
            # Check status
            if result.get("status") == "error":
                st.error(f"PDF Error: {result.get('error', 'Unknown error')}")
                return

            # Extract data
            title = result.get("title", "Report")
            filepath = result.get("filepath")
            filename = result.get("filename")
            file_size = result.get("file_size", 0)
            row_count = result.get("row_count", 0)

            if not filepath:
                st.error("PDF generation error: no file path returned")
                return

            # Show success
            st.success(f"PDF Report Generated: **{title}**")

            # Show metrics
            col1, col2 = st.columns(2)
            with col1:
                file_size_mb = file_size / (1024 * 1024)
                size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 0.01 else f"{file_size} bytes"
                st.metric("File Size", size_display)
            with col2:
                st.metric("Rows", row_count)

            # Show file path
            st.info(f"Saved to: `{filepath}`")

            # Render download button
            self._render_download_button(filepath, filename)

    def render_with_progress(
        self,
        title: str,
        data: list,
        summary: str,
        generator_func,
        container
    ) -> None:
        """
        Render PDF generation with progress bar.

        Args:
            title: PDF title
            data: PDF data
            summary: PDF summary
            generator_func: Function that generates PDF and returns result
            container: Streamlit container
        """
        with container:
            progress_bar = st.progress(0, text="Initializing PDF generation...")
            start_time = time.time()

            try:
                # Simulate progress steps
                progress_bar.progress(20, text="Creating output directory...")
                time.sleep(0.1)

                progress_bar.progress(40, text="Preparing document structure...")
                time.sleep(0.1)

                progress_bar.progress(60, text="Formatting data table...")

                # Call generator function
                result = generator_func(title, data, summary)

                progress_bar.progress(80, text="Building PDF file...")
                time.sleep(0.1)

                progress_bar.progress(100, text="PDF generation complete")
                elapsed_time = time.time() - start_time

                # Clear progress bar
                time.sleep(0.5)
                progress_bar.empty()

                # Render result with elapsed time
                if result.get("status") == "success":
                    self._render_success_with_time(result, elapsed_time, container)
                else:
                    st.error(f"PDF Error: {result.get('error', 'Unknown error')}")

            except Exception as e:
                logger.error("PDF rendering error: %s", str(e), exc_info=True)
                progress_bar.empty()
                st.error(f"PDF rendering error: {str(e)}")
                with st.expander("Error Details"):
                    import traceback
                    st.code(traceback.format_exc())

    def _render_success_with_time(
        self,
        result: Dict[str, Any],
        elapsed_time: float,
        container
    ) -> None:
        """Render success with elapsed time metric."""
        title = result.get("title", "Report")
        filepath = result.get("filepath")
        filename = result.get("filename")
        file_size = result.get("file_size", 0)
        row_count = result.get("row_count", 0)

        st.success(f"PDF Report Generated: **{title}**")

        # Metrics with time
        col1, col2, col3 = st.columns(3)
        with col1:
            file_size_mb = file_size / (1024 * 1024)
            size_display = f"{file_size_mb:.2f} MB" if file_size_mb >= 0.01 else f"{file_size} bytes"
            st.metric("File Size", size_display)
        with col2:
            st.metric("Rows", row_count)
        with col3:
            st.metric("Generation Time", f"{elapsed_time:.2f}s")

        st.info(f"Saved to: `{filepath}`")

        self._render_download_button(filepath, filename)

    def _render_download_button(self, filepath: str, filename: str) -> None:
        """Render download button with unique key."""
        try:
            # Read PDF file
            with open(filepath, "rb") as f:
                pdf_bytes = f.read()

            # Generate unique key
            pdf_key = hashlib.md5(
                f"{filename}_{time.time()}".encode()
            ).hexdigest()

            # Render button
            st.download_button(
                label="Download PDF Report",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                width='stretch',
                key=f"pdf_{pdf_key}"
            )

        except Exception as e:
            logger.error("Error creating download button: %s", str(e))
            st.error(f"Could not create download button: {str(e)}")
