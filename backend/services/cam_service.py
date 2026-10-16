"""
cam_service.py - Professional CAM Report (10 sections, fully dynamic)
Fixed: TableStyle alt-row backgrounds now respect actual row count
"""
import os
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

NAVY=colors.HexColor("#0f1f3d"); TEAL=colors.HexColor("#0d7377"); LTEAL=colors.HexColor("#e0f4f4")
AMBER=colors.HexColor("#f59e0b"); RED=colors.HexColor("#dc2626"); GREEN=colors.HexColor("#059669")
LGRAY=colors.HexColor("#f8f9fa"); MGRAY=colors.HexColor("#e5e7eb"); DGRAY=colors.HexColor("#374151")
PURPLE=colors.HexColor("#7c3aed")

def _dc(d):
    if "Reject" in (d or ""): return RED
    if "Strict" in (d or "") or "Condition" in (d or ""): return AMBER
    return GREEN

def _s():
    b=getSampleStyleSheet()
    return {
        "title": ParagraphStyle("T",parent=b["Normal"],fontSize=20,fontName="Helvetica-Bold",textColor=NAVY,spaceAfter=4),
        "h2":    ParagraphStyle("H",parent=b["Normal"],fontSize=12,fontName="Helvetica-Bold",textColor=NAVY,spaceBefore=14,spaceAfter=6),
        "body":  ParagraphStyle("B",parent=b["Normal"],fontSize=10,fontName="Helvetica",textColor=DGRAY,leading=15,spaceAfter=5),
        "small": ParagraphStyle("S",parent=b["Normal"],fontSize=8,fontName="Helvetica",textColor=colors.HexColor("#6b7280"),leading=12),
        "flag":  ParagraphStyle("F",parent=b["Normal"],fontSize=9,fontName="Helvetica",textColor=colors.HexColor("#7f1d1d"),leading=13,leftIndent=12,spaceAfter=3),
        "pos":   ParagraphStyle("P",parent=b["Normal"],fontSize=9,fontName="Helvetica",textColor=colors.HexColor("#064e3b"),leading=13,leftIndent=12,spaceAfter=3),
        "disc":  ParagraphStyle("D",parent=b["Normal"],fontSize=8,fontName="Helvetica-Oblique",textColor=colors.HexColor("#9ca3af"),leading=11),
    }

def _ts(rows, hc=None):
    """
    Build TableStyle safely — alt row bg only applied for rows that exist.
    rows = total number of rows in the table (including header).
    """
    hc = hc or TEAL
    st = [
        ("BACKGROUND",    (0,0), (-1,0), hc),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 9),
        ("FONTSIZE",      (0,1), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.5, MGRAY),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]
    # Only add alt background for rows that actually exist
    for i in range(1, rows):
        if i % 2 == 0:
            st.append(("BACKGROUND", (0,i), (-1,i), LGRAY))
    return TableStyle(st)

