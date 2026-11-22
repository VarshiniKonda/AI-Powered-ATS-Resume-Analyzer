"""Accessible PDF report rendering from persisted analysis results."""

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def build_analysis_pdf(
    title: str,
    company: str | None,
    resume_filename: str,
    score: float,
    breakdown: dict[str, Any],
    details: dict[str, Any],
) -> bytes:
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Resume compatibility analysis",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#142238"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            textColor=colors.HexColor("#3767e8"),
            spaceBefore=12,
            spaceAfter=5,
        )
    )
    story = [
        Paragraph("Resume &amp; Job Compatibility Report", styles["ReportTitle"]),
        Paragraph(
            "Estimated decision-support analysis; this is not an employer ATS score.",
            styles["BodyText"],
        ),
        Spacer(1, 8),
        Paragraph(f"<b>Role:</b> {escape(title)}", styles["BodyText"]),
        Paragraph(f"<b>Company:</b> {escape(company or 'Not provided')}", styles["BodyText"]),
        Paragraph(f"<b>Resume:</b> {escape(resume_filename)}", styles["BodyText"]),
        Spacer(1, 8),
        Paragraph(f"Estimated compatibility: {score:.1f} / 100", styles["Heading1"]),
    ]

    rows = [["Component", "Score", "Effective weight"]]
    for key, component in breakdown.items():
        label = key.replace("_", " ").title()
        value = component.get("score")
        score_text = f"{value:.1f}%" if value is not None else "Not assessed"
        weight = component.get("effective_weight_percent", 0)
        rows.append([label, score_text, f"{weight:.1f}%"])
    table = Table(rows, colWidths=[90 * mm, 35 * mm, 45 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf0ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#142238")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce3ed")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([Paragraph("Score breakdown", styles["SectionHeading"]), table])

    def add_list(title_text: str, items: list[str]) -> None:
        story.append(Paragraph(title_text, styles["SectionHeading"]))
        if not items:
            story.append(Paragraph("None identified.", styles["BodyText"]))
        for item in items:
            story.append(Paragraph(f"- {escape(str(item))}", styles["BodyText"]))
            story.append(Spacer(1, 3))

    matched = [
        f"{item['skill']} ({item['match_type']}, {item['category']})"
        for item in details.get("matched_skills", [])
    ]
    add_list("Matched and partially matched skills", matched)
    missing = [
        f"{item['skill']} ({item['category']}): {item['explanation']}"
        for item in details.get("missing_skills", [])
    ]
    add_list("Missing skills and why they matter", missing)
    add_list("Matched keywords", details.get("matched_keywords", []))
    add_list("Important missing keywords (verify truthfully before adding)", details.get("important_missing_keywords", []))
    add_list("Resume strengths", details.get("resume_strengths", []))
    add_list("Areas to improve", details.get("areas_to_improve", []))
    add_list("Actionable improvement suggestions", details.get("improvement_suggestions", []))
    add_list("Skills to learn before claiming", details.get("skills_to_learn", []))
    story.append(Paragraph("Section feedback", styles["SectionHeading"]))
    for section, feedback in details.get("section_feedback", {}).items():
        story.append(Paragraph(f"<b>{escape(section.title())}:</b> {escape(str(feedback))}", styles["BodyText"]))
        story.append(Spacer(1, 4))

    document.build(story)
    return output.getvalue()
