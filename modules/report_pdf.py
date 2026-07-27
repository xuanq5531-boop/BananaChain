
from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import re
import uuid
from typing import Any, Iterable

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

GREEN = colors.HexColor("#2F7D32")
DARK_GREEN = colors.HexColor("#1E5423")
LIGHT_GREEN = colors.HexColor("#EAF5E8")
GOLD = colors.HexColor("#D89A00")
DARK = colors.HexColor("#263238")
MUTED = colors.HexColor("#607D68")
BORDER = colors.HexColor("#C9DDC7")
LIGHT_GREY = colors.HexColor("#F5F7F4")
WARNING = colors.HexColor("#FFF4D6")

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    """Register Unicode fonts when available, including Chinese support."""
    global FONT_REGULAR, FONT_BOLD
    candidates = [
        (
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            try:
                pdfmetrics.registerFont(TTFont("BananaRegular", str(regular)))
                pdfmetrics.registerFont(TTFont("BananaBold", str(bold)))
                FONT_REGULAR = "BananaRegular"
                FONT_BOLD = "BananaBold"
                return
            except Exception:
                continue


_register_fonts()


def _clean(value: Any) -> str:
    text = str(value or "")
    # ReportLab paragraphs use a small HTML subset. Escape unsafe symbols.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Remove most emoji/symbols that may render inconsistently in PDF fonts.
    text = re.sub(
        r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]",
        "",
        text,
    )
    return text.strip()


def _list_items(items: Iterable[Any]) -> list[str]:
    return [_clean(item) for item in items if str(item or "").strip()]


def _report_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now():%Y%m%d-%H%M}-{uuid.uuid4().hex[:6].upper()}"


def _styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=27,
            textColor=DARK_GREEN,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName=FONT_REGULAR,
            fontSize=10,
            leading=14,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        ),
        "h1": ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=13,
            leading=17,
            textColor=DARK_GREEN,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=9.5,
            leading=14,
            textColor=DARK,
            spaceAfter=1.8 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=11,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=9.2,
            leading=13.5,
            leftIndent=5 * mm,
            firstLineIndent=-3 * mm,
            bulletIndent=1.5 * mm,
            textColor=DARK,
            spaceAfter=1.4 * mm,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
            alignment=TA_CENTER,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=styles["BodyText"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=15,
            textColor=DARK_GREEN,
            alignment=TA_CENTER,
        ),
        "warning": ParagraphStyle(
            "Warning",
            parent=styles["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8.2,
            leading=12,
            textColor=colors.HexColor("#6A4B00"),
        ),
    }


