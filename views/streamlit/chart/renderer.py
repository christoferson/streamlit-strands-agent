"""
Chart Renderer for Streamlit - UI-specific rendering logic.

This module contains ALL Streamlit-specific code for displaying charts.
"""

import hashlib
import logging
import time
from typing import Dict, Any

import pandas as pd
import plotly.express as px
import streamlit as st

logger = logging.getLogger(__name__)


class ChartRenderer:
    """Streamlit-specific UI renderer for charts."""

    def render(self, result: Dict[str, Any], container) -> None:
        """
        Render chart from prepared data.

        Args:
            result: Result from render_chart tool
            container: Streamlit container to render in
        """
        with container:
            # Check status
            if result.get("status") == "error":
                st.error(f"Chart Error: {result.get('error', 'Unknown error')}")
                return

            # Extract data
            data = result.get("data", [])
            x = result.get("x_label")
            y = result.get("y_label")
            title = result.get("title")
            chart_type = result.get("chart_type")
            color_col = result.get("color_column")
            x_order = result.get("x_order", [])

            if not data:
                st.warning("Chart error: no data provided")
                return

            try:
                # Convert to DataFrame
                df = pd.DataFrame(data)

                # Display title
                st.markdown(f"**{title}**")

                # Create chart based on type and whether we have color grouping
                if color_col:
                    fig = self._create_grouped_chart(df, chart_type, x, y, color_col)
                else:
                    fig = self._create_simple_chart(df, chart_type, x, y, result.get("y_columns", []))

                # Update x-axis ordering
                if x_order:
                    fig.update_xaxes(categoryorder="array", categoryarray=x_order)

                # Render chart with unique key
                chart_key = self._generate_unique_key(title, len(data), x, y)
                st.plotly_chart(fig, width='stretch', key=f"chart_{chart_key}")

            except Exception as e:
                logger.error("Chart rendering error: %s", str(e), exc_info=True)
                st.error(f"Chart rendering error: {str(e)}")

    def _create_grouped_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x: str,
        y: str,
        color_col: str
    ):
        """Create a chart with color grouping (multi-series)."""
        if chart_type == "bar":
            return px.bar(df, x=x, y=y, color=color_col, barmode="group")
        elif chart_type == "line":
            return px.line(df, x=x, y=y, color=color_col, markers=True)
        else:  # area
            return px.area(df, x=x, y=y, color=color_col)

    def _create_simple_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        x: str,
        y_columns: list
    ):
        """Create a simple chart without color grouping."""
        # Prepare data with x column and y columns
        chart_df = df.set_index(x)
        plot_df = chart_df[y_columns].reset_index()

        if chart_type == "bar":
            return px.bar(plot_df, x=x, y=y_columns, barmode="group")
        elif chart_type == "line":
            return px.line(plot_df, x=x, y=y_columns, markers=True)
        else:  # area
            return px.area(plot_df, x=x, y=y_columns)

    @staticmethod
    def _generate_unique_key(title: str, data_len: int, x: str, y: str) -> str:
        """Generate unique key for chart widget to avoid duplicates."""
        key_string = f"{title}_{data_len}_{x}_{y}_{time.time()}"
        return hashlib.md5(key_string.encode()).hexdigest()
