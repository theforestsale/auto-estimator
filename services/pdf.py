import io
import json

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.helpers import estimate_totals, money

PAGE_W, PAGE_H = letter
MARGIN = 0.75 * inch


def render_estimate_pdf(estimate, shop):
    """Return estimate PDF bytes as rendered from the stored AI payload."""
    ai_data = json.loads(estimate.ai_json or "{}")
    totals = estimate_totals(ai_data, estimate.labor_rate, estimate.tax_rate)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        rightMargin=MARGIN,
        leftMargin=MARGIN,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title=f"Estimate {estimate.id}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=18, leading=22))
    styles.add(ParagraphStyle(name="Muted", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.grey))
    styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14))

    story = []

    header = Table(
        [
            [
                Paragraph(f"<b>{escape(shop['name'])}</b>", styles["H1"]),
                Paragraph(
                    f"<b>ESTIMATE #{estimate.id}</b><br/>"
                    f"<font size=9 color='#555555'>Created {estimate.created_at.strftime('%b %d, %Y')}<br/>"
                    f"Status: {escape(estimate.status)}</font>",
                    styles["Body"],
                ),
            ]
        ],
        colWidths=[3.6 * inch, 3.0 * inch],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(header)

    contact = Paragraph(
        f"<font size=9 color='#555555'>{escape(shop['phone'])} &nbsp; {escape(shop['email'])}<br/>"
        f"{escape(shop['address'])}</font>",
        styles["Body"],
    )
    story.append(contact)
    story.append(Spacer(1, 14))

    vehicle = Table(
        [
            [Paragraph("<b>Customer</b>", styles["Body"]), Paragraph("<b>Vehicle</b>", styles["Body"])],
            [
                Paragraph(escape(estimate.customer_name), styles["Body"]),
                Paragraph(
                    f"{estimate.year or '—'} {escape(estimate.make)} {escape(estimate.model)}"
                    f"{('<br/>' + escape(estimate.mileage) + ' miles') if estimate.mileage else ''}",
                    styles["Body"],
                ),
            ],
            [Paragraph("<b>Complaint</b>", styles["Body"]), ""],
            [Paragraph(escape(estimate.issue_desc), styles["Body"]), ""],
        ],
        colWidths=[3.0 * inch, 3.6 * inch],
    )
    vehicle.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(vehicle)
    story.append(Spacer(1, 16))

    if ai_data.get("diagnosis"):
        story.append(Paragraph("<b>Diagnosis</b>", styles["Body"]))
        story.append(Paragraph(escape(ai_data["diagnosis"]), styles["Body"]))
        story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Recommended Work</b>", styles["Body"]))
    story.append(Spacer(1, 6))

    rows = [["Description", "Type", "Qty", "Rate", "Amount"]]
    for item in ai_data.get("recommended_work", []):
        rows.append([
            escape(item["item"]),
            item["category"].title(),
            f"{item['quantity']:g} {item['unit_label']}",
            money(item["unit_price"]),
            money(item["quantity"] * item["unit_price"]),
        ])
    rows.append(["", "", "", "<b>Labor subtotal</b>", f"<b>{money(totals['labor'])}</b>"])

    work_table = Table(rows, colWidths=[2.9 * inch, 0.9 * inch, 0.9 * inch, 0.9 * inch, 1.0 * inch])
    work_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#195070")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor("#195070")),
    ]))
    story.append(work_table)
    story.append(Spacer(1, 12))

    totals_block = Table(
        [
            ["Parts", money(totals["parts"])],
            ["Shop supplies / misc", money(totals["misc"])],
            ["Subtotal", money(totals["subtotal"])],
            [f"Tax ({estimate.tax_rate:g}%)", money(totals["tax"])],
            ["<b>TOTAL</b>", f"<b>{money(totals['total'])}</b>"],
        ],
        colWidths=[2.2 * inch, 1.6 * inch],
    )
    totals_block.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LINEABOVE", (0, -2), (-1, -2), 0.5, colors.HexColor("#999999")),
        ("LINEBELOW", (0, -1), (-1, -1), 2, colors.black),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(totals_block)
    story.append(Spacer(1, 12))

    if ai_data.get("parts"):
        story.append(Paragraph("<b>Parts (estimated)</b>", styles["Body"]))
        story.append(Spacer(1, 4))
        part_rows = [["Part", "Est. price"]]
        for part in ai_data["parts"][:12]:
            part_rows.append([escape(part["name"]), money(part["est_price"])])
        part_table = Table(part_rows, colWidths=[5.0 * inch, 1.6 * inch])
        part_table.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dddddd")),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(part_table)
        story.append(Spacer(1, 12))

    if ai_data.get("notes"):
        story.append(Paragraph("<b>Notes</b>", styles["Body"]))
        for note in ai_data["notes"]:
            story.append(Paragraph(f"• {escape(note)}", styles["Body"]))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(PAGE_W / 2, 0.45 * inch, "Estimated cost; final price may vary after inspection.")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")