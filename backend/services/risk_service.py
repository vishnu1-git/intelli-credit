"""
risk_service.py  —  100-point weighted credit scoring model
Components:
  Financial Health   40 pts  (revenue, profit margin)
  Leverage           20 pts  (debt-to-revenue ratio)
  External Intel     20 pts  (news + PDF + bank + MCA penalties)
  GST Compliance     10 pts
  Qualitative        10 pts  (officer notes)
"""

from services.gst_service import evaluate_gst_risk

WEIGHTS = {
    "financial":   40,
    "leverage":    20,
    "external":    20,
    "gst":         10,
    "qualitative": 10,
}

OFFICER_RISK = [
    ("fraud",            10, "Fraud mentioned in officer notes"),
    ("default",          10, "Default risk flagged"),
    ("nclt",             10, "NCLT proceedings flagged"),
    ("bankruptcy",       10, "Bankruptcy risk noted"),
    ("money laundering", 10, "Money laundering concern raised"),
    ("litigation",        7, "Active litigation flagged"),
    ("regulatory",        7, "Regulatory issue flagged"),
    ("factory shutdown",  7, "Factory shutdown noted"),
    ("penalty",           5, "Penalty exposure noted"),
]
OFFICER_POSITIVE = [
    ("strong management", 3),
    ("long relationship", 2),
    ("good repayment",    3),
    ("clean record",      3),
    ("blue chip",         2),
]


# ── Component scorers ─────────────────────────────────────────────────────────

def _score_financial(revenue: float, profit: float):
    score = WEIGHTS["financial"]
    flags, narr = [], []
    if revenue <= 0:
        score -= 30
        flags.append("No revenue detected — zero turnover")
        narr.append("Revenue extraction returned zero; company may be pre-revenue or document unreadable.")
    else:
        if profit <= 0:
            score -= 15
            flags.append("Company is loss-making (negative PAT)")
            narr.append("Negative PAT signals inability to service debt from operations.")
        else:
            margin = profit / revenue * 100
            if margin < 2:
                score -= 5
                flags.append(f"Very thin profit margin ({margin:.1f}%)")
                narr.append(f"Net margin of {margin:.1f}% leaves almost no buffer for debt service.")
            elif margin < 5:
                score -= 2
                narr.append(f"Profit margin of {margin:.1f}% is below the healthy 5% threshold.")
            else:
                narr.append(f"Profit margin of {margin:.1f}% is acceptable.")
    return max(score, 0), flags, narr


def _score_leverage(revenue: float, debt: float):
    score = WEIGHTS["leverage"]
    flags, narr = [], []
    if revenue <= 0:
        return 0, ["Cannot assess leverage — no revenue"], []
    ratio = debt / revenue
    if ratio > 2.0:
        score -= 18
        flags.append(f"Critically high debt-to-revenue ratio ({ratio:.2f}x)")
        narr.append(f"Debt is {ratio:.2f}x revenue — severely overleveraged.")
    elif ratio > 1.0:
        score -= 12
        flags.append(f"Debt exceeds annual revenue ({ratio:.2f}x)")
        narr.append(f"Total debt {ratio:.2f}x revenue — significant leverage concern.")
    elif ratio > 0.7:
        score -= 6
        flags.append(f"Elevated leverage ({ratio:.2f}x revenue)")
        narr.append(f"Debt-to-revenue {ratio:.2f}x is above the 0.7x conservative threshold.")
    elif ratio > 0.4:
        score -= 2
        narr.append(f"Moderate leverage ({ratio:.2f}x). Manageable.")
    else:
        narr.append(f"Conservative leverage ({ratio:.2f}x). Strong balance sheet.")
    return max(score, 0), flags, narr


