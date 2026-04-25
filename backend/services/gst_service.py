def evaluate_gst_risk(revenue: float, gst_turnover: float | None = None) -> dict:
    """
    Evaluates GST compliance risk.

    In a real deployment this would ingest GSTR-3B / GSTR-1 data.
    For now we simulate a realistic mismatch distribution:
      - Companies with very high revenue (>500 Cr) tend to have closer GST alignment
      - Mid-size companies show moderate variance
      - Small companies show higher variance
    """
    try:
        revenue = float(revenue)
    except (TypeError, ValueError):
        return {
            "gst_penalty": 0,
            "gst_mismatch_percent": 0.0,
            "gst_risk_level": "GST Data Unavailable",
            "gst_turnover_display": "N/A",
            "gst_note": "Could not parse revenue for GST analysis"
        }

    if revenue <= 0:
        return {
            "gst_penalty": 5,
            "gst_mismatch_percent": 0.0,
            "gst_risk_level": "No Revenue Declared",
            "gst_turnover_display": "₹0",
            "gst_note": "Revenue is zero — GST analysis not possible"
        }

    # Simulate realistic GST mismatch based on company size
    revenue_cr = revenue / 1e7

    if revenue_cr >= 10000:        # Large-cap (>10,000 Cr)
        simulated_ratio = 0.975    # 2.5% mismatch
    elif revenue_cr >= 1000:       # Mid-large (1,000–10,000 Cr)
        simulated_ratio = 0.962    # 3.8% mismatch
    elif revenue_cr >= 100:        # Mid-cap (100–1,000 Cr)
        simulated_ratio = 0.94     # 6% mismatch
    elif revenue_cr >= 10:         # Small-mid (10–100 Cr)
        simulated_ratio = 0.91     # 9% mismatch
    else:                          # Micro/small (<10 Cr)
        simulated_ratio = 0.87     # 13% mismatch

    if gst_turnover is None:
        gst_turnover = revenue * simulated_ratio

    try:
        gst_turnover = float(gst_turnover)
    except (TypeError, ValueError):
        gst_turnover = revenue * simulated_ratio

    mismatch_pct = abs(revenue - gst_turnover) / revenue * 100

    if mismatch_pct > 25:
        penalty, risk_level = 20, "High GST Mismatch — Possible Evasion"
    elif mismatch_pct > 15:
        penalty, risk_level = 15, "Significant GST Mismatch"
    elif mismatch_pct > 10:
        penalty, risk_level = 10, "Moderate GST Mismatch"
    elif mismatch_pct > 5:
        penalty, risk_level = 5, "Minor GST Variance"
    else:
        penalty, risk_level = 0, "GST Compliant"

    # Display formatting
    gst_cr = gst_turnover / 1e7
    if gst_cr >= 1:
        gst_display = f"₹{gst_cr:,.2f} Cr"
    else:
        gst_display = f"₹{gst_turnover / 1e5:,.2f} L"

    return {
        "gst_penalty": penalty,
        "gst_mismatch_percent": round(mismatch_pct, 2),
        "gst_risk_level": risk_level,
        "gst_turnover_display": gst_display,
        "gst_note": (
            "GST turnover estimated from declared revenue. "
            "Upload GSTR-3B for exact analysis."
        )
    }