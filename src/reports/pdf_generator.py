"""
TrueNAS Enterprise PDF Report Generator

Generates professionally branded PDF reports using ReportLab.
"""

import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# TrueNAS Brand Colors (converted to ReportLab colors)
COLORS = {
    "primary": colors.HexColor("#0095D5"),
    "secondary": colors.HexColor("#31BEEC"),
    "gray": colors.HexColor("#AEADAE"),
    "accent": colors.HexColor("#71BF44"),
    "white": colors.white,
    "black": colors.black,
    "background": colors.HexColor("#0d1117"),
    "surface": colors.HexColor("#161b22"),
    "border": colors.HexColor("#30363d"),
    "critical": colors.HexColor("#dc3545"),
    "warning": colors.HexColor("#ffc107"),
    "success": colors.HexColor("#28a745"),
}


def get_health_color(score: float) -> colors.Color:
    """Get color based on health score."""
    if score < 40:
        return COLORS["critical"]
    elif score < 60:
        return COLORS["warning"]
    elif score < 80:
        return COLORS["secondary"]
    else:
        return COLORS["success"]


def get_health_status(score: float) -> str:
    """Get status text based on health score."""
    if score < 40:
        return "Critical"
    elif score < 60:
        return "At Risk"
    elif score < 80:
        return "Moderate"
    else:
        return "Healthy"


