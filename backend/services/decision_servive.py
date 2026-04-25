
def loan_recommendation(revenue, profit, debt, risk_score):

    # Risk Grade
    if risk_score <= 30:
        risk_grade = "Low"
        exposure_factor = 0.30
        interest_rate = 9.5

    elif risk_score <= 60:
        risk_grade = "Moderate"
        exposure_factor = 0.20
        interest_rate = 11

    elif risk_score <= 80:
        risk_grade = "High"
        exposure_factor = 0.10
        interest_rate = 13

    else:
        risk_grade = "Critical"
        exposure_factor = 0
        interest_rate = None

    # Loan Amount Calculation
    loan_amount = revenue * exposure_factor

    # Decision
    if risk_grade == "Critical":
        decision = "Reject"
    else:
        decision = "Approve"

    return {
        "risk_grade": risk_grade,
        "loan_amount": loan_amount,
        "interest_rate": interest_rate,
        "decision": decision
    }