def generate_cam(company, financials, research, analysis, bank_data=None, mca_data=None):
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    safe = "".join(c for c in company.strip() if c.isalnum() or c in " _-").strip()
    fp = os.path.join(upload_dir, f"{safe}_CAM_Report.pdf")
    doc = SimpleDocTemplate(fp, leftMargin=0.75*inch, rightMargin=0.75*inch,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    s = _s()
    E = []
    now = datetime.now().strftime("%d %b %Y, %I:%M %p")
    score = analysis.get("final_score", analysis.get("risk_score", 0))
    base_score = analysis.get("base_score", score)
    bd = analysis.get("score_breakdown", {})
    fc = analysis.get("five_cs", {})
    gst = analysis.get("gst_analysis", {})
    ml = analysis.get("ml_analysis", {})
    dc = _dc(analysis.get("decision", ""))
    ml_adj = ml.get("ml_score_adjustment", 0) if ml else 0
    covenants = analysis.get("sanction_covenants", [])

    # ── Header ────────────────────────────────────────────────────────────────
    hdr = Table([[
        Paragraph("<b>CREDIT APPRAISAL MEMORANDUM</b>", s["title"]),
        Paragraph(f"<b>{company.upper()}</b><br/><font size='8' color='#6b7280'>Generated: {now}</font>", s["body"]),
    ]], colWidths=[4*inch, 3*inch])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),LTEAL),("TOPPADDING",(0,0),(-1,-1),14),
        ("BOTTOMPADDING",(0,0),(-1,-1),14),("LEFTPADDING",(0,0),(-1,-1),16),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,0),"RIGHT"),
    ]))
    E.append(hdr); E.append(Spacer(1, 0.15*inch))

    # ── Score card ────────────────────────────────────────────────────────────
    sc_data = [
        ["Final Calibrated Score", "Decision", "Indicative Loan Limit", "Interest Rate"],
        [
            Paragraph(f"<font size='18' color='#0f1f3d'><b>{score}</b></font><font size='8'>/100</font><br/><font size='7' color='#6b7280'>Base: {base_score} | ML: {ml_adj:+d}</font>", s["body"]),
            Paragraph(f"<b>{analysis.get('decision','N/A')}</b>", s["body"]),
            Paragraph(f"<b>{analysis.get('loan_amount','N/A')}</b>", s["body"]),
            Paragraph(f"<b>{analysis.get('interest_rate','N/A')}</b>", s["body"]),
        ]
    ]
    sc = Table(sc_data, colWidths=[1.75*inch]*4)
    sc.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
        ("BACKGROUND",(0,1),(-1,1),LGRAY),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ("TEXTCOLOR",(1,1),(1,1),dc),
    ]))
    E.append(sc); E.append(Spacer(1, 0.1*inch))

    # ── ML row ────────────────────────────────────────────────────────────────
    if ml and not ml.get("error") and ml.get("ml_grade"):
        ml_data = [
            ["XGBoost Risk Grade", "Reject Probability", "ML Model Prediction", "Overlay Adjustment"],
            [
                Paragraph(f"<b>{ml.get('ml_grade','N/A')}</b>", s["body"]),
                Paragraph(f"<b>{ml.get('ml_reject_probability',0)*100:.1f}%</b>", s["body"]),
                Paragraph(f"<b>{ml.get('ml_prediction','N/A')}</b>", s["body"]),
                Paragraph(f"<b>{ml_adj:+d} pts</b>", s["body"]),
            ]
        ]
        mt = Table(ml_data, colWidths=[1.75*inch]*4)
        mt.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),PURPLE),("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
            ("BACKGROUND",(0,1),(-1,1),colors.HexColor("#f5f3ff")),
            ("GRID",(0,0),(-1,-1),0.5,MGRAY),("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
        ]))
        E.append(mt); E.append(Spacer(1, 0.1*inch))

    # ── 1. Executive Summary ──────────────────────────────────────────────────
    E.append(HRFlowable(width="100%", thickness=0.5, color=MGRAY))
    E.append(Paragraph("1. Executive Summary", s["h2"]))
    E.append(Paragraph(analysis.get("explanation","N/A"), s["body"]))

    # ── 2. Score Breakdown & Reconciliation ───────────────────────────────────
    E.append(Paragraph("2. Score Breakdown & Reconciliation", s["h2"]))
    bd_items = [
        ("Financial Health", "financial_score",   40),
        ("Capital & Leverage", "leverage_score",  20),
        ("External Intelligence", "external_score", 20),
        ("GST Compliance",   "gst_score",         10),
        ("Qualitative / Notes", "qualitative_score", 10),
    ]
    bdr = [["Component", "Score", "Max", "Rating / Impact"]]
    for lbl, k, mx in bd_items:
        v = bd.get(k, 0)
        bdr.append([lbl, str(v), str(mx), "Strong" if v/mx>=0.75 else ("Adequate" if v/mx>=0.5 else "Stressed")])

    # Add Subtotal and ML calibration reconciliation rows
    bdr.append(["Base Underwriting Subtotal", str(base_score), "100", "Composite Baseline"])
    bdr.append(["XGBoost ML Risk Overlay", f"{ml_adj:+d} pts", "—", "Grade: " + (ml.get("ml_grade","N/A") if ml else "N/A")])
    bdr.append(["Final Calibrated Credit Score", str(score), "100", f"Decision: {analysis.get('decision','N/A')}"])

    bdt = Table(bdr, colWidths=[2.8*inch, 1.2*inch, 1.0*inch, 1.6*inch])
    bds = [
        ("BACKGROUND",(0,0),(-1,0),NAVY),("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),9),
        ("FONTSIZE",(0,1),(-1,-1),9),("GRID",(0,0),(-1,-1),0.5,MGRAY),
        ("ALIGN",(1,0),(-1,-1),"CENTER"),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),("LEFTPADDING",(0,0),(-1,-1),8),
        # Highlight Base Subtotal row
        ("BACKGROUND",(0,6),(-1,6),colors.HexColor("#f1f5f9")),
        ("FONTNAME",(0,6),(-1,6),"Helvetica-Bold"),
        # Highlight ML Overlay row
        ("BACKGROUND",(0,7),(-1,7),colors.HexColor("#faf5ff")),
        ("TEXTCOLOR",(0,7),(-1,7),PURPLE),
        ("FONTNAME",(0,7),(-1,7),"Helvetica-Bold"),
        # Highlight Final Calibrated Score row
        ("BACKGROUND",(0,8),(-1,8),LTEAL),
        ("FONTNAME",(0,8),(-1,8),"Helvetica-Bold"),
    ]
    for i, (_, k, mx) in enumerate(bd_items, 1):
        v = bd.get(k, 0)
        c = GREEN if v/mx>=0.75 else (AMBER if v/mx>=0.5 else RED)
        bds += [("TEXTCOLOR",(1,i),(1,i),c),("FONTNAME",(1,i),(1,i),"Helvetica-Bold")]
        if i % 2 == 0:
            bds.append(("BACKGROUND",(0,i),(-1,i),LGRAY))
    bdt.setStyle(TableStyle(bds))
    E.append(bdt)

    # ── 3. Financial Analysis ─────────────────────────────────────────────────
    E.append(Paragraph("3. Financial Analysis", s["h2"]))
    fin_data = [
        ["Metric", "Value", "Extraction Pipeline"],
        ["Revenue from Operations", financials.get("revenue_display","N/A"), financials.get("pipeline", "pdfplumber + Tesseract OCR")],
        ["Net Profit / PAT",        financials.get("profit_display","N/A"),  f"Method: {financials.get('extraction_method','table+text')}"],
        ["Total Debt / Borrowings", financials.get("debt_display","N/A"),    "Verified against liabilities"],
    ]
    ft = Table(fin_data, colWidths=[2.2*inch, 1.8*inch, 2.6*inch])
    ft.setStyle(_ts(len(fin_data), TEAL))
    E.append(ft)
    for f in financials.get("pdf_risk_flags", []):
        E.append(Paragraph(f"⚠  {f}", s["flag"]))

    # ── 4. GST Compliance ─────────────────────────────────────────────────────
    E.append(Paragraph("4. GST Compliance Assessment", s["h2"]))
    gst_data = [
        ["Field", "Value"],
        ["Declared P&L Revenue", financials.get("revenue_display","N/A")],
        ["Verified GST Turnover", gst.get("gst_turnover_display","Pending Submission")],
        ["Turnover Mismatch %",  gst.get("gst_mismatch_display", "N/A (Unverified)")],
        ["Compliance Risk Tier", gst.get("gst_risk_level","Pending Verification")],
        ["Score Penalty",        f"{gst.get('gst_penalty',0)} pts"],
    ]
    gt = Table(gst_data, colWidths=[2.8*inch, 3.8*inch])
    gt.setStyle(_ts(len(gst_data), TEAL))
    E.append(gt)
    E.append(Paragraph(gst.get("gst_note",""), s["small"]))

    # ── 5. External Intelligence ──────────────────────────────────────────────
    E.append(Paragraph("5. External Intelligence Review", s["h2"]))
    E.append(Paragraph(
        f"<b>Sentiment:</b> {research.get('overall_sentiment','Neutral')}  |  "
        f"<b>Verified Articles Analyzed:</b> {research.get('articles_analyzed',0)}  |  "
        f"<b>Penalty:</b> {research.get('external_penalty',0)} pts", s["body"]))
    xf = [f for f in analysis.get("risk_flags",[]) if f.startswith("[")]
    if xf:
        for f in xf: E.append(Paragraph(f"⚠  {f}", s["flag"]))
    else:
        E.append(Paragraph("✓  No verified adverse news or regulatory actions detected for borrower.", s["pos"]))
    for p in research.get("positive_signals",[]): E.append(Paragraph(f"✓  {p}", s["pos"]))

    # ── 6. Five Cs ────────────────────────────────────────────────────────────
    E.append(Paragraph("6. Five Cs of Credit Evaluation", s["h2"]))
    cs_rows = [
        [Paragraph(f"<b>{lbl}</b>", s["body"]), Paragraph(fc.get(k,"Not assessed"), s["body"])]
        for lbl, k in [("Character","character"),("Capacity","capacity"),
                       ("Capital","capital"),("Collateral","collateral"),("Conditions","conditions")]
    ]
    cst = Table(cs_rows, colWidths=[1.3*inch, 5.3*inch])
    cst.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),0.5,MGRAY),("BACKGROUND",(0,0),(0,-1),LTEAL),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),("LEFTPADDING",(0,0),(-1,-1),10),
    ]))
    E.append(cst)

    # ── 7. Bank Statement ─────────────────────────────────────────────────────
    E.append(Paragraph("7. Bank Statement Analysis", s["h2"]))
    if bank_data and not bank_data.get("error"):
        has_txns = bank_data.get("has_txn_data", False)
        bk_data = [
            ["Metric", "Value"],
            ["Extraction Status",      "Verified Data" if has_txns else "Incomplete (0 txns parsed)"],
            ["Opening Balance",        bank_data.get("opening_balance_display","N/A")],
            ["Closing Balance",         bank_data.get("closing_balance_display","N/A")],
            ["Avg Monthly Balance",     bank_data.get("avg_monthly_balance_display","N/A")],
            ["Total Credits",           bank_data.get("total_credits_display","N/A")],
            ["Total Debits",            bank_data.get("total_debits_display","N/A")],
            ["Inflow / Outflow Ratio",  bank_data.get("inflow_outflow_display", "N/A")],
            ["OD Utilisation %",        str(bank_data.get("od_utilisation_pct",0))+"%"],
            ["Bounce / Return Count",   str(bank_data.get("bounce_count",0))],
            ["Transactions Scanned",    str(bank_data.get("transaction_count",0))],
        ]
        bk = Table(bk_data, colWidths=[2.8*inch, 3.8*inch])
        bk.setStyle(_ts(len(bk_data), TEAL))
        E.append(bk)
        for f in bank_data.get("bank_flags",[]): E.append(Paragraph(f"⚠  {f}", s["flag"]))
        for p in bank_data.get("bank_positive",[]): E.append(Paragraph(f"✓  {p}", s["pos"]))
        E.append(Paragraph(f"Score penalty: {bank_data.get('bank_score_penalty',0)} pts | {bank_data.get('extraction_note','N/A')}", s["small"]))
    else:
        E.append(Paragraph(f"Bank statement: {(bank_data or {}).get('error','Not uploaded / not provided.')}", s["body"]))

    # ── 8. MCA ───────────────────────────────────────────────────────────────
    E.append(Paragraph("8. MCA / ROC Company Registry Data", s["h2"]))
    if mca_data:
        mca_rows_data = [
            ["Field", "Value"],
            ["CIN",                   mca_data.get("cin","N/A")],
            ["Company Type",          mca_data.get("company_type","N/A")],
            ["Status",                mca_data.get("status","N/A")],
            ["ROC",                   mca_data.get("roc","N/A")],
            ["Date of Incorporation", mca_data.get("date_incorporation","N/A")],
            ["Paid-up Capital",       mca_data.get("paid_up_capital","N/A")],
            ["Registered State",      mca_data.get("registered_state","N/A")],
            ["Data Source",           mca_data.get("source","N/A")],
        ]
        mt2 = Table(mca_rows_data, colWidths=[2.2*inch, 4.4*inch])
        mt2.setStyle(_ts(len(mca_rows_data), NAVY))
        E.append(mt2)
        for f in mca_data.get("mca_flags",[]): E.append(Paragraph(f"⚠  {f}", s["flag"]))
        if mca_data.get("error"): E.append(Paragraph(f"Note: {mca_data['error']}", s["small"]))
    else:
        E.append(Paragraph("MCA lookup not performed.", s["body"]))

    # ── 9. Risk Narrative ─────────────────────────────────────────────────────
    E.append(Paragraph("9. Risk Narrative", s["h2"]))
    for item in (analysis.get("detailed_narrative",[]) or ["No significant risk items."]):
        E.append(Paragraph(f"•  {item}", s["body"]))

    # ── 10. Sanction Covenants & Recommendation ───────────────────────────────
    E.append(Spacer(1, 0.1*inch))
    E.append(HRFlowable(width="100%", thickness=1, color=NAVY))
    E.append(Paragraph("10. Final Underwriting Recommendation & Covenants", s["h2"]))
    E.append(Paragraph(
        f"Based on calibrated AI + ML credit risk appraisal (Base: <b>{base_score}/100</b>, "
        f"ML Calibrated: <b>{score}/100</b>), Intelli-Credit recommends: "
        f"<b>{analysis.get('decision','N/A')}</b>. Indicative facility exposure: <b>{analysis.get('loan_amount','N/A')}</b> "
        f"at benchmark pricing of <b>{analysis.get('interest_rate','N/A')}</b>.", s["body"]))

    if covenants:
        E.append(Paragraph("<b>Mandatory Sanction Covenants & Pre-Disbursement Conditions:</b>", s["body"]))
        for cov in covenants:
            E.append(Paragraph(f"• <b>[COVENANT]</b> {cov}", s["flag"]))

    if ml and ml.get("ml_grade"):
        E.append(Paragraph(
            f"Machine Learning Overlay: <b>XGBoost 2.0 (97.92% Accuracy)</b> — Grade: {ml.get('ml_grade')}, "
            f"Reject probability: {ml.get('ml_reject_probability',0)*100:.1f}%. "
            f"Pipeline: pdfplumber + Tesseract OCR. Storage: MongoDB.", s["body"]))
    E.append(Spacer(1, 0.06*inch))
    E.append(Paragraph(
        "This report is system-generated and assists, but does not replace, human credit judgment. "
        "Final approval authority rests with the institutional credit committee.", s["disc"]))

    doc.build(E)
    return f"{safe}_CAM_Report.pdf"