def _score_external(ext_penalty: int, ext_flags: list, pdf_flags: list,
                    bank_data: dict | None, mca_data: dict | None):
    score = WEIGHTS["external"]
    flags = list(ext_flags or [])
    narr  = []

    score -= ext_penalty
    score -= len(pdf_flags) * 5
    flags.extend(pdf_flags)

    # Bank penalties
    if bank_data and not bank_data.get("error"):
        bp = bank_data.get("bank_score_penalty", 0)
        score -= bp
        flags.extend(bank_data.get("bank_flags", []))
        if bp > 0:
            narr.append(f"Bank statement flagged {len(bank_data.get('bank_flags',[]))} issue(s).")
        positives = bank_data.get("bank_positive", [])
        if positives:
            narr.append("Banking positives: " + "; ".join(positives) + ".")

    # MCA penalties
    if mca_data and not mca_data.get("error"):
        mp = mca_data.get("mca_penalty", 0)
        score -= mp
        flags.extend(mca_data.get("mca_flags", []))
        if mp > 0:
            narr.append(f"MCA status issue: {mca_data.get('status','Unknown')}.")

    if ext_penalty >= 20:
        narr.append("Critical adverse news — major reputational and legal risk.")
    elif ext_penalty >= 10:
        narr.append("Moderate adverse external signals detected.")
    elif ext_penalty > 0:
        narr.append("Minor adverse news signals noted.")
    else:
        narr.append("No significant adverse external intelligence.")

    return max(score, 0), flags, narr


def _score_qualitative(notes: str | None):
    score = WEIGHTS["qualitative"]
    flags, narr = [], []
    if not notes or not notes.strip():
        narr.append("No credit officer notes submitted.")
        return score, flags, narr
    nl = notes.lower()
    ded = 0
    for kw, pen, msg in OFFICER_RISK:
        if kw in nl:
            ded += pen
            flags.append(f"Officer note: {msg}")
            narr.append(f"Officer observation: {msg.lower()}.")
    for kw, bon in OFFICER_POSITIVE:
        if kw in nl:
            score = min(score + bon, WEIGHTS["qualitative"])
    return max(score - ded, 0), flags, narr


# ── Dynamic Five Cs ───────────────────────────────────────────────────────────

