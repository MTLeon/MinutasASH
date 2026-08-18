"""Generador PDF nativo para minutas aprobadas."""

from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.models import MeetingMetadata, MinuteAnalysis

ASH_BLUE = colors.HexColor("#17365D")
ASH_LIGHT_BLUE = colors.HexColor("#D9EAF7")
ASH_GRAY = colors.HexColor("#5B6573")


def _text(value: object, fallback: str = "No indicado") -> str:
    clean = " ".join(str(value or "").split())
    return escape(clean or fallback)


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(ASH_GRAY)
    canvas.drawString(18 * mm, 12 * mm, "Minutas ASH")
    canvas.drawRightString(
        A4[0] - 18 * mm,
        12 * mm,
        f"Página {document.page}",
    )
    canvas.restoreState()


def generate_minute_pdf(
    analysis: MinuteAnalysis,
    metadata: MeetingMetadata,
    output_path: str | Path,
    logo_path: str | Path | None = None,
) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="MinuteTitle",
            parent=styles["Title"],
            textColor=ASH_BLUE,
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MinuteHeading",
            parent=styles["Heading2"],
            textColor=ASH_BLUE,
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MinuteBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
        )
    )
    body = styles["MinuteBody"]
    heading = styles["MinuteHeading"]
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
        title=metadata.matter or metadata.minute_number or "Minuta",
        author=metadata.minute_taker or "Minutas ASH",
    )
    story: list[Flowable] = []
    logo = Path(logo_path) if logo_path else None
    if logo and logo.is_file():
        image = Image(str(logo), width=34 * mm, height=13 * mm)
        story.append(
            Table(
                [[image]], colWidths=[A4[0] - 32 * mm], style=[("ALIGN", (0, 0), (-1, -1), "RIGHT")]
            )
        )
    story.extend(
        [
            Paragraph("MINUTA DE REUNIÓN", styles["MinuteTitle"]),
            Paragraph(_text(metadata.matter, "Sin materia"), styles["Heading3"]),
            Spacer(1, 4 * mm),
        ]
    )
    details = [
        ["N.º de minuta", _text(metadata.minute_number), "Fecha", _text(metadata.document_date)],
        ["Proyecto", _text(metadata.project_code), "Reunión", _text(metadata.meeting_date)],
        ["Cliente", _text(metadata.client), "Lugar", _text(metadata.location)],
        ["Redactor", _text(metadata.minute_taker), "Aprobó", _text(metadata.approved_by)],
    ]
    details_table = Table(
        [[Paragraph(str(cell), body) for cell in row] for row in details],
        colWidths=[29 * mm, 55 * mm, 24 * mm, 54 * mm],
        repeatRows=0,
    )
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), ASH_LIGHT_BLUE),
                ("BACKGROUND", (2, 0), (2, -1), ASH_LIGHT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AEB8C4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([details_table, Spacer(1, 5 * mm)])

    story.append(Paragraph("Objetivo y resumen", heading))
    if analysis.objective:
        story.append(Paragraph(f"<b>Objetivo:</b> {_text(analysis.objective)}", body))
    story.append(Paragraph(_text(analysis.executive_summary, "Sin resumen ejecutivo."), body))

    if metadata.attendees:
        story.append(Paragraph("Participantes", heading))
        attendee_rows = [["Nombre", "Cargo", "Organización"]]
        attendee_rows.extend(
            [
                [_text(item.name), _text(item.role, ""), _text(item.organization, "")]
                for item in metadata.attendees
            ]
        )
        attendee_table = Table(
            [[Paragraph(str(cell), body) for cell in row] for row in attendee_rows],
            colWidths=[62 * mm, 47 * mm, 53 * mm],
            repeatRows=1,
        )
        attendee_table.setStyle(_table_style())
        story.append(attendee_table)

    story.append(Paragraph("Puntos de minuta", heading))
    if analysis.items:
        item_rows = [["Tipo", "Descripción", "Responsable", "Plazo", "Evidencia"]]
        for item in analysis.items:
            item_rows.append(
                [
                    _text(item.category),
                    _text(item.description),
                    _text(item.responsible, ""),
                    _text(item.due_date_text or item.due_date_iso, ""),
                    _text(item.evidence, ""),
                ]
            )
        item_table = Table(
            [[Paragraph(str(cell), body) for cell in row] for row in item_rows],
            colWidths=[24 * mm, 68 * mm, 28 * mm, 22 * mm, 24 * mm],
            repeatRows=1,
        )
        item_table.setStyle(_table_style())
        story.append(item_table)
    else:
        story.append(Paragraph("No se registraron puntos activos.", body))

    if analysis.next_meeting:
        next_meeting = analysis.next_meeting
        story.extend(
            [
                Paragraph("Próxima reunión", heading),
                Paragraph(
                    f"{_text(next_meeting.description)} · "
                    f"{_text(next_meeting.date_text)} · {_text(next_meeting.time_text)}",
                    body,
                ),
            ]
        )
    if analysis.warnings:
        story.extend([Spacer(1, 4 * mm), Paragraph("Advertencias de revisión", heading)])
        for warning in analysis.warnings:
            story.append(Paragraph(f"• {_text(warning)}", body))

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    if not output.is_file() or output.stat().st_size < 500:
        raise RuntimeError("El PDF generado está vacío o incompleto.")
    return output


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), ASH_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AEB8C4")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F7FA")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )
