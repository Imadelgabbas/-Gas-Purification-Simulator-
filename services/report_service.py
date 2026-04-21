"""
Report service for exporting gas purification results as PDF files.
"""

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


class ReportService:
    """Builds a simple PDF report for comparison results."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#1f4e79"),
            spaceAfter=8,
        )
        self.section_style = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#1f4e79"),
            spaceBefore=8,
            spaceAfter=6,
        )
        self.body_style = ParagraphStyle(
            "BodyTextClean",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            spaceAfter=4,
        )
        self.small_style = ParagraphStyle(
            "SmallText",
            parent=self.styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#555555"),
        )

    def build_comparison_report(self, form_data, comparison_results):
        """
        Generate a PDF report for the current comparison result set.

        Args:
            form_data: Input parameters stored in session
            comparison_results: Recommendation results stored in session

        Returns:
            BytesIO buffer positioned at the start of the generated PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        story = []
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        story.append(Paragraph("Gas Purification Report", self.title_style))
        story.append(Paragraph(f"Generated on {generated_at}", self.small_style))
        story.append(Spacer(1, 8))

        story.append(Paragraph("Input Data", self.section_style))
        story.append(self._build_input_table(form_data))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Scores", self.section_style))
        story.append(self._build_scores_table(comparison_results.get("scores", {})))
        story.append(Spacer(1, 10))

        story.append(Paragraph("Best Method", self.section_style))
        best_method = comparison_results.get("best_method", "N/A")
        best_score = comparison_results.get("best_score", "N/A")
        story.append(
            Paragraph(
                f"<b>{self._escape(best_method)}</b> (Score: {best_score})",
                self.body_style,
            )
        )
        story.append(Spacer(1, 6))

        story.append(Paragraph("Explanation", self.section_style))
        explanation = comparison_results.get("explanation", "No explanation available.")
        story.append(Paragraph(self._escape(explanation), self.body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer

    def _build_input_table(self, form_data):
        gas_mixture = form_data.get("gas_mixture", [])
        gas_summary = ", ".join(
            f"{gas.get('name', 'Unknown')}: {gas.get('percentage', 0)}%"
            for gas in gas_mixture
        ) or "No gas mixture provided"

        rows = [
            [self._label_cell("Gas Mixture"), self._value_cell(gas_summary)],
            [self._label_cell("Temperature"), self._value_cell(f"{form_data.get('temperature', 'N/A')} C")],
            [self._label_cell("Pressure"), self._value_cell(f"{form_data.get('pressure', 'N/A')} bar")],
            [self._label_cell("Flow Rate"), self._value_cell(f"{form_data.get('flowRate', 'N/A')} m3/h")],
            [self._label_cell("Impurity To Remove"), self._value_cell(str(form_data.get("impurityToRemove", "N/A")))],
            [self._label_cell("Desired Purity"), self._value_cell(f"{form_data.get('desiredPurity', 'N/A')}%")],
        ]

        table = Table(rows, colWidths=[48 * mm, 120 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edf4fb")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEADING", (0, 0), (-1, -1), 12),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8d7e6")),
                    ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.HexColor("#fafcfe")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _build_scores_table(self, scores):
        rows = [[self._header_cell("Method"), self._header_cell("Score")]]
        for method, score in scores.items():
            rows.append(
                [
                    self._value_cell(method),
                    self._value_cell(
                        f"{score:.2f}" if isinstance(score, (int, float)) else str(score)
                    ),
                ]
            )

        table = Table(rows, colWidths=[85 * mm, 35 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 1), (1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8d7e6")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return table

    def _escape(self, value):
        return (
            str(value)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _label_cell(self, value):
        return Paragraph(self._escape(value), self.body_style)

    def _value_cell(self, value):
        return Paragraph(self._escape(value), self.body_style)

    def _header_cell(self, value):
        header_style = ParagraphStyle(
            "TableHeader",
            parent=self.body_style,
            fontName="Helvetica-Bold",
            textColor=colors.white,
            alignment=1,
        )
        return Paragraph(self._escape(value), header_style)