def _five_cs(revenue, profit, debt, ext_flags, pdf_flags, gst, notes, bank_data, mca_data):
    # Character
    char_issues = [f for f in (ext_flags + pdf_flags)
                   if any(w in f.lower() for w in
                          ["fraud","litigation","legal","regulatory","scam","nclt"])]
    character = (
        f"Adverse signals: {'; '.join(char_issues[:2])}. Management integrity requires verification."
        if char_issues else
        "No adverse character signals from external research or document review."
    )

    # Capacity
    if revenue > 0 and profit > 0:
        margin  = profit / revenue * 100
        dscr    = profit / (debt * 0.1) if debt > 0 else 99
        capacity = (
            f"Net margin {margin:.1f}%. Estimated DSCR proxy {min(dscr,9.9):.1f}x "
            f"({'adequate' if dscr>=1.2 else 'tight'} for debt servicing)."
        )
    elif profit <= 0:
        capacity = "Company is loss-making. Debt servicing capacity is constrained."
    else:
        capacity = "Revenue data unavailable — capacity assessment inconclusive."

    # Capital
    if revenue > 0:
        d2r    = debt / revenue
        label  = "Strong" if d2r < 0.4 else ("Moderate" if d2r < 0.7 else "Stressed")
        capital = f"Debt-to-revenue {d2r:.2f}x. {label} capital structure."
        if bank_data and not bank_data.get("error"):
            ratio = bank_data.get("inflow_outflow_ratio", 0)
            capital += f" Bank inflow/outflow ratio: {ratio:.2f}x."
    else:
        capital = "Capital structure assessment requires revenue data."

    # Collateral
    collateral = (
        "Collateral assessment requires independent valuation report. "
        "Asset details not fully extractable from submitted documents."
    )
    if mca_data and mca_data.get("paid_up_capital") and mca_data["paid_up_capital"] != "Not retrieved":
        collateral = (
            f"Paid-up capital: {mca_data['paid_up_capital']}. "
            "Collateral adequacy to be confirmed via independent valuation."
        )

    # Conditions
    gst_level  = gst.get("gst_risk_level", "N/A")
    mca_status = (mca_data or {}).get("status", "Not retrieved")
    conditions = (
        f"GST compliance: {gst_level}. "
        f"MCA company status: {mca_status}. "
        "Sector and macro conditions to be assessed by credit committee."
    )

    return {
        "character":  character,
        "capacity":   capacity,
        "capital":    capital,
        "collateral": collateral,
        "conditions": conditions,
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def calculate_risk(
    financials:       dict,
    external_penalty: int  = 0,
    external_flags:   list = None,
    officer_notes:    str  = None,
    bank_data:        dict = None,
    mca_data:         dict = None,
) -> dict:

    pdf_flags = financials.get("pdf_risk_flags", [])
    try:
        revenue = float(financials.get("revenue", 0) or 0)
        profit  = float(financials.get("profit",  0) or 0)
        debt    = float(financials.get("debt",    0) or 0)
    except (TypeError, ValueError):
        return {
            "risk_score": 40, "decision": "Insufficient Data",
            "interest_rate": "N/A", "loan_amount": "N/A",
            "risk_flags": ["Financial data incomplete"],
            "score_breakdown": {}, "gst_analysis": {}, "five_cs": {},
            "explanation": "Financial extraction failed.",
            "detailed_narrative": ["Could not parse financials from the document."],
        }

    gst = evaluate_gst_risk(revenue)

    fin_score,  fin_flags,  fin_narr  = _score_financial(revenue, profit)
    lev_score,  lev_flags,  lev_narr  = _score_leverage(revenue, debt)
    ext_score,  ext_flags,  ext_narr  = _score_external(
        external_penalty, external_flags or [], pdf_flags, bank_data, mca_data)
    gst_score  = max(WEIGHTS["gst"] - gst["gst_penalty"], 0)
    qual_score, qual_flags, qual_narr = _score_qualitative(officer_notes)

    if gst["gst_penalty"] > 0:
        ext_flags.append(f"GST Risk: {gst['gst_risk_level']}")

    all_flags = fin_flags + lev_flags + ext_flags + qual_flags
    all_narr  = fin_narr  + lev_narr  + ext_narr  + qual_narr

    base_score = round(min(fin_score + lev_score + ext_score + gst_score + qual_score, 100), 1)

    # Initial decision based on base score
    if base_score >= 80:
        decision, rate, mult = "Approve", "9.5% p.a.", 2.0
    elif base_score >= 70:
        decision, rate, mult = "Approve with Conditions", "11.5% p.a.", 1.2
    elif base_score >= 60:
        decision, rate, mult = "Approve with Strict Conditions", "13.5% p.a.", 0.6
    else:
        decision, rate, mult = "Reject", "N/A", 0.0

    if mult > 0 and revenue > 0:
        loan_cr = (revenue * mult) / 1e7
        loan    = f"₹{loan_cr:,.2f} Cr (indicative)"
    else:
        loan = "Not Applicable"

    five_cs = _five_cs(revenue, profit, debt, ext_flags, pdf_flags,
                       gst, officer_notes, bank_data, mca_data)

    explanation = (
        f"Base Underwriting Score: {base_score}/100. "
        f"Financial Health {fin_score}/40, "
        f"Leverage {lev_score}/20, "
        f"External {ext_score}/20, "
        f"GST {gst_score}/10, "
        f"Qualitative {qual_score}/10. "
        f"Recommendation: {decision}."
    )

    return {
        "base_score":    base_score,
        "final_score":   base_score,
        "risk_score":    base_score,
        "decision":      decision,
        "interest_rate": rate,
        "loan_amount":   loan,
        "risk_flags":    all_flags,
        "score_breakdown": {
            "financial_score":   fin_score,
            "leverage_score":    lev_score,
            "external_score":    ext_score,
            "gst_score":         gst_score,
            "qualitative_score": qual_score,
            "base_score":        base_score,
            "ml_adjustment":     0,
            "final_score":       base_score,
        },
        "gst_analysis":      gst,
        "five_cs":           five_cs,
        "explanation":       explanation,
        "detailed_narrative": all_narr,
        "sanction_covenants": [],
        "gated_reasons":     [],
    }


# ── ML-enhanced wrapper ────────────────────────────────────────────────────────

def calculate_risk_with_ml(
    financials:       dict,
    external_penalty: int  = 0,
    external_flags:   list = None,
    officer_notes:    str  = None,
    bank_data:        dict = None,
    mca_data:         dict = None,
) -> dict:
    """
    Calls calculate_risk then augments with ML model prediction.
    Applies institutional decision gates to guarantee that data-quality issues
    and unverified records enforce conditional approvals and covenants.
    """
    result = calculate_risk(
        financials, external_penalty, external_flags,
        officer_notes, bank_data, mca_data
    )

    base_score = result["base_score"]
    adj = 0
    ml = {}

    try:
        from services.ml_scoring_service import ml_credit_score
        ml = ml_credit_score(
            financials, result["gst_analysis"],
            {"external_penalty": external_penalty, "external_flags": external_flags or []},
            bank_data,
        )
        adj = ml.get("ml_score_adjustment", 0)
        final_score = round(min(max(base_score + adj, 0), 100), 1)
        result["final_score"] = final_score
        result["risk_score"] = final_score
        result["score_breakdown"]["ml_adjustment"] = adj
        result["score_breakdown"]["final_score"] = final_score
        result["ml_analysis"] = ml
    except Exception as e:
        final_score = base_score
        result["ml_analysis"] = {"error": f"ML model unavailable: {e}"}

    # 1. Base Score-to-Decision Mapping
    if final_score >= 80:
        decision, rate, mult = "Approve", "9.5% p.a.", 2.0
    elif final_score >= 70:
        decision, rate, mult = "Approve with Conditions", "11.5% p.a.", 1.2
    elif final_score >= 60:
        decision, rate, mult = "Approve with Strict Conditions", "13.5% p.a.", 0.6
    else:
        decision, rate, mult = "Reject", "N/A", 0.0

    # ─────────────────────────────────────────────────────────────
    # 2. INSTITUTIONAL DECISION GATES & SANITY CONTROLS (BUG 5 FIX)
    # ─────────────────────────────────────────────────────────────
    covenants = []
    gated_reasons = []

    # Gate A: Bank Statement Extraction Integrity
    bank_has_txns = bank_data and bank_data.get("has_txn_data", False)
    if bank_data and not bank_data.get("error"):
        if not bank_has_txns:
            gated_reasons.append("Bank statement contains zero extracted transactions (extraction incomplete)")
            covenants.append("Pre-sanction Covenant: Complete 12-month original bank statements must be audited manually prior to final facility sanction.")
            # Data-quality circuit breaker: cannot unconditionally approve with zero bank transactions
            if decision == "Approve":
                decision = "Approve with Conditions"
                rate = "11.5% p.a."
                mult = min(mult, 1.2)

    # Gate B: GST Filing Verification Gate
    gst_info = result.get("gst_analysis", {})
    if not gst_info.get("gst_verified", False):
        covenants.append("Pre-disbursement Covenant: Mandatory receipt and reconciliation of 12-month GSTR-3B filings required.")
        if decision == "Approve" and not bank_has_txns:
            decision = "Approve with Strict Conditions"
            rate = "13.5% p.a."
            mult = min(mult, 0.8)

    # Gate C: Verified Critical Adverse Media Gate
    has_critical_news = (external_penalty >= 20) or any(
        "[CRITICAL]" in str(f) or "fraud" in str(f).lower() or "nclt" in str(f).lower()
        for f in (external_flags or [])
    )
    if has_critical_news:
        decision = "Reject"
        rate = "N/A"
        mult = 0.0
        gated_reasons.append("Critical adverse media findings (NCLT / Fraud / Investigation)")

    # Recalculate loan amount based on gated multiplier
    revenue = float(financials.get("revenue", 0) or 0)
    if mult > 0 and revenue > 0:
        loan_cr = (revenue * mult) / 1e7
        loan = f"₹{loan_cr:,.2f} Cr (indicative)"
    else:
        loan = "Not Applicable"

    result["decision"] = decision
    result["interest_rate"] = rate
    result["loan_amount"] = loan
    result["sanction_covenants"] = covenants
    result["gated_reasons"] = gated_reasons

    # Clear, consistent explanation narrative
    cov_str = (" Active Sanction Covenants: " + "; ".join(covenants)) if covenants else ""
    ml_grade_str = ml.get("ml_grade", "Grade A (Standard)") if ml else "Grade A"
    ml_prob_str = f"{ml.get('ml_reject_probability', 0)*100:.1f}%" if ml else "N/A"

    result["explanation"] = (
        f"Base Underwriting Score: {base_score}/100. "
        f"XGBoost ML Risk Calibration ({ml_grade_str}, reject probability {ml_prob_str}): {adj:+d} pts. "
        f"Final Calibrated Credit Score: {final_score}/100. "
        f"Final Recommendation: {decision}."
        f"{cov_str}"
    )

    return result

