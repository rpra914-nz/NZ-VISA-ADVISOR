"""
report_agent.py
Generates a formatted, client-ready PDF report for LIAs.
Combines:
  - Intake profile (from intake_agent)
  - SMC assessment (from classification_agent)
  - Document review results (from document_review_agent)
Output: PDF bytes ready for st.download_button()
"""

import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Colour palette ────────────────────────────────────────────────────────────
NZ_BLUE = colors.HexColor("#003087")      # INZ-style navy
NZ_TEAL = colors.HexColor("#00857C")      # accent teal
LIGHT_GREY = colors.HexColor("#F4F6F8")
MID_GREY = colors.HexColor("#8C9099")
GREEN = colors.HexColor("#1A7F37")
AMBER = colors.HexColor("#D97706")
RED = colors.HexColor("#DC2626")
WHITE = colors.white
BLACK = colors.black

STATUS_COLOUR = {"ok": GREEN, "warning": AMBER, "error": RED}
STATUS_ICON = {"ok": "✅", "warning": "⚠️", "error": "❌"}

# ── Style helpers ─────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()
    custom = {}

    custom["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"],
        fontSize=26, textColor=NZ_BLUE, spaceAfter=4, alignment=TA_LEFT,
    )
    custom["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"],
        fontSize=12, textColor=MID_GREY, spaceAfter=2, alignment=TA_LEFT,
    )
    custom["section_heading"] = ParagraphStyle(
        "section_heading", parent=base["Heading1"],
        fontSize=13, textColor=NZ_BLUE, spaceBefore=10, spaceAfter=4,
        borderPad=2,
    )
    custom["body"] = ParagraphStyle(
        "body", parent=base["Normal"],
        fontSize=10, leading=15, spaceAfter=4, textColor=BLACK,
    )
    custom["small"] = ParagraphStyle(
        "small", parent=base["Normal"],
        fontSize=8, leading=12, textColor=MID_GREY, spaceAfter=2,
    )
    custom["disclaimer"] = ParagraphStyle(
        "disclaimer", parent=base["Normal"],
        fontSize=8, leading=12, textColor=MID_GREY,
        borderColor=MID_GREY, borderWidth=0.5, borderPad=6,
        backColor=LIGHT_GREY,
    )
    custom["points_big"] = ParagraphStyle(
        "points_big", parent=base["Normal"],
        fontSize=28, textColor=NZ_TEAL, alignment=TA_CENTER, spaceAfter=2,
    )
    custom["status_label"] = ParagraphStyle(
        "status_label", parent=base["Normal"],
        fontSize=11, textColor=WHITE, alignment=TA_CENTER,
    )
    return custom

# ── Section builders ──────────────────────────────────────────────────────────

def _header_block(styles, profile: dict) -> list:
    name = profile.get("full_name", "Client")
    date_str = datetime.now().strftime("%d %B %Y")
    story = []
    story.append(Paragraph("NZ Visa Advisor", styles["cover_title"]))
    story.append(Paragraph("Skilled Migrant Category — Assessment Report", styles["cover_sub"]))
    story.append(HRFlowable(width="100%", thickness=2, color=NZ_BLUE, spaceAfter=6))
    meta = [
        ["Client:", name],
        ["Prepared by:", "NZ Visa Advisor (AI-assisted — for LIA review only)"],
        ["Date:", date_str],
        ["Visa Category:", "Skilled Migrant Category (SMC) Residence"],
    ]
    t = Table(meta, colWidths=[45*mm, 120*mm])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), MID_GREY),
        ("TEXTCOLOR", (1, 0), (1, -1), BLACK),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))
    return story


