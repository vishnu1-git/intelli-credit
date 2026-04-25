from services.gst_service import evaluate_gst_risk


# ─── Scoring weights ──────────────────────────────────────────────────────────
WEIGHTS = {
    "financial_health": 40,
    "leverage":         20,
    "external":         20,
    "gst":              10,
    "qualitative":      10,
}

OFFICER_RISK_WORDS = [
    ("fraud",              10, "Fraud mentioned in officer notes"),
    ("default",            10, "Default risk flagged by officer"),
    ("nclt",               10, "NCLT proceedings flagged"),
    ("bankruptcy",         10, "Bankruptcy risk noted"),
    ("money laundering",   10, "Money laundering concern raised"),
    ("litigation",          7, "Active litigation flagged"),
    ("regulatory",          7, "Regulatory issue flagged"),
    ("factory shutdown",    7, "Factory shutdown noted"),
    ("low capacity",        5, "Low capacity utilisation noted"),
    ("penalty",             5, "Penalty exposure noted"),
]

OFFICER_POSITIVE_WORDS = [
    ("strong management",  3),
    ("long relationship",  2),
    ("good repayment",     3),
    ("clean record",       3),
    ("blue chip",          2),
]


def _score_financial_health(revenue: float, profit: float) -> tuple[float, list, list]:
    score = WEIGHTS["financial_health"]
    flags, narrative = [], []

    if revenue <= 0:
        score -= 30
        flags.append("No revenue detected — zero turnover")
        narrative.append("Revenue extraction returned zero, indicating either a very early-stage company or extraction failure.")
    else:
        if profit <= 0:
            score -= 15
            flags.append("Negative profitability (loss-making)")
            narrative.append("Company is loss-making. Negative PAT signals inability to service debt from operations.")
        else:
            margin = (profit / revenue) * 100
            if margin < 2:
                score -= 5
                flags.append(f"Very thin profit margin ({margin:.1f}%)")
                narrative.append(f"Net profit margin of {margin:.1f}% is extremely thin — leaves no buffer for debt servicing.")
            elif margin < 5:
                score -= 2
                narrative.append(f"Profit margin of {margin:.1f}% is below healthy threshold of 5%.")
            else:
                narrative.append(f"Profit margin of {margin:.1f}% is acceptable.")

    return max(score, 0), flags, narrative


def _score_leverage(revenue: float, debt: float) -> tuple[float, list, list]:
    score = WEIGHTS["leverage"]
    flags, narrative = [], []

    if revenue <= 0:
        return 0, ["Cannot assess leverage — no revenue"], []

    ratio = debt / revenue

    if ratio > 2.0:
        score -= 18
        flags.append(f"Debt-to-revenue ratio critically high ({ratio:.2f}x)")
        narrative.append(f"Debt is {ratio:.2f}x revenue — extremely overleveraged. Indicates severe repayment stress.")
    elif ratio > 1.0:
        score -= 12
        flags.append(f"Debt exceeds revenue ({ratio:.2f}x)")
        narrative.append(f"Total debt ({ratio:.2f}x revenue) exceeds annual turnover — significant leverage concern.")
    elif ratio > 0.7:
        score -= 6
        flags.append(f"Elevated debt-to-revenue ratio ({ratio:.2f}x)")
        narrative.append(f"Debt-to-revenue ratio of {ratio:.2f}x is above the conservative 0.7x threshold.")
    elif ratio > 0.4:
        score -= 2
        narrative.append(f"Moderate leverage ({ratio:.2f}x revenue). Manageable but worth monitoring.")
    else:
        narrative.append(f"Conservative leverage ({ratio:.2f}x revenue). Strong balance sheet position.")

    return max(score, 0), flags, narrative


def _score_external(external_penalty: int, external_flags: list, pdf_flags: list) -> tuple[float, list, list]:
    score = WEIGHTS["external"]
    flags, narrative = list(external_flags or []), []

    score -= external_penalty
    pdf_penalty = len(pdf_flags) * 5
    score -= pdf_penalty

    if pdf_flags:
        flags.extend(pdf_flags)
        narrative.append(f"{len(pdf_flags)} risk signal(s) detected in submitted PDF documents.")

    if external_penalty >= 20:
        narrative.append("Critical adverse news detected — major reputational and legal risk.")
    elif external_penalty >= 10:
        narrative.append("Moderate adverse external signals. Requires further diligence.")
    elif external_penalty > 0:
        narrative.append("Minor adverse news signals noted in external research.")
    else:
        narrative.append("No significant adverse external intelligence detected.")

    return max(score, 0), flags, narrative


def _score_qualitative(officer_notes: str | None) -> tuple[float, list, list]:
    score = WEIGHTS["qualitative"]
    flags, narrative = [], []

    if not officer_notes or not officer_notes.strip():
        narrative.append("No credit officer notes submitted.")
        return score, flags, narrative

    notes_lower = officer_notes.lower()
    deductions = 0

    for keyword, penalty, flag_msg in OFFICER_RISK_WORDS:
        if keyword in notes_lower:
            deductions += penalty
            flags.append(f"Officer Note: {flag_msg}")
            narrative.append(f"Officer observation indicates {flag_msg.lower()}.")

    for keyword, bonus in OFFICER_POSITIVE_WORDS:
        if keyword in notes_lower:
            score = min(score + bonus, WEIGHTS["qualitative"])

    score = max(score - deductions, 0)
    return score, flags, narrative


