"""
PDF service implementation.

Pure business logic for PDF report generation.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from ..base.service import BaseService

logger = logging.getLogger(__name__)


class PdfService(BaseService):
    """
    Service for generating PDF reports.

    This service creates PDF files but does NOT handle UI display.
    UI rendering is handled by the renderer in the view layer.
    """

    def __init__(self, output_dir: Path = None):
        """
        Initialize PDF service.

        Args:
            output_dir: Directory where PDFs will be saved (default: outputs/pdfs)
        """
        if output_dir is None:
            output_dir = Path("outputs/pdfs")
        super().__init__(output_dir=output_dir)

    def execute(
        self,
        title: str,
        data: List[Dict[str, Any]],
        summary: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a PDF report from data.

        Args:
            title: Report title
            data: List of dictionaries containing report data
            summary: Optional summary text

        Returns:
            Dictionary with file path, metadata, and status
        """
        # Validate data
        if not data:
            return {
                "status": "error",
                "error": "No data provided for PDF generation"
            }

        if not title:
            return {
                "status": "error",
                "error": "Title is required"
            }

        logger.info("Generating PDF report: title=%s rows=%d", title, len(data))

        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = self._sanitize_filename(title)
            filename = f"{safe_title}_{timestamp}.pdf"
            filepath = self.output_dir / filename

            # Create PDF document
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )

            # Build document elements
            elements = self._build_document_elements(title, data, summary)

            # Generate PDF
            doc.build(elements)

            # Get file info
            file_size = filepath.stat().st_size

            logger.info("PDF generated: %s (size=%d bytes)", filepath, file_size)

            return {
                "status": "success",
                "title": title,
                "filepath": str(filepath),
                "filename": filename,
                "row_count": len(data),
                "columns": list(pd.DataFrame(data).columns),
                "file_size": file_size,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error("PDF generation failed: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "error": f"PDF generation failed: {str(e)}"
            }

    def _build_document_elements(
        self,
        title: str,
        data: List[Dict[str, Any]],
        summary: str
    ) -> list:
        """Build PDF document elements (title, table, etc.)."""
        elements = []
        styles = getSampleStyleSheet()

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(title, title_style))

        # Metadata
        metadata_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Rows: {len(data)}"
        metadata_style = ParagraphStyle(
            'Metadata',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            alignment=TA_CENTER
        )
        elements.append(Paragraph(metadata_text, metadata_style))
        elements.append(Spacer(1, 20))

        # Summary (optional)
        if summary:
            summary_style = ParagraphStyle(
                'Summary',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=20,
                alignment=TA_LEFT
            )
            elements.append(Paragraph("<b>Summary:</b>", summary_style))
            elements.append(Paragraph(summary, summary_style))
            elements.append(Spacer(1, 20))

        # Data table
        table = self._create_data_table(data)
        elements.append(table)

        return elements

    def _create_data_table(self, data: List[Dict[str, Any]]) -> Table:
        """Create formatted data table."""
        df = pd.DataFrame(data)

        # Format numeric columns
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                if 'revenue' in col.lower() or 'profit' in col.lower():
                    df[col] = df[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
                elif 'margin' in col.lower():
                    df[col] = df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                else:
                    df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

        # Create table data
        table_data = [df.columns.tolist()] + df.values.tolist()
        table = Table(table_data)

        # Apply styling
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))

        return table

    @staticmethod
    def _sanitize_filename(title: str) -> str:
        """Sanitize title for use as filename."""
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return safe_title.replace(' ', '_')
