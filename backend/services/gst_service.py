def evaluate_gst_risk(revenue: float, gst_turnover: float | None = None) -> dict:
    """
    Evaluates GST compliance risk based on verified filings.

    If verified GSTR-3B / GSTR-1 data is NOT provided:
      - Does NOT fabricate a synthetic mismatch or penalize the borrower on estimations.
      - Explicitly marks GST as 'Pending Verification'.
      - Sets penalty to 0 pts (neutral) and adds a mandatory pre-disbursement verification condition.

    If verified GST turnover IS provided:
      - Calculates exact variance between audited P&L turnover and GSTR turnover.
      - Applies institutional risk penalties if material discrepancies exist.
    """
    try:
        revenue = float(revenue)
    except (TypeError, ValueError):
        return {
            "gst_verified": False,
            "gst_penalty": 0,
            "gst_mismatch_percent": 0.0,
            "gst_mismatch_display": "N/A",
            "gst_risk_level": "GST Data Unavailable",
            "gst_turnover_display": "N/A",
            "gst_note": "Could not parse revenue for GST analysis",
            "requires_covenant": True,
        }

    if revenue <= 0:
        return {
            "gst_verified": False,
            "gst_penalty": 0,
            "gst_mismatch_percent": 0.0,
            "gst_mismatch_display": "N/A",
            "gst_risk_level": "No Revenue Declared",
            "gst_turnover_display": "₹0",
            "gst_note": "Revenue is zero — GST reconciliation not applicable",
            "requires_covenant": False,
        }

    # Case A: GSTR filing NOT provided by borrower
    if gst_turnover is None:
        return {
            "gst_verified": False,
            "gst_penalty": 0,
            "gst_mismatch_percent": 0.0,
            "gst_mismatch_display": "N/A (Unverified)",
            "gst_risk_level": "Pending Verification (GSTR Not Uploaded)",
            "gst_turnover_display": "Pending GSTR-3B Submission",
            "gst_note": (
                "GST filings not provided with submission. Assessed neutrally without estimated penalties. "
                "Mandatory Covenant: 12-month GSTR-3B / GSTR-1 returns must be verified prior to loan disbursement."
            ),
            "requires_covenant": True,
        }

    # Case B: Verified GST turnover provided
    try:
        gst_turnover = float(gst_turnover)
    except (TypeError, ValueError):
        return {
            "gst_verified": False,
            "gst_penalty": 0,
            "gst_mismatch_percent": 0.0,
            "gst_mismatch_display": "N/A (Invalid Data)",
            "gst_risk_level": "Invalid GST Turnover",
            "gst_turnover_display": "Error",
            "gst_note": "Invalid GST turnover format provided.",
            "requires_covenant": True,
        }

    mismatch_pct = abs(revenue - gst_turnover) / revenue * 100

    if mismatch_pct > 25:
        penalty, risk_level = 10, "High GST Mismatch (>25%) — Potential Tax Non-Compliance"
    elif mismatch_pct > 15:
        penalty, risk_level = 7, "Significant GST Mismatch (15–25%)"
    elif mismatch_pct > 10:
        penalty, risk_level = 4, "Moderate GST Mismatch (10–15%)"
    elif mismatch_pct > 5:
        penalty, risk_level = 2, "Minor GST Variance (5–10%)"
    else:
        penalty, risk_level = 0, "GST Compliant (<5% variance)"

    gst_cr = gst_turnover / 1e7
    if gst_cr >= 1:
        gst_display = f"₹{gst_cr:,.2f} Cr"
    else:
        gst_display = f"₹{gst_turnover / 1e5:,.2f} L"

    return {
        "gst_verified": True,
        "gst_penalty": penalty,
        "gst_mismatch_percent": round(mismatch_pct, 2),
        "gst_mismatch_display": f"{mismatch_pct:.2f}%",
        "gst_risk_level": risk_level,
        "gst_turnover_display": gst_display,
        "gst_note": f"Verified against GSTR filings ({mismatch_pct:.2f}% variance to declared P&L turnover).",
        "requires_covenant": mismatch_pct > 10,
    }
