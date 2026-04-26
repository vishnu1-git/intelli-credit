from services.gst_service import evaluate_gst_risk

def calculate_risk(
    financial_data,
    external_penalty,
    external_flags,
    officer_notes=None,
    bank_data=None,
    mca_data=None
):
    financials = financial_data

    revenue = float(financials.get("revenue", 0))
    profit = float(financials.get("profit", 0))
    debt = float(financials.get("debt", 0))

    gst = evaluate_gst_risk(revenue)

    score = 70
    if profit <= 0:
        score -= 20
    if debt > revenue:
        score -= 10
    score -= external_penalty

    if score >= 70:
        decision = "Approve"
        rate = "10%"
    elif score >= 50:
        decision = "Conditional"
        rate = "12%"
    else:
        decision = "Reject"
        rate = "N/A"

    return {
        "risk_score": score,
        "decision": decision,
        "interest_rate": rate,
        "loan_amount": "₹1 Cr",
        "risk_flags": external_flags,
        "score_breakdown": {
            "financial_score": score
        },
        "gst_analysis": gst,
        "five_cs": {},
        "explanation": f"Score {score}/100",
        "detailed_narrative": []
    }