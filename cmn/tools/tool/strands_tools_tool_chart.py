import json
import logging

import pandas as pd
import plotly.express as px
import streamlit as st
from strands import tool

logger = logging.getLogger(__name__)


@tool
def render_chart(
    chart_type: str,
    title: str,
    x_label: str,
    y_label: str,
    data: list,
    color: str = "",
) -> str:
    """
    Visualize data as a chart. Always call AFTER fetching data with sales_data.

    x_label and y_label must exactly match column names in the data array.

    Args:
        chart_type: Chart type — 'bar', 'line', or 'area'.
        title: Chart title, e.g. '2024 Monthly Revenue'.
        x_label: Column name for X axis, e.g. 'month_name'.
        y_label: Column name for Y axis, e.g. 'revenue'.
        data: Array of data objects, e.g. [{'month_name': 'Jan', 'revenue': 125000}].
        color: Optional hex colour, e.g. '#4A90D9'.

    Returns:
        str: JSON payload containing all chart data needed for rendering.
    """
    if not data:
        return json.dumps({"error": "No data provided."})

    logger.info("render_chart: type=%s title=%s rows=%d", chart_type, title, len(data))

    # Return the full payload — app.py renders it from the result chunk
    return json.dumps({
        "status":     "chart_ready",
        "chart_type": chart_type,
        "title":      title,
        "x_label":    x_label,
        "y_label":    y_label,
        "data":       data,
        "color":      color,
    })


def render_chart_payload(payload: dict, container) -> None:
    """
    Render a chart payload. Called by app.py after streaming completes.
    """
    data       = payload.get("data", [])
    x          = payload["x_label"]
    y          = payload["y_label"]
    title      = payload["title"]
    chart_type = payload["chart_type"]

    if not data:
        with container:
            st.warning("Chart error: no data.")
        return

    df = pd.DataFrame(data)

    if x not in df.columns:
        with container:
            st.warning(f"Chart error: '{x}' not in columns {list(df.columns)}")
        return

    color_col = next(
        (c for c in ["series", "type", "category"] if c in df.columns),
        None,
    )
    x_order = df[x].unique().tolist()

    with container:
        st.markdown(f"**{title}**")

        if color_col:
            if chart_type == "bar":
                fig = px.bar(df, x=x, y=y, color=color_col, barmode="group")
            elif chart_type == "line":
                fig = px.line(df, x=x, y=y, color=color_col, markers=True)
            else:
                fig = px.area(df, x=x, y=y, color=color_col)
        else:
            chart_df  = df.set_index(x)
            y_columns = (
                [y] if y in chart_df.columns
                else chart_df.select_dtypes(include="number").columns.tolist()
            )
            plot_df = chart_df[y_columns].reset_index()

            if chart_type == "bar":
                fig = px.bar(plot_df, x=x, y=y_columns, barmode="group")
            elif chart_type == "line":
                fig = px.line(plot_df, x=x, y=y_columns, markers=True)
            else:
                fig = px.area(plot_df, x=x, y=y_columns)

        fig.update_xaxes(categoryorder="array", categoryarray=x_order)
        st.plotly_chart(fig, width="content")