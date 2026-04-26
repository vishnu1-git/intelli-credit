from services.gst_service import evaluate_gst_risk

# ─── Weights ─────────────────────────────────────────
WEIGHTS = {
    "financial_health": 40,
    "leverage": 20,
    "external": 20,
    "gst": 10,
    "qualitative": 10,
}

# ─── Financial scoring ───────────────────────────────
def _score_financial_health(revenue, profit):
    score = WEIGHTS["financial_health"]
    flags = []
    narrative = []

    if revenue <= 0:
        score -= 30
        flags.append("No revenue detected")
    elif profit <= 0:
        score -= 15
        flags.append("Loss making")
    else:
        margin = (profit / revenue) * 100
        if margin < 5:
            score -= 5
            flags.append("Low profit margin")

    return max(score, 0), flags, narrative


def _score_leverage(revenue, debt):
    score = WEIGHTS["leverage"]
    flags = []
    narrative = []

    if revenue <= 0:
        return 0, ["No revenue for leverage"], []

    ratio = debt / revenue

    if ratio > 2:
        score -= 18
        flags.append("High leverage")
    elif ratio > 1:
        score -= 10

    return max(score, 0), flags, narrative


def _score_external(external_penalty, external_flags, pdf_flags):
    score = WEIGHTS["external"]
    flags = list(external_flags or [])

    score -= external_penalty
    score -= len(pdf_flags) * 5

    return max(score, 0), flags, []


def _score_qualitative(notes):
    score = WEIGHTS["qualitative"]
    flags = []

    if notes:
        notes = notes.lower()
        if "fraud" in notes:
            score -= 10
            flags.append("Fraud risk")
        if "default" in notes:
            score -= 10
            flags.append("Default risk")

    return max(score, 0), flags, []


# ─── MAIN FUNCTION (FIXED) ───────────────────────────

def calculate_risk(
    financial_data,
    external_penalty,
    external_flags,
    officer_notes=None,
    bank_data=None,
    mca_data=None
):

    # ✅ FIXED: correct variable usage
    financials = financial_data

    pdf_flags = financials.get("pdf_risk_flags", [])

    try:
        revenue = float(financials.get("revenue", 0))
        profit = float(financials.get("profit", 0))
        debt = float(financials.get("debt", 0))
    except:
        return {
            "risk_score": 40,
            "decision": "Insufficient Data",
            "interest_rate": "N/A",
            "loan_amount": "N/A",
            "risk_flags": ["Invalid financial data"],
            "score_breakdown": {},
            "gst_analysis": {},
            "five_cs": {},
            "explanation": "Financial parsing failed",
            "detailed_narrative": []
        }

    # ─── scoring ─────────────────────────
    fin_score, fin_flags, _ = _score_financial_health(revenue, profit)
    lev_score, lev_flags, _ = _score_leverage(revenue, debt)
    ext_score, ext_flags, _ = _score_external(external_penalty, external_flags, pdf_flags)
    gst_analysis = evaluate_gst_risk(revenue)
    gst_score = max(WEIGHTS["gst"] - gst_analysis["gst_penalty"], 0)
    qual_score, qual_flags, _ = _score_qualitative(officer_notes)

    total_score = min(
        fin_score + lev_score + ext_score + gst_score + qual_score,
        100
    )

    # ─── decision ───────────────────────
    if total_score >= 80:
        decision = "Approve"
        rate = "9.5%"
        multiplier = 2
    elif total_score >= 60:
        decision = "Approve with Conditions"
        rate = "12%"
        multiplier = 1
    else:
        decision = "Reject"
        rate = "N/A"
        multiplier = 0

    loan_amount = f"₹{(revenue * multiplier)/1e7:.2f} Cr" if multiplier else "N/A"

    return {
        "risk_score": total_score,
        "decision": decision,
        "interest_rate": rate,
        "loan_amount": loan_amount,
        "risk_flags": fin_flags + lev_flags + ext_flags + qual_flags,
        "score_breakdown": {
            "financial_score": fin_score,
            "leverage_score": lev_score,
            "external_score": ext_score,
            "gst_score": gst_score,
            "qualitative_score": qual_score,
        },
        "gst_analysis": gst_analysis,
        "five_cs": {},
        "explanation": f"Score: {total_score}/100",
        "detailed_narrative": []
    }from services.gst_service import evaluate_gst_risk

WEIGHTS = {
    "financial_health": 40,
    "leverage": 20,
    "external": 20,
    "gst": 10,
    "qualitative": 10,
}

def calculate_risk(
    financial_data,
    external_penalty,
    external_flags,
    officer_notes=None,
    bank_data=None,
    mca_data=None
):

    # ✅ FIX: correct variable
    financials = financial_data

    # SAFE extraction
    revenue = float(financials.get("revenue", 0))
    profit = float(financials.get("profit", 0))
    debt = float(financials.get("debt", 0))

    pdf_flags = financials.get("pdf_risk_flags", [])

    # simple scoring
    fin_score = WEIGHTS["financial_health"] if profit > 0 else 20
    lev_score = WEIGHTS["leverage"] if debt < revenue else 10
    ext_score = WEIGHTS["external"] - external_penalty
    gst = evaluate_gst_risk(revenue)
    gst_score = WEIGHTS["gst"] - gst["gst_penalty"]
    qual_score = WEIGHTS["qualitative"]

    total = max(min(fin_score + lev_score + ext_score + gst_score + qual_score, 100), 0)

    if total >= 70:
        decision = "Approve"
        rate = "10%"
    elif total >= 50:
        decision = "Conditional"
        rate = "12%"
    else:
        decision = "Reject"
        rate = "N/A"

    return {
        "risk_score": total,
        "decision": decision,
        "interest_rate": rate,
        "loan_amount": "₹1 Cr",
        "risk_flags": pdf_flags + external_flags,
        "score_breakdown": {
            "financial_score": fin_score,
            "leverage_score": lev_score,
            "external_score": ext_score,
            "gst_score": gst_score,
            "qualitative_score": qual_score,
        },
        "gst_analysis": gst,
        "five_cs": {},
        "explanation": f"Score {total}/100",
        "detailed_narrative": []
    }