def _build_five_cs(
    revenue: float, profit: float, debt: float,
    external_flags: list, pdf_flags: list,
    gst_analysis: dict, officer_notes: str | None
) -> dict:
    """Generate dynamic Five Cs evaluation."""

    # Character
    char_issues = [f for f in (external_flags + pdf_flags)
                   if any(w in f.lower() for w in ["fraud", "litigation", "legal", "regulatory", "scam"])]
    if char_issues:
        character = f"Adverse signals noted: {'; '.join(char_issues[:2])}. Management integrity requires further verification."
    else:
        character = "No adverse character signals detected from external research or document review."

    # Capacity
    if revenue > 0 and profit > 0:
        margin = (profit / revenue) * 100
        dscr_proxy = profit / (debt * 0.1) if debt > 0 else 99
        capacity = (
            f"Net profit margin of {margin:.1f}%. Estimated DSCR proxy of {min(dscr_proxy, 9.9):.1f}x "
            f"({'adequate' if dscr_proxy >= 1.2 else 'tight'} for debt servicing)."
        )
    elif profit <= 0:
        capacity = "Company is currently loss-making. Capacity to service debt is constrained."
    else:
        capacity = "Revenue data unavailable — capacity assessment inconclusive."

    # Capital
    if revenue > 0:
        d2r = debt / revenue
        capital = (
            f"Debt-to-revenue ratio of {d2r:.2f}x. "
            f"{'Strong' if d2r < 0.4 else 'Moderate' if d2r < 0.7 else 'Stressed'} capital structure."
        )
    else:
        capital = "Capital structure assessment requires revenue data."

    # Collateral
    collateral = (
        "Collateral assessment requires independent valuation report. "
        "Asset details not extractable from submitted documents in this version."
    )

    # Conditions
    gst_level = gst_analysis.get("gst_risk_level", "N/A")
    conditions = (
        f"GST compliance status: {gst_level}. "
        "Sector and macroeconomic conditions should be assessed by the credit committee separately."
    )

    return {
        "character": character,
        "capacity": capacity,
        "capital": capital,
        "collateral": collateral,
        "conditions": conditions,
    }


def calculate_risk(
    financials: dict,
    external_penalty: int = 0,
    external_flags: list | None = None,
    officer_notes: str | None = None
) -> dict:

    pdf_flags = financials.get("pdf_risk_flags", [])

    try:
        revenue = float(financials["revenue"])
        profit = float(financials["profit"])
        debt = float(financials["debt"])
    except (KeyError, ValueError, TypeError):
        return {
            "risk_score": 40,
            "decision": "Insufficient Data",
            "interest_rate": "N/A",
            "loan_amount": "N/A",
            "risk_flags": ["Financial data incomplete or unextractable"],
            "score_breakdown": {},
            "gst_analysis": {},
            "five_cs": {},
            "explanation": "Financial extraction failed. Please verify the uploaded document format.",
            "detailed_narrative": ["Could not parse revenue, profit, or debt from the submitted file."]
        }

    # Score each component
    fin_score,  fin_flags,  fin_narrative  = _score_financial_health(revenue, profit)
    lev_score,  lev_flags,  lev_narrative  = _score_leverage(revenue, debt)
    ext_score,  ext_flags,  ext_narrative  = _score_external(external_penalty, external_flags, pdf_flags)
    gst_analysis                           = evaluate_gst_risk(revenue)
    gst_score = max(WEIGHTS["gst"] - gst_analysis["gst_penalty"], 0)
    qual_score, qual_flags, qual_narrative = _score_qualitative(officer_notes)

    if gst_analysis["gst_penalty"] > 0:
        ext_flags.append(f"GST Risk: {gst_analysis['gst_risk_level']}")

    all_flags = fin_flags + lev_flags + ext_flags + qual_flags
    all_narrative = fin_narrative + lev_narrative + ext_narrative + qual_narrative

    total_score = min(fin_score + lev_score + ext_score + gst_score + qual_score, 100)
    total_score = round(total_score, 2)

    # Decision logic
    if total_score >= 80:
        decision = "Approve"
        interest_rate = "9.5% p.a."
        loan_multiplier = 2.0      # 2x annual revenue cap
    elif total_score >= 70:
        decision = "Approve with Conditions"
        interest_rate = "11.5% p.a."
        loan_multiplier = 1.2
    elif total_score >= 60:
        decision = "Approve with Strict Conditions"
        interest_rate = "13.5% p.a."
        loan_multiplier = 0.6
    else:
        decision = "Reject"
        interest_rate = "N/A"
        loan_multiplier = 0

    if loan_multiplier > 0 and revenue > 0:
        raw_loan = revenue * loan_multiplier
        loan_cr = raw_loan / 1e7
        loan_amount = f"₹{loan_cr:,.2f} Cr (indicative)"
    else:
        loan_amount = "Not Applicable"

    five_cs = _build_five_cs(
        revenue, profit, debt, ext_flags, pdf_flags, gst_analysis, officer_notes
    )

    explanation = (
        f"Composite credit score: {total_score}/100. "
        f"Financial Health: {fin_score}/{WEIGHTS['financial_health']}, "
        f"Leverage: {lev_score}/{WEIGHTS['leverage']}, "
        f"External Intelligence: {ext_score}/{WEIGHTS['external']}, "
        f"GST Compliance: {gst_score}/{WEIGHTS['gst']}, "
        f"Qualitative: {qual_score}/{WEIGHTS['qualitative']}. "
        f"Recommendation: {decision}."
    )

    return {
        "risk_score": total_score,
        "decision": decision,
        "interest_rate": interest_rate,
        "loan_amount": loan_amount,
        "risk_flags": all_flags,
        "score_breakdown": {
            "financial_score": fin_score,
            "leverage_score": lev_score,
            "external_score": ext_score,
            "gst_score": gst_score,
            "qualitative_score": qual_score,
        },
        "gst_analysis": gst_analysis,
        "five_cs": five_cs,
        "explanation": explanation,
        "detailed_narrative": all_narrative,
    }