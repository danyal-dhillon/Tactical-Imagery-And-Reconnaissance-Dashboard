"""ReportLab PDF tactical intelligence briefing layouts and compilation flow."""

from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors as rl_colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import settings


def compile_intel_report(database, session_id, output_path):
    """Build the PDF briefing for a session. Returns the output path."""
    session = database.get_session(session_id)
    if session is None:
        raise ValueError(f"Session {session_id} does not exist in the database.")

    inventory = database.get_inventory(session_id)
    top_detections = database.get_top_detections(session_id, settings.PDF_DETAIL_ROWS)
    total_detections = database.count_detections(session_id)

    level_totals = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
    for row in inventory:
        level_totals[row["threat_level"]] = level_totals.get(row["threat_level"], 0) + row["total"]

    base_styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BriefTitle", parent=base_styles["Title"], fontName="Helvetica-Bold", fontSize=18,
        leading=22, textColor=rl_colors.HexColor("#121414"), alignment=0, spaceAfter=4,
    )
    heading_style = ParagraphStyle(
        "BriefHeading", parent=base_styles["Heading2"], fontName="Helvetica-Bold", fontSize=12,
        leading=15, textColor=rl_colors.HexColor("#121414"), spaceBefore=10, spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BriefBody", parent=base_styles["BodyText"], fontName="Helvetica", fontSize=9, leading=12,
    )
    cell_style = ParagraphStyle(
        "BriefCell", parent=base_styles["BodyText"], fontName="Helvetica", fontSize=8, leading=10,
        wordWrap="CJK",
    )
    header_cell_style = ParagraphStyle(
        "BriefHeaderCell", parent=cell_style, fontName="Helvetica-Bold",
        textColor=rl_colors.white,
    )
    disclaimer_style = ParagraphStyle(
        "BriefDisclaimer", parent=base_styles["BodyText"], fontName="Helvetica-Oblique",
        fontSize=8, leading=10, textColor=rl_colors.HexColor("#444444"),
    )

    def cell(text, style=cell_style):
        return Paragraph(escape(str(text)), style)

    def level_cell(level):
        color = {"CRITICAL": "#C0392B", "HIGH": "#D35400", "MEDIUM": "#7F6000"}.get(level, "#000000")
        return Paragraph(f'<font color="{color}"><b>{escape(level)}</b></font>', cell_style)

    document = SimpleDocTemplate(
        output_path, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Tactical Intelligence Briefing - Session {session_id}",
        author="Tactical Recon Dashboard",
    )
    width = document.width

    def build_table(data, ratios, extra_styles=None):
        col_widths = [width * ratio for ratio in ratios]
        table = Table(data, colWidths=col_widths, repeatRows=1)
        style_commands = [
            ("BACKGROUND", (0, 0), (-1, 0), rl_colors.HexColor("#1A1D1D")),
            ("GRID", (0, 0), (-1, -1), 0.5, rl_colors.HexColor("#8A9494")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rl_colors.white, rl_colors.HexColor("#F1F3F3")]),
        ]
        if extra_styles:
            style_commands.extend(extra_styles)
        table.setStyle(TableStyle(style_commands))
        return table

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    story = [
        Paragraph("TACTICAL INTELLIGENCE BRIEFING", title_style),
        Paragraph(f"Reconnaissance Session #{session_id}", body_style),
        Spacer(1, 8),
    ]

    metadata_rows = [
        [cell("Field", header_cell_style), cell("Value", header_cell_style)],
        [cell("Document"), cell(f"Tactical Intelligence Briefing - Session {session_id}")],
        [cell("System Timestamp"), cell(generated_at)],
        [cell("Session Start"), cell(session["timestamp"])],
        [cell("Source Type"), cell(session["source_type"] or "UNKNOWN")],
        [cell("Total Logged Detections"), cell(total_detections)],
        [cell("Critical Threats"), cell(level_totals.get("CRITICAL", 0))],
        [cell("High Threats"), cell(level_totals.get("HIGH", 0))],
        [cell("Medium Threats"), cell(level_totals.get("MEDIUM", 0))],
        [cell("Distinct Asset Classes"), cell(len(inventory))],
    ]
    story.append(build_table(metadata_rows, [0.35, 0.65]))

    story.append(Paragraph("Active Threat Inventory", heading_style))
    if inventory:
        inventory_rows = [[
            cell("Asset Class", header_cell_style), cell("Count", header_cell_style),
            cell("Threat Level", header_cell_style), cell("Avg Confidence", header_cell_style),
            cell("Peak Confidence", header_cell_style),
        ]]
        for row in inventory:
            inventory_rows.append([
                cell(row["class_name"]), cell(row["total"]), level_cell(row["threat_level"]),
                cell(f"{row['avg_conf'] * 100:.1f}%"), cell(f"{row['max_conf'] * 100:.1f}%"),
            ])
        story.append(build_table(inventory_rows, [0.34, 0.12, 0.18, 0.18, 0.18]))
    else:
        story.append(Paragraph("No detections were logged for this session.", body_style))

    story.append(Paragraph("TechInt Context Summary", heading_style))
    if inventory:
        techint_rows = [[
            cell("Asset Class", header_cell_style), cell("Estimated Manufacturer", header_cell_style),
            cell("Primary Role", header_cell_style), cell("Threat Assessment", header_cell_style),
        ]]
        for row in inventory:
            record = database.get_techint(row["class_name"]) or {}
            techint_rows.append([
                cell(row["class_name"]),
                cell(record.get("manufacturer", "Unknown")),
                cell(record.get("role", "Unclassified Hardware Asset")),
                cell(record.get("assessment", "UNDETERMINED")),
            ])
        story.append(build_table(techint_rows, [0.22, 0.24, 0.24, 0.30]))
    else:
        story.append(Paragraph("No TechInt records applicable.", body_style))

    story.append(Paragraph("Highest-Confidence Detection Log", heading_style))
    if top_detections:
        detail_rows = [[
            cell("Detection ID", header_cell_style), cell("Asset Class", header_cell_style),
            cell("Confidence", header_cell_style), cell("Threat Level", header_cell_style),
        ]]
        for row in top_detections:
            detail_rows.append([
                cell(row["detection_id"]), cell(row["class_name"]),
                cell(f"{row['confidence'] * 100:.1f}%"), level_cell(row["threat_level"]),
            ])
        story.append(build_table(detail_rows, [0.18, 0.40, 0.20, 0.22]))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Showing {len(top_detections)} of {total_detections} logged detections, ranked by confidence.",
            body_style,
        ))
    else:
        story.append(Paragraph("No detection records available.", body_style))

    story.append(Spacer(1, 14))
    story.append(Paragraph(escape(settings.DISCLAIMER_TEXT), disclaimer_style))

    document.build(story)
    return output_path