class PDFReportGenerator:
    """Generates TrueNAS branded PDF reports."""

    def __init__(self, summary: Dict[str, Any], cases: Dict[str, Any]):
        self.summary = summary
        self.cases_data = cases
        self.cases = cases.get("cases", [])
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """Configure custom styles for TrueNAS branding."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='TrueNASTitle',
            parent=self.styles['Title'],
            fontSize=28,
            textColor=COLORS["primary"],
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Subtitle style
        self.styles.add(ParagraphStyle(
            name='TrueNASSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=COLORS["gray"],
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=COLORS["primary"],
            spaceBefore=20,
            spaceAfter=10,
            fontName='Helvetica-Bold',
            borderColor=COLORS["primary"],
            borderWidth=2,
            borderPadding=5
        ))

        # Subsection header
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=COLORS["secondary"],
            spaceBefore=15,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceBefore=3,
            spaceAfter=3,
            leading=14
        ))

        # Metric value style
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=24,
            textColor=COLORS["primary"],
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        # Metric label style
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=COLORS["gray"],
            alignment=TA_CENTER
        ))

        # Quote style
        self.styles.add(ParagraphStyle(
            name='Quote',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            leftIndent=20,
            rightIndent=20,
            spaceBefore=10,
            spaceAfter=10,
            fontName='Helvetica-Oblique'
        ))

    def _create_header(self) -> list:
        """Create the report header with branding."""
        elements = []

        # TrueNAS Enterprise title
        elements.append(Paragraph(
            '<font color="#0095D5">TrueNAS</font><font color="#000000">Enterprise</font>',
            self.styles['TrueNASTitle']
        ))

        # Report title
        elements.append(Paragraph(
            "Account Health Report",
            ParagraphStyle(
                name='ReportTitle',
                parent=self.styles['Title'],
                fontSize=20,
                textColor=colors.black,
                alignment=TA_CENTER
            )
        ))

        # Account and date
        account_name = self.summary.get("account_name", "Unknown Account")
        analysis_date = self.summary.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))

        elements.append(Paragraph(
            f"{account_name} | {analysis_date}",
            self.styles['TrueNASSubtitle']
        ))

        # Divider
        elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=COLORS["primary"],
            spaceAfter=20
        ))

        return elements

    def _create_health_score_section(self) -> list:
        """Create the health score overview section."""
        elements = []

        health_score = self.summary.get("account_health_score", 0)
        health_color = get_health_color(health_score)
        health_status = get_health_status(health_score)

        # Health score display
        elements.append(Paragraph("Account Health Score", self.styles['SectionHeader']))

        # Score table with colored indicator
        score_data = [
            [Paragraph(f"<font color='{health_color.hexval()}'>{health_score:.0f}</font>",
                      self.styles['MetricValue'])],
            [Paragraph(f"<font color='{health_color.hexval()}'>{health_status}</font>",
                      self.styles['MetricLabel'])]
        ]

        score_table = Table(score_data, colWidths=[2*inch])
        score_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, COLORS["border"]),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8f9fa")),
        ]))

        elements.append(score_table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_key_metrics_section(self) -> list:
        """Create the key metrics overview."""
        elements = []

        elements.append(Paragraph("Key Metrics", self.styles['SectionHeader']))

        claude_stats = self.summary.get("claude_statistics", {})

        metrics_data = [
            ["Total Cases", "High Frustration", "Avg Frustration", "Frustrated Messages"],
            [
                str(self.summary.get("total_cases", 0)),
                str(claude_stats.get("high_frustration", 0)),
                f"{claude_stats.get('avg_frustration_score', 0):.1f}/10",
                f"{claude_stats.get('frustrated_messages_count', 0)}"
            ]
        ]

        metrics_table = Table(metrics_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('TEXTCOLOR', (0, 0), (-1, 0), COLORS["gray"]),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
        ]))

        elements.append(metrics_table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_critical_cases_section(self) -> list:
        """Create the critical cases summary."""
        elements = []

        elements.append(Paragraph("Critical Cases Overview", self.styles['SectionHeader']))

        # Get top 10 cases by criticality
        top_cases = sorted(self.cases, key=lambda x: x.get("criticality_score", 0), reverse=True)[:10]

        if not top_cases:
            elements.append(Paragraph("No cases to display.", self.styles['BodyText']))
            return elements

        # Create table
        table_data = [["Case #", "Severity", "Criticality", "Frustration", "Issue Type"]]

        for case in top_cases:
            claude = case.get("claude_analysis") or {}
            table_data.append([
                str(case.get("case_number", "")),
                case.get("severity", "N/A"),
                f"{case.get('criticality_score', 0):.0f}",
                f"{claude.get('frustration_score', 0)}/10",
                claude.get("issue_class", "Unknown")[:20]
            ])

        case_table = Table(table_data, colWidths=[0.8*inch, 0.7*inch, 0.9*inch, 0.9*inch, 2.5*inch])
        case_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), COLORS["primary"]),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, COLORS["border"]),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))

        elements.append(case_table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_case_details_section(self) -> list:
        """Create detailed case analysis for top cases."""
        elements = []

        elements.append(PageBreak())
        elements.append(Paragraph("Detailed Case Analysis", self.styles['SectionHeader']))

        # Get top 5 cases for detailed view
        top_cases = sorted(self.cases, key=lambda x: x.get("criticality_score", 0), reverse=True)[:5]

        for case in top_cases:
            claude = case.get("claude_analysis") or {}
            deepseek = case.get("deepseek_analysis") or {}

            case_num = case.get("case_number", "N/A")
            issue_class = claude.get("issue_class", "Unknown")

            # Case header
            elements.append(Paragraph(
                f"Case #{case_num} - {issue_class}",
                self.styles['SubsectionHeader']
            ))

            # Case metrics
            case_metrics = [
                f"Criticality: {case.get('criticality_score', 0):.0f} pts",
                f"Frustration: {claude.get('frustration_score', 0)}/10",
                f"Age: {case.get('case_age_days', 0)} days",
                f"Status: {case.get('status', 'Unknown')}"
            ]
            elements.append(Paragraph(" | ".join(case_metrics), self.styles['BodyText']))
            elements.append(Spacer(1, 10))

            # Executive Summary
            exec_summary = deepseek.get("executive_summary") or deepseek.get("root_cause", "")
            if exec_summary:
                elements.append(Paragraph("<b>Executive Summary:</b>", self.styles['BodyText']))
                elements.append(Paragraph(exec_summary[:500], self.styles['BodyText']))
                elements.append(Spacer(1, 5))

            # Pain Points
            pain_points = deepseek.get("pain_points", "")
            if pain_points:
                elements.append(Paragraph("<b>Pain Points:</b>", self.styles['BodyText']))
                elements.append(Paragraph(pain_points[:300], self.styles['BodyText']))
                elements.append(Spacer(1, 5))

            # Recommended Action
            recommendation = deepseek.get("recommended_action", "")
            if recommendation:
                elements.append(Paragraph("<b>Recommended Action:</b>", self.styles['BodyText']))
                elements.append(Paragraph(
                    f"<font color='#71BF44'>{recommendation[:300]}</font>",
                    self.styles['BodyText']
                ))

            # Key Customer Quote
            key_phrase = claude.get("key_phrase", "")
            if key_phrase:
                elements.append(Spacer(1, 5))
                elements.append(Paragraph(f'"{key_phrase[:200]}"', self.styles['Quote']))

            elements.append(HRFlowable(width="100%", thickness=0.5, color=COLORS["border"], spaceAfter=15))

        return elements

    def _create_footer(self, canvas, doc):
        """Add footer to each page."""
        canvas.saveState()

        # Footer line
        canvas.setStrokeColor(COLORS["border"])
        canvas.line(0.75*inch, 0.5*inch, 7.75*inch, 0.5*inch)

        # Footer text
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(COLORS["gray"])

        # Left side: Generated info
        canvas.drawString(0.75*inch, 0.35*inch,
                         f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Center: TrueNAS Enterprise
        canvas.drawCentredString(4.25*inch, 0.35*inch, "TrueNAS Enterprise - Account Health Report")

        # Right side: Page number
        canvas.drawRightString(7.75*inch, 0.35*inch, f"Page {doc.page}")

        canvas.restoreState()

    def generate(self) -> bytes:
        """Generate the PDF report and return as bytes."""
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Build document elements
        elements = []

        # Header
        elements.extend(self._create_header())

        # Health Score
        elements.extend(self._create_health_score_section())

        # Key Metrics
        elements.extend(self._create_key_metrics_section())

        # Critical Cases Table
        elements.extend(self._create_critical_cases_section())

        # Detailed Case Analysis
        elements.extend(self._create_case_details_section())

        # Build PDF
        doc.build(elements, onFirstPage=self._create_footer, onLaterPages=self._create_footer)

        buffer.seek(0)
        return buffer.getvalue()


def generate_pdf_report(summary: Dict[str, Any], cases: Dict[str, Any]) -> bytes:
    """Convenience function to generate a PDF report."""
    generator = PDFReportGenerator(summary, cases)
    return generator.generate()