def _footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(BORDER)
    canvas.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
    canvas.setFont(FONT_REGULAR, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 8 * mm, "BananaChain AI - Evidence-Based Decision Support")
    canvas.drawRightString(width - 18 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _document(buffer: BytesIO):
    frame = Frame(
        17 * mm,
        18 * mm,
        A4[0] - 34 * mm,
        A4[1] - 34 * mm,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    template = PageTemplate(id="report", frames=[frame], onPage=_footer)
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        title="BananaChain AI Report",
        author="BananaChain AI",
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    doc.addPageTemplates([template])
    return doc


def _pil_to_flowable(image_data: Any, max_width=75 * mm, max_height=55 * mm):
    try:
        if isinstance(image_data, PILImage.Image):
            image = image_data.copy()
        else:
            image = PILImage.fromarray(image_data)
        image = image.convert("RGB")
        temp = BytesIO()
        image.save(temp, format="JPEG", quality=88)
        temp.seek(0)
        width, height = image.size
        ratio = min(max_width / width, max_height / height)
        return Image(temp, width=width * ratio, height=height * ratio)
    except Exception:
        return None


def _header(story, styles, title: str, subtitle: str, report_id: str, logo_path: Path | None):
    logo = None
    if logo_path and Path(logo_path).exists():
        try:
            logo = Image(str(logo_path), width=22 * mm, height=22 * mm)
        except Exception:
            logo = None

    title_block = [
        Paragraph(_clean(title), styles["title"]),
        Paragraph(_clean(subtitle), styles["subtitle"]),
    ]
    if logo:
        table = Table([[logo, title_block]], colWidths=[28 * mm, 145 * mm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, 0), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(table)
    else:
        story.extend(title_block)

    meta = Table(
        [
            [
                Paragraph("<b>Report ID</b><br/>" + _clean(report_id), styles["small"]),
                Paragraph("<b>Generated</b><br/>" + datetime.now().strftime("%d %B %Y, %H:%M"), styles["small"]),
                Paragraph("<b>Purpose</b><br/>Portable decision record", styles["small"]),
            ]
        ],
        colWidths=[58 * mm, 58 * mm, 58 * mm],
    )
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    story.extend([meta, Spacer(1, 4 * mm)])


def _metrics(story, styles, metrics: list[tuple[str, str]]):
    cells = []
    for label, value in metrics:
        cells.append([
            Paragraph(_clean(value), styles["metric_value"]),
            Paragraph(_clean(label), styles["metric_label"]),
        ])
    table = Table([cells], colWidths=[174 * mm / len(cells)] * len(cells))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story.extend([table, Spacer(1, 3 * mm)])


def _section(story, styles, heading: str, paragraphs=None, bullets=None):
    story.append(Paragraph(_clean(heading), styles["h1"]))
    for paragraph in paragraphs or []:
        story.append(Paragraph(_clean(paragraph).replace("\n", "<br/>"), styles["body"]))
    for item in _list_items(bullets or []):
        story.append(Paragraph("• " + item.replace("\n", "<br/>"), styles["bullet"]))


def _sources(story, styles, sources):
    if not sources:
        return
    story.append(Paragraph("Evidence Sources", styles["h1"]))
    for source in sources:
        title = _clean(source.get("short", "Source"))
        url = _clean(source.get("url", ""))
        story.append(Paragraph(f"• {title}<br/><font size='7'>{url}</font>", styles["bullet"]))


def _disclaimer(story, styles, text: str):
    box = Table([[Paragraph(_clean(text), styles["warning"])]], colWidths=[174 * mm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WARNING),
        ("BOX", (0, 0), (-1, -1), 0.7, GOLD),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
    ]))
    story.extend([Spacer(1, 3 * mm), box])


def build_disease_report(
    *,
    report_scope: str,
    language: str,
    result: dict,
    disease: dict,
    weather: dict | None,
    weather_advice: list[str],
    references: list[dict],
    disclaimer: str,
    confidence_note: str,
    logo_path: Path | None = None,
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = _document(buffer)
    story = []
    report_id = _report_id("DX")

    full = report_scope == "full"
    title = "Banana Disease Management Report" if full else "Banana Diagnostic Report"
    subtitle = (
        "Diagnosis, field recommendations and evidence record"
        if full else
        "Portable AI screening result for inspection and discussion"
    )
    _header(story, styles, title, subtitle, report_id, logo_path)

    image = _pil_to_flowable(result.get("img_raw"))
    summary = [
        Paragraph(
            f"<b>Predicted condition:</b> {_clean(result.get('pred_class', '')).title()}<br/>"
            f"<b>Severity:</b> {_clean(disease.get('severity', {}).get(language, ''))}<br/>"
            f"<b>Model confidence:</b> {float(result.get('confidence', 0))*100:.1f}%<br/>"
            f"<font size='8'>{_clean(confidence_note)}</font>",
            styles["body"],
        )
    ]
    if image:
        summary_table = Table([[image, summary]], colWidths=[78 * mm, 96 * mm])
    else:
        summary_table = Table([[summary]], colWidths=[174 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story.extend([summary_table, Spacer(1, 2 * mm)])

    _section(
        story,
        styles,
        "Diagnostic Interpretation",
        paragraphs=[disease.get("what_is_it", {}).get(language, "")],
    )

    if weather:
        _section(
            story,
            styles,
            "Field Conditions at Assessment",
            paragraphs=[
                f"{weather.get('city', '')}: {weather.get('temp', '')}°C, "
                f"{weather.get('humidity', '')}% humidity, "
                f"{weather.get('description', '')}."
            ],
        )

    if full:
        if weather_advice:
            _section(story, styles, "Weather-Aware Advice", bullets=weather_advice)
        _section(
            story,
            styles,
            "Immediate Actions",
            bullets=disease.get("immediate_actions", {}).get(language, []),
        )
        _section(
            story,
            styles,
            "Prevention",
            bullets=disease.get("prevention_tips", {}).get(language, []),
        )
        _section(
            story,
            styles,
            "Monitoring",
            paragraphs=[disease.get("monitoring_schedule", {}).get(language, "")],
        )
        estimated_loss = disease.get("estimated_loss")
        if estimated_loss:
            _section(
                story,
                styles,
                "Potential Economic Impact",
                paragraphs=[estimated_loss.get(language, "")],
            )
        contact = disease.get("contact")
        if contact:
            _section(story, styles, "Where to Seek Help", paragraphs=[contact])
        _sources(story, styles, references)

    _disclaimer(story, styles, disclaimer)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This report may be shared with growers, buyers, sellers, inspectors or advisers "
        "as a decision-support record. Confirm high-impact disease decisions through an "
        "authorised agricultural or laboratory service.",
        styles["small"],
    ))
    doc.build(story)
    return buffer.getvalue()


def build_ripeness_report(
    *,
    report_scope: str,
    language: str,
    result: dict,
    decision: dict,
    user_type: str,
    price_info: dict,
    references: list[dict],
    disclaimer: str,
    confidence_note: str,
    logo_path: Path | None = None,
) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = _document(buffer)
    story = []
    report_id = _report_id("SC")

    titles = {
        "assessment": ("Banana Quality Assessment", "Ripeness and condition record"),
        "recommendations": ("Banana Handling Recommendation", "Recommended next actions for the selected stakeholder"),
        "price": ("Banana Price Reference", "Observed market reference for negotiation and comparison"),
        "full": ("Banana End-to-End Decision Report", "Quality, handling, market and financial decision support"),
    }
    title, subtitle = titles.get(report_scope, titles["full"])
    _header(story, styles, title, subtitle, report_id, logo_path)

    if report_scope in {"assessment", "full"}:
        image = _pil_to_flowable(result.get("img_raw"))
        assessment_text = [
            Paragraph(
                f"<b>Ripeness result:</b> {_clean(result.get('pred_class', '')).title()}<br/>"
                f"<b>Status:</b> {_clean(decision.get('status', {}).get(language, ''))}<br/>"
                f"<b>Model confidence:</b> {float(result.get('confidence', 0))*100:.1f}%<br/>"
                f"<b>Estimated shelf life:</b> {_clean(decision.get('shelf_life', ''))}<br/>"
                f"<b>Urgency:</b> {_clean(decision.get('urgency', {}).get(language, ''))}<br/>"
                f"<font size='8'>{_clean(confidence_note)}</font>",
                styles["body"],
            )
        ]
        if image:
            assessment_table = Table([[image, assessment_text]], colWidths=[78 * mm, 96 * mm])
        else:
            assessment_table = Table([[assessment_text]], colWidths=[174 * mm])
        assessment_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
        ]))
        story.extend([assessment_table, Spacer(1, 2 * mm)])
        _section(
            story,
            styles,
            "Quality Interpretation",
            paragraphs=[decision.get("what_it_means", {}).get(language, "")],
        )

    if report_scope in {"recommendations", "full"}:
        _metrics(
            story,
            styles,
            [
                ("Stakeholder", user_type),
                ("Variety", result.get("variety", "")),
                ("Quantity", f"{result.get('quantity', 0)} kg"),
            ],
        )
        _section(
            story,
            styles,
            "Recommended Actions",
            bullets=decision.get("actions_for_user", {}).get(language, []),
        )
        _section(
            story,
            styles,
            "Storage and Handling",
            bullets=decision.get("storage", {}).get(language, []),
        )

    if report_scope in {"price", "full"}:
        observed_price = float(price_info.get("observed_price", 0) or 0)
        quantity = float(result.get("quantity", 0) or 0)
        full_value = float(price_info.get("full_value", quantity * observed_price) or 0)
        salvage = float(price_info.get("recoverable_value", decision.get("salvage_value", 0)) or 0)
        loss = float(price_info.get("potential_loss", max(full_value - salvage, 0)) or 0)

        _metrics(
            story,
            styles,
            [
                ("Observed reference", f"RM {observed_price:.2f}/kg"),
                ("Reference lot value", f"RM {full_value:.2f}"),
                ("Recoverable value", f"RM {salvage:.2f}"),
                ("Potential difference", f"RM {loss:.2f}"),
            ],
        )
        price_rows = [
            ["Variety", result.get("variety", "")],
            ["Quantity", f"{quantity:.0f} kg"],
            ["Observed date", price_info.get("date") or "Not available"],
            ["Observed range", price_info.get("range") or "Not available"],
            ["Data source", "PriceCatcher/KPDN-linked data via manamurah.com"],
        ]
        table = Table(
            [[Paragraph(f"<b>{_clean(a)}</b>", styles["body"]), Paragraph(_clean(b), styles["body"])] for a, b in price_rows],
            colWidths=[48 * mm, 126 * mm],
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREEN),
            ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
            ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
        ]))
        story.extend([Paragraph("Price Reference", styles["h1"]), table])
        story.append(Paragraph(
            "The price is an observed reference, not a guaranteed farm-gate, wholesale or retail transaction price. "
            "Final value depends on location, grade, volume, buyer requirements, logistics and negotiation.",
            styles["small"],
        ))

    _sources(story, styles, references)
    _disclaimer(story, styles, disclaimer)
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(
        "This report is designed to support convenient information sharing between sellers, "
        "buyers, farmers, retailers, processors and advisers. It does not replace physical "
        "inspection, contractual grading or professional confirmation.",
        styles["small"],
    ))
    doc.build(story)
    return buffer.getvalue()