def _profile_section(styles, profile: dict) -> list:
    story = [Paragraph("1. Client Profile", styles["section_heading"])]
    fields = [
        ("Full Name", profile.get("full_name", "—")),
        ("Age", profile.get("age", "—")),
        ("Nationality", profile.get("nationality", "—")),
        ("Current Location", profile.get("current_location", "—")),
        ("Occupation / Job Title", profile.get("job_title", "—")),
        ("Employer (NZ)", profile.get("employer", "—")),
        ("Annual Salary (NZD)", profile.get("salary", "—")),
        ("Highest Qualification", profile.get("qualification", "—")),
        ("Years of Experience", profile.get("experience_years", "—")),
        ("English Proficiency", profile.get("english_level", "—")),
        ("ANZSCO Code", profile.get("anzsco_code", "—")),
    ]
    rows = [[f, v] for f, v in fields if v and v != "—" or True]
    t = Table(rows, colWidths=[65*mm, 100*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF6")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))
    return story


def _assessment_section(styles, assessment: dict) -> list:
    story = [Paragraph("2. SMC Points Assessment", styles["section_heading"])]

    total = assessment.get("total_points", 0)
    status = assessment.get("status", "UNKNOWN")
    strengths = assessment.get("strengths", [])
    gaps = assessment.get("gaps", [])
    breakdown = assessment.get("points_breakdown", {})
    reasoning = assessment.get("reasoning", "")

    # Status banner
    colour_map = {
        "ELIGIBLE": GREEN,
        "LIKELY_ELIGIBLE": AMBER,
        "NOT_ELIGIBLE": RED,
    }
    banner_colour = colour_map.get(status, MID_GREY)
    banner_label = status.replace("_", " ")

    banner_data = [[
        Paragraph(f"<b>{total} / 160+ points</b>", styles["points_big"]),
        Paragraph(f"<b>{banner_label}</b>", styles["status_label"]),
    ]]
    banner = Table(banner_data, colWidths=[80*mm, 85*mm])
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EEF4FF")),
        ("BACKGROUND", (1, 0), (1, 0), banner_colour),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#EEF4FF"), banner_colour]),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D0D5DD")),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 8))

    # Points breakdown table
    if breakdown:
        story.append(Paragraph("<b>Points Breakdown</b>", styles["body"]))
        rows = [["Category", "Points Awarded", "Max Available"]]
        for category, pts in breakdown.items():
            label = category.replace("_", " ").title()
            max_pts = {
                "skilled_employment": 60,
                "qualification": 50,
                "age": 30,
                "new_zealand_work_experience": 10,
                "partner_bonus": 20,
                "other": 10,
            }.get(category, "—")
            rows.append([label, str(pts), str(max_pts)])
        t = Table(rows, colWidths=[90*mm, 40*mm, 35*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NZ_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (0, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 6))

    # Strengths
    if strengths:
        story.append(Paragraph("<b>Strengths</b>", styles["body"]))
        for s in strengths:
            story.append(Paragraph(f"• {s}", styles["body"]))

    # Gaps
    if gaps:
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Gaps / Areas to Address</b>", styles["body"]))
        for g in gaps:
            story.append(Paragraph(f"• {g}", styles["body"]))

    # Reasoning
    if reasoning:
        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Adviser Notes</b>", styles["body"]))
        story.append(Paragraph(reasoning, styles["body"]))

    story.append(Spacer(1, 6))
    return story


def _document_section(styles, doc_review: dict) -> list:
    story = [Paragraph("3. Document Review", styles["section_heading"])]

    reviewed = doc_review.get("reviewed_docs", [])
    checklist = doc_review.get("checklist", [])
    missing = doc_review.get("required_missing", [])
    all_ok = doc_review.get("all_required_present", False)

    # Summary banner
    if all_ok:
        summary_text = "All required documents appear to be present."
        summary_colour = GREEN
    elif missing:
        summary_text = f"{len(missing)} required document(s) missing."
        summary_colour = RED
    else:
        summary_text = "Some documents may need attention."
        summary_colour = AMBER

    story.append(Paragraph(
        f'<font color="#{summary_colour.hexval()[2:]}"><b>{summary_text}</b></font>',
        styles["body"]
    ))
    story.append(Spacer(1, 4))

    # Per-document results
    if reviewed:
        story.append(Paragraph("<b>Uploaded Documents</b>", styles["body"]))
        for doc in reviewed:
            icon = STATUS_ICON.get(doc.get("status", "warning"), "⚠️")
            label = doc.get("label", doc.get("doc_type", "Unknown"))
            fname = doc.get("filename", "")
            summary = doc.get("summary", "")
            issues = doc.get("issues", [])
            suggestions = doc.get("suggestions", [])

            block = []
            block.append(Paragraph(f"<b>{icon} {label}</b> <font color='#8C9099'>({fname})</font>", styles["body"]))
            if summary:
                block.append(Paragraph(summary, styles["small"]))
            for issue in issues:
                block.append(Paragraph(f"  ⚠ {issue}", styles["small"]))
            for sug in suggestions:
                block.append(Paragraph(f"  → {sug}", styles["small"]))
            block.append(Spacer(1, 4))
            story.extend(block)

    # Document checklist
    story.append(Paragraph("<b>INZ SMC Document Checklist</b>", styles["body"]))
    rows = [["Document", "Required", "Status"]]
    for item in checklist:
        icon = STATUS_ICON["ok"] if item["present"] else (STATUS_ICON["error"] if item["required"] else STATUS_ICON["warning"])
        rows.append([
            item["label"],
            "Yes" if item["required"] else "Recommended",
            icon + (" Present" if item["present"] else " Missing"),
        ])
    t = Table(rows, colWidths=[90*mm, 35*mm, 40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NZ_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D0D5DD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (0, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))
    return story


def _disclaimer_section(styles) -> list:
    text = (
        "DISCLAIMER: This report is generated by an AI-assisted tool for use by "
        "Licensed Immigration Advisers (LIAs) only. It does not constitute legal or "
        "immigration advice. All assessments must be verified by a qualified LIA against "
        "current INZ policy before submission. Immigration New Zealand (INZ) makes the "
        "final decision on all residence applications."
    )
    return [
        HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=6),
        Paragraph(text, styles["disclaimer"]),
    ]


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report(profile: dict, assessment: dict, doc_review: dict) -> bytes:
    """
    Generate a PDF report and return it as bytes.

    Args:
        profile:    dict from intake_agent (client details)
        assessment: dict from classification_agent (points, status, etc.)
        doc_review: dict from document_review_agent (reviewed_docs, checklist)

    Returns:
        PDF file as bytes — ready for st.download_button()
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm,
    )

    styles = _build_styles()
    story = []

    story.extend(_header_block(styles, profile))
    story.append(Spacer(1, 6))
    story.extend(_profile_section(styles, profile))
    story.extend(_assessment_section(styles, assessment))
    story.extend(_document_section(styles, doc_review))
    story.extend(_disclaimer_section(styles))

    doc.build(story)
    return buffer.getvalue()