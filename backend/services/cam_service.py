import os
from datetime import datetime
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT


# ─── Color palette ────────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#0f1f3d")
TEAL       = colors.HexColor("#0d7377")
LIGHT_TEAL = colors.HexColor("#e0f4f4")
AMBER      = colors.HexColor("#f59e0b")
RED        = colors.HexColor("#dc2626")
GREEN      = colors.HexColor("#059669")
LIGHT_GRAY = colors.HexColor("#f8f9fa")
MID_GRAY   = colors.HexColor("#e5e7eb")
DARK_GRAY  = colors.HexColor("#374151")


def _decision_color(decision: str) -> colors.HexColor:
    if "Reject" in decision:
        return RED
    if "Strict" in decision:
        return AMBER
    if "Condition" in decision:
        return AMBER
    return GREEN


def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "title": ParagraphStyle(
            "CamTitle",
            parent=base["Normal"],
            fontSize=22,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "CamSubtitle",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=colors.HexColor("#6b7280"),
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "CamH2",
            parent=base["Normal"],
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "CamBody",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=DARK_GRAY,
            leading=15,
            spaceAfter=6,
        ),
        "bullet": ParagraphStyle(
            "CamBullet",
            parent=base["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=DARK_GRAY,
            leading=15,
            leftIndent=14,
            spaceAfter=4,
        ),
        "flag": ParagraphStyle(
            "CamFlag",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=colors.HexColor("#7f1d1d"),
            leading=13,
            leftIndent=14,
            spaceAfter=3,
        ),
        "positive": ParagraphStyle(
            "CamPositive",
            parent=base["Normal"],
            fontSize=9,
            fontName="Helvetica",
            textColor=colors.HexColor("#064e3b"),
            leading=13,
            leftIndent=14,
            spaceAfter=3,
        ),
    }
    return styles


def generate_cam(company: str, financials: dict, research: dict, analysis: dict, bank_data: dict | None = None, mca_data: dict | None = None) -> str:
    os.makedirs("uploads", exist_ok=True)

    safe_name = "".join(c for c in company.strip() if c.isalnum() or c in " _-").strip()
    filename = f"{safe_name}_CAM_Report.pdf"
    file_path = os.path.join("uploads", filename)

    doc = SimpleDocTemplate(
        file_path,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    s = _build_styles()
    elems = []
    decision_color = _decision_color(analysis.get("decision", ""))
    now = datetime.now().strftime("%d %B %Y, %I:%M %p")

    # ── Header bar (table trick for background) ──────────────────────────────
    header_data = [[
        Paragraph(f"<b>CREDIT APPRAISAL MEMO</b>", s["title"]),
        Paragraph(f"{company.upper()}<br/><font size='9' color='#6b7280'>Prepared: {now}</font>", s["subtitle"]),
    ]]
    header_table = Table(header_data, colWidths=[4 * inch, 3 * inch])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_TEAL),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING", (0, 0), (-1, -1), 16),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
    ]))
    elems.append(header_table)
    elems.append(Spacer(1, 0.2 * inch))

    # ── Score summary card ───────────────────────────────────────────────────
    score = analysis.get("risk_score", 0)
    breakdown = analysis.get("score_breakdown", {})

    summary_data = [
        ["Credit Score", "Decision", "Loan Amount", "Interest Rate"],
        [
            Paragraph(f"<font size='22' color='#0f1f3d'><b>{score}</b></font><font size='10'>/100</font>", s["body"]),
            Paragraph(f"<font size='13'><b>{analysis.get('decision','N/A')}</b></font>", s["body"]),
            Paragraph(f"<font size='11'>{analysis.get('loan_amount','N/A')}</font>", s["body"]),
            Paragraph(f"<font size='11'>{analysis.get('interest_rate','N/A')}</font>", s["body"]),
        ]
    ]
    summary_table = Table(summary_data, colWidths=[1.75 * inch] * 4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BACKGROUND", (0, 1), (-1, 1), LIGHT_GRAY),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TEXTCOLOR", (1, 1), (1, 1), decision_color),
    ]))
    elems.append(summary_table)
    elems.append(Spacer(1, 0.15 * inch))

    # ── Score breakdown bar ──────────────────────────────────────────────────
    elems.append(Paragraph("<b>Score Breakdown</b>", s["h2"]))
    bd_labels  = ["Financial Health (/40)", "Leverage (/20)", "External Intel (/20)", "GST Compliance (/10)", "Qualitative (/10)"]
    bd_keys    = ["financial_score", "leverage_score", "external_score", "gst_score", "qualitative_score"]
    bd_maxvals = [40, 20, 20, 10, 10]

    bd_data = [["Component", "Score", "Max"]]
    for lbl, key, mx in zip(bd_labels, bd_keys, bd_maxvals):
        val = breakdown.get(key, 0)
        ratio = val / mx if mx else 0
        bar_color = GREEN if ratio >= 0.75 else (AMBER if ratio >= 0.5 else RED)
        bd_data.append([lbl, val, mx])

    bd_table = Table(bd_data, colWidths=[3.5 * inch, 1.5 * inch, 1.5 * inch])
    bd_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]
    for i, (key, mx) in enumerate(zip(bd_keys, bd_maxvals), start=1):
        val = breakdown.get(key, 0)
        ratio = val / mx if mx else 0
        c = GREEN if ratio >= 0.75 else (AMBER if ratio >= 0.5 else RED)
        bd_style.append(("TEXTCOLOR", (1, i), (1, i), c))
        bd_style.append(("FONTNAME", (1, i), (1, i), "Helvetica-Bold"))
        if i % 2 == 0:
            bd_style.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))

    bd_table.setStyle(TableStyle(bd_style))
    elems.append(bd_table)
    elems.append(Spacer(1, 0.1 * inch))

    # ── 1. Executive Summary ─────────────────────────────────────────────────
    elems.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY))
    elems.append(Paragraph("1. Executive Summary", s["h2"]))
    elems.append(Paragraph(analysis.get("explanation", "N/A"), s["body"]))

    # ── 2. Financial Analysis ────────────────────────────────────────────────
    elems.append(Paragraph("2. Financial Analysis", s["h2"]))

    fin_data = [
        ["Metric", "Extracted Value", "Display"],
        ["Revenue from Operations", financials.get("revenue", "0"), financials.get("revenue_display", "N/A")],
        ["Net Profit / PAT",        financials.get("profit", "0"),  financials.get("profit_display", "N/A")],
        ["Total Debt / Borrowings", financials.get("debt", "0"),    financials.get("debt_display", "N/A")],
        ["Extraction Method", financials.get("extraction_method", "N/A"), "—"],
    ]
    fin_table = Table(fin_data, colWidths=[2.5 * inch, 2 * inch, 2 * inch])
    fin_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("FONTSIZE", (0, 1), (-1, -1), 10),
        ("BACKGROUND", (0, 2), (-1, 2), LIGHT_GRAY),
        ("BACKGROUND", (0, 4), (-1, 4), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elems.append(fin_table)

    # PDF risk flags
    pdf_flags = financials.get("pdf_risk_flags", [])
    if pdf_flags:
        elems.append(Spacer(1, 0.08 * inch))
        elems.append(Paragraph("<b>Document Risk Signals:</b>", s["body"]))
        for f in pdf_flags:
            elems.append(Paragraph(f"⚠  {f}", s["flag"]))

    # ── 3. GST Compliance ────────────────────────────────────────────────────
    elems.append(Paragraph("3. GST Compliance Assessment", s["h2"]))
    gst = analysis.get("gst_analysis", {})
    gst_data = [
        ["Declared Revenue",    financials.get("revenue_display", "N/A")],
        ["Estimated GST Turnover", gst.get("gst_turnover_display", "N/A")],
        ["Mismatch %",          f"{gst.get('gst_mismatch_percent', 0):.2f}%"],
        ["Risk Level",          gst.get("gst_risk_level", "N/A")],
        ["GST Penalty Applied", f"{gst.get('gst_penalty', 0)} pts"],
    ]
    gst_table = Table(gst_data, colWidths=[3 * inch, 3.5 * inch])
    gst_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GRAY),
        ("BACKGROUND", (0, 2), (-1, 2), LIGHT_GRAY),
        ("BACKGROUND", (0, 4), (-1, 4), LIGHT_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elems.append(gst_table)
    elems.append(Paragraph(gst.get("gst_note", ""), s["body"]))

    # ── 4. External Intelligence ─────────────────────────────────────────────
    elems.append(Paragraph("4. External Intelligence Review", s["h2"]))

    sentiment = research.get("overall_sentiment", "Neutral")
    articles  = research.get("articles_analyzed", 0)
    elems.append(Paragraph(
        f"<b>Overall Sentiment:</b> {sentiment} &nbsp;|&nbsp; "
        f"<b>Articles Analyzed:</b> {articles}",
        s["body"]
    ))

    ext_flags = analysis.get("risk_flags", [])
    news_flags = [f for f in ext_flags if f.startswith("[")]
    if news_flags:
        elems.append(Paragraph("<b>Adverse News Signals:</b>", s["body"]))
        for f in news_flags:
            elems.append(Paragraph(f"⚠  {f}", s["flag"]))
    else:
        elems.append(Paragraph("✓  No major adverse external signals detected.", s["positive"]))

    positive = research.get("positive_signals", [])
    if positive:
        elems.append(Paragraph("<b>Positive Signals:</b>", s["body"]))
        for p in positive:
            elems.append(Paragraph(f"✓  {p}", s["positive"]))

    # ── 5. Five Cs Evaluation ────────────────────────────────────────────────
    elems.append(Paragraph("5. Five Cs of Credit Evaluation", s["h2"]))
    five_cs = analysis.get("five_cs", {})
    cs_labels = [
        ("Character",   five_cs.get("character",   "Not assessed")),
        ("Capacity",    five_cs.get("capacity",    "Not assessed")),
        ("Capital",     five_cs.get("capital",     "Not assessed")),
        ("Collateral",  five_cs.get("collateral",  "Not assessed")),
        ("Conditions",  five_cs.get("conditions",  "Not assessed")),
    ]
    cs_data = [[Paragraph(f"<b>{c}</b>", s["body"]), Paragraph(v, s["body"])] for c, v in cs_labels]
    cs_table = Table(cs_data, colWidths=[1.4 * inch, 5.1 * inch])
    cs_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, MID_GRAY),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_TEAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    elems.append(cs_table)

    # ── 6. Risk Narrative ────────────────────────────────────────────────────
    elems.append(Paragraph("6. Risk Narrative", s["h2"]))
    narrative = analysis.get("detailed_narrative", [])
    if narrative:
        for item in narrative:
            elems.append(Paragraph(f"•  {item}", s["bullet"]))
    else:
        elems.append(Paragraph("No significant risk narrative items.", s["body"]))

    # ── 7. Final Recommendation ──────────────────────────────────────────────
    elems.append(Spacer(1, 0.1 * inch))
    elems.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    elems.append(Paragraph("7. Final Recommendation", s["h2"]))

    rec_text = (
        f"Based on the composite credit assessment, the Intelli-Credit system recommends to "
        f"<b>{analysis.get('decision', 'N/A')}</b> the proposed credit facility. "
        f"Indicative loan exposure: <b>{analysis.get('loan_amount', 'N/A')}</b> "
        f"at <b>{analysis.get('interest_rate', 'N/A')}</b>."
    )
    elems.append(Paragraph(rec_text, s["body"]))
    elems.append(Spacer(1, 0.05 * inch))
    elems.append(Paragraph(
        "<i>This report is system-generated and is intended to assist, not replace, "
        "human credit judgment. Final approval authority rests with the sanctioning committee.</i>",
        ParagraphStyle("Disclaimer", parent=s["body"], fontSize=8,
                       textColor=colors.HexColor("#9ca3af"), fontName="Helvetica-Oblique")
    ))

    doc.build(elems)
    return filename
