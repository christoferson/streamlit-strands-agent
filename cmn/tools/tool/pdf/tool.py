"""
PDF tool implementation.

Thin wrapper around PdfService that extends BaseTool.
"""

from typing import List, Dict, Any
from strands import tool
from ..base.tool import BaseTool
from .service import PdfService


class PdfTool(BaseTool):
    """
    PDF tool that generates PDF reports.

    This is a thin wrapper around PdfService that:
    1. Converts parameters to appropriate types
    2. Calls the service
    3. Converts results to JSON strings
    4. Handles errors
    """

    def __init__(self):
        """Initialize PDF tool with service."""
        service = PdfService()
        super().__init__(service)

    @tool(name="generate_pdf_report")
    def execute(
        self,
        title: str,
        data: List[Dict[str, Any]],
        summary: str = ""
    ) -> str:
        """
        Generate a PDF sales report with formatted data tables and save to disk.

        CRITICAL: Always fetch fresh data with sales_data BEFORE calling this tool.
        NEVER reuse data from earlier in the conversation.

        Args:
            title: Report title, e.g. '2024 Sales Report' or 'Q2 Revenue Analysis'
            data: Sales data array from sales_data tool - must be FRESH data
            summary: Optional text summary to include at the top of the report

        Returns:
            JSON string with file path and metadata
        """
        # Call service and add data/summary to result for UI rendering
        result = self.service.execute(title=title, data=data, summary=summary)

        # Add original data to result for UI rendering (if successful)
        if result.get("status") == "success":
            result["data"] = data
            result["summary"] = summary

        import json
        return json.dumps(result)
