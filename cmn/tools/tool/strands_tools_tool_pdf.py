import hashlib
import json
import logging
import os
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from strands import tool

logger = logging.getLogger(__name__)

# PDF output directory
PDF_OUTPUT_DIR = Path("outputs/pdfs")


@tool
def generate_pdf_report(
    title: str,
    data: list,
    summary: str = "",
) -> str:
    """
    Generate a PDF sales report with formatted data tables and save to disk.

    Use this tool to create downloadable PDF reports from sales data.
    Always fetch data with sales_data first, then call this tool.

    Args:
        title: Report title, e.g. '2024 Sales Report' or 'Q2 Revenue Analysis'
        data: Sales data array from sales_data tool
        summary: Optional text summary to include at the top of the report

    Returns:
        str: JSON payload containing file path and metadata
    """
    try:
        if not data:
            return json.dumps({"error": "No data provided for PDF generation"})

        logger.info("generate_pdf_report: title=%s rows=%d", title, len(data))

        # Create output directory
        PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        filename = f"{safe_title}_{timestamp}.pdf"
        filepath = PDF_OUTPUT_DIR / filename

        # Create PDF document
        doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                               rightMargin=72, leftMargin=72,
                               topMargin=72, bottomMargin=18)

        # Container for PDF elements
        elements = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        # Add title
        elements.append(Paragraph(title, title_style))

        # Add metadata
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

        # Add summary if provided
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

        # Convert data to table
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

        # Prepare table data with headers
        table_data = [df.columns.tolist()] + df.values.tolist()

        # Create table
        table = Table(table_data)

        # Style the table
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

        elements.append(table)

        # Build PDF
        doc.build(elements)

        # Get file size
        file_size = filepath.stat().st_size

        logger.info("PDF saved: %s (size=%d bytes)", filepath, file_size)

        return json.dumps({
            "status": "pdf_saved",
            "title": title,
            "filepath": str(filepath),
            "filename": filename,
            "row_count": len(data),
            "columns": list(df.columns),
            "file_size": file_size,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        logger.error("Error generating PDF: %s", str(e), exc_info=True)
        return json.dumps({"error": f"PDF generation failed: {str(e)}"})


def render_pdf_payload(payload: dict, container) -> None:
    """
    Render PDF download section with file info and download button.
    Shows progress bar and elapsed time during generation.
    """
    logger.info("render_pdf_payload called with payload keys: %s", list(payload.keys()))

    title = payload.get("title", "Report")
    data = payload.get("data", [])
    summary = payload.get("summary", "")

    if not data:
        with container:
            st.warning("PDF generation error: no data provided")
        return

    with container:
        # Show progress
        progress_bar = st.progress(0, text="Initializing PDF generation...")
        start_time = time.time()

        try:
            # Step 1: Create directory
            progress_bar.progress(20, text="📁 Creating output directory...")
            PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            time.sleep(0.2)  # Brief pause for UX

            # Step 2: Prepare document
            progress_bar.progress(40, text="📄 Preparing document structure...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            filename = f"{safe_title}_{timestamp}.pdf"
            filepath = PDF_OUTPUT_DIR / filename

            doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                                   rightMargin=72, leftMargin=72,
                                   topMargin=72, bottomMargin=18)

            # Step 3: Format data
            progress_bar.progress(60, text="📊 Formatting data table...")
            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=TA_CENTER
            )

            elements.append(Paragraph(title, title_style))

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

            df = pd.DataFrame(data)

            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    if 'revenue' in col.lower() or 'profit' in col.lower():
                        df[col] = df[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "")
                    elif 'margin' in col.lower():
                        df[col] = df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "")
                    else:
                        df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "")

            table_data = [df.columns.tolist()] + df.values.tolist()
            table = Table(table_data)

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

            elements.append(table)

            # Step 4: Build PDF
            progress_bar.progress(80, text="✍️ Building PDF file...")
            doc.build(elements)

            # Step 5: Finalize
            progress_bar.progress(100, text="✅ PDF generation complete!")
            elapsed_time = time.time() - start_time

            # Get file info
            file_size = filepath.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            logger.info("PDF saved: %s (size=%d bytes, time=%.2fs)", filepath, file_size, elapsed_time)

            # Clear progress bar
            time.sleep(0.5)
            progress_bar.empty()

            # Show success message
            st.success(f"✅ PDF Report Generated: **{title}**")

            # Show file info
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("File Size", f"{file_size_mb:.2f} MB" if file_size_mb >= 0.01 else f"{file_size} bytes")
            with col2:
                st.metric("Rows", len(data))
            with col3:
                st.metric("Generation Time", f"{elapsed_time:.2f}s")

            # Show file path
            st.info(f"📁 Saved to: `{filepath}`")

            # Read file and provide download button
            with open(filepath, "rb") as f:
                pdf_bytes = f.read()

            # Generate unique key with high-precision timestamp to avoid duplicates
            pdf_key = hashlib.md5(f"{title}_{timestamp}_{time.time()}".encode()).hexdigest()

            st.download_button(
                label="⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True,
                key=f"pdf_{pdf_key}"
            )

        except Exception as e:
            logger.error("Error generating PDF: %s", str(e), exc_info=True)
            progress_bar.empty()
            st.error(f"❌ PDF generation error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
