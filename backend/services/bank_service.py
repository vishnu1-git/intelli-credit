"""
bank_service.py
Extracts key banking metrics from uploaded bank statement PDFs.
Supports: SBI, HDFC, ICICI, Axis, Kotak, PNB, BOB statement formats.
Two-pass: table extraction first, regex fallback.
"""

import pdfplumber
import re
from io import BytesIO


# ─── Regex patterns for common Indian bank statement formats ─────────────────

BALANCE_PATTERNS = [
    r"(?:closing balance|balance c/f|balance carried forward|end balance)"
    r"[^\d\n]{0,30}([\d,]+\.?\d{0,2})",
    r"(?:available balance|current balance|ledger balance)"
    r"[^\d\n]{0,30}([\d,]+\.?\d{0,2})",
]

OPENING_BALANCE_PATTERNS = [
    r"(?:opening balance|balance b/f|balance brought forward|opening bal)"
    r"[^\d\n]{0,30}([\d,]+\.?\d{0,2})",
]

# Debit/credit transaction patterns
DEBIT_PATTERNS  = [r"(?:total debit|total withdrawal|total dr)[^\d\n]{0,30}([\d,]+\.?\d{0,2})"]
CREDIT_PATTERNS = [r"(?:total credit|total deposit|total cr)[^\d\n]{0,30}([\d,]+\.?\d{0,2})"]

# OD / limit patterns
OD_LIMIT_PATTERNS = [
    r"(?:od limit|overdraft limit|sanctioned limit|drawing power)"
    r"[^\d\n]{0,30}([\d,]+\.?\d{0,2})",
]

# Bounce / return patterns
BOUNCE_PATTERNS = [
    r"(cheque return|ECS return|NACH return|mandate return|inward return|outward return)",
]

# EMI / loan deduction pattern
EMI_PATTERNS = [
    r"(EMI|loan repayment|loan installment|equated monthly)",
]


def _parse_amount(text: str) -> float:
    """Convert Indian number string to float."""
    if not text:
        return 0.0
    cleaned = text.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_with_patterns(text: str, patterns: list) -> float:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _parse_amount(match.group(1))
    return 0.0


def _count_occurrences(text: str, patterns: list) -> int:
    count = 0
    for pattern in patterns:
        count += len(re.findall(pattern, text, re.IGNORECASE))
    return count


# ─── Table-based transaction extraction ──────────────────────────────────────

def _extract_transactions_from_tables(pdf_bytes: bytes) -> dict:
    """
    Scan tables for debit/credit columns.
    Returns dict with totals and monthly breakdown.
    """
    monthly = {}
    total_credits = 0.0
    total_debits  = 0.0
    transaction_count = 0
    large_credits = []   # credits > 10 lakh (suspicious if sudden)
    large_debits  = []

    MONTH_MAP = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in (tables or []):
                    if not table or len(table) < 2:
                        continue

                    # Detect header row
                    header = [str(c).lower().strip() if c else "" for c in table[0]]

                    # Find debit/credit/balance/date column indices
                    date_col   = next((i for i, h in enumerate(header) if "date" in h), None)
                    debit_col  = next((i for i, h in enumerate(header)
                                       if any(w in h for w in ["debit", "withdrawal", "dr"])), None)
                    credit_col = next((i for i, h in enumerate(header)
                                       if any(w in h for w in ["credit", "deposit", "cr"])), None)

                    if debit_col is None and credit_col is None:
                        continue

                    for row in table[1:]:
                        if not row:
                            continue

                        # Date extraction for monthly bucketing
                        month_key = None
                        if date_col is not None and date_col < len(row) and row[date_col]:
                            date_str = str(row[date_col]).lower()
                            for mon, num in MONTH_MAP.items():
                                if mon in date_str:
                                    month_key = num
                                    break
                            if not month_key:
                                # Try numeric date like 01/04/2024
                                dm = re.search(r"\d{1,2}[/-](\d{1,2})[/-]\d{2,4}", date_str)
                                if dm:
                                    month_key = int(dm.group(1))

                        # Debit
                        if debit_col is not None and debit_col < len(row):
                            val = _parse_amount(str(row[debit_col] or ""))
                            if val > 0:
                                total_debits += val
                                transaction_count += 1
                                if month_key:
                                    monthly.setdefault(month_key, {"credits": 0.0, "debits": 0.0})
                                    monthly[month_key]["debits"] += val
                                if val >= 1_000_000:
                                    large_debits.append(val)

                        # Credit
                        if credit_col is not None and credit_col < len(row):
                            val = _parse_amount(str(row[credit_col] or ""))
                            if val > 0:
                                total_credits += val
                                transaction_count += 1
                                if month_key:
                                    monthly.setdefault(month_key, {"credits": 0.0, "debits": 0.0})
                                    monthly[month_key]["credits"] += val
                                if val >= 1_000_000:
                                    large_credits.append(val)

    except Exception:
        pass

    return {
        "total_credits":   total_credits,
        "total_debits":    total_debits,
        "transaction_count": transaction_count,
        "monthly":         monthly,
        "large_credits":   large_credits,
        "large_debits":    large_debits,
    }


# ─── Main analysis function ───────────────────────────────────────────────────

def analyze_bank_statement(bank_file) -> dict:
    """
    Full bank statement analysis.
    Returns structured metrics used by risk_service for scoring.
    """
    try:
        raw_bytes = bank_file.read()
        bank_file.seek(0)
    except Exception:
        return _empty_result("Could not read bank statement file")

    # Extract full text for regex pass
    full_text = ""
    try:
        with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception as e:
        return _empty_result(f"PDF parse error: {e}")

    if not full_text.strip():
        return _empty_result("Bank statement appears to be scanned/image-based. Text extraction failed.")

    # Regex extraction
    closing_balance  = _extract_with_patterns(full_text, BALANCE_PATTERNS)
    opening_balance  = _extract_with_patterns(full_text, OPENING_BALANCE_PATTERNS)
    regex_credits    = _extract_with_patterns(full_text, CREDIT_PATTERNS)
    regex_debits     = _extract_with_patterns(full_text, DEBIT_PATTERNS)
    od_limit         = _extract_with_patterns(full_text, OD_LIMIT_PATTERNS)
    bounce_count     = _count_occurrences(full_text, BOUNCE_PATTERNS)
    emi_count        = _count_occurrences(full_text, EMI_PATTERNS)

    # Table-based extraction (more accurate)
    table_data = _extract_transactions_from_tables(raw_bytes)

    # Merge: prefer table data if available
    total_credits = table_data["total_credits"] or regex_credits
    total_debits  = table_data["total_debits"]  or regex_debits
    monthly       = table_data["monthly"]
    txn_count     = table_data["transaction_count"]
    large_credits = table_data["large_credits"]
    large_debits  = table_data["large_debits"]

    # Average monthly balance from monthly breakdown
    if monthly:
        monthly_avg_balances = []
        running = opening_balance or closing_balance
        for m in sorted(monthly.keys()):
            running += monthly[m]["credits"] - monthly[m]["debits"]
            monthly_avg_balances.append(max(running, 0))
        avg_monthly_balance = sum(monthly_avg_balances) / len(monthly_avg_balances)
    else:
        avg_monthly_balance = (opening_balance + closing_balance) / 2 if opening_balance else closing_balance

    # Inflow-outflow ratio
    if total_debits > 0:
        inflow_outflow_ratio = round(total_credits / total_debits, 2)
    else:
        inflow_outflow_ratio = 99.0

    # Utilisation vs OD limit
    od_utilisation_pct = 0.0
    if od_limit > 0 and closing_balance < 0:
        od_utilisation_pct = round(abs(closing_balance) / od_limit * 100, 1)

    # Flags
    flags = []
    bank_score_penalty = 0

    if bounce_count >= 3:
        flags.append(f"High bounce/return count ({bounce_count} occurrences) — poor payment discipline")
        bank_score_penalty += 15
    elif bounce_count >= 1:
        flags.append(f"Cheque/ECS returns detected ({bounce_count} occurrences)")
        bank_score_penalty += 7

    if inflow_outflow_ratio < 0.8:
        flags.append(f"Outflows exceed inflows (ratio {inflow_outflow_ratio}x) — cash drain")
        bank_score_penalty += 10
    elif inflow_outflow_ratio < 1.0:
        flags.append(f"Near-breakeven cashflow (ratio {inflow_outflow_ratio}x)")
        bank_score_penalty += 5

    if closing_balance < 0:
        flags.append(f"Negative closing balance — overdraft position")
        bank_score_penalty += 12

    if od_utilisation_pct > 90:
        flags.append(f"OD limit nearly exhausted ({od_utilisation_pct}% utilised)")
        bank_score_penalty += 10
    elif od_utilisation_pct > 70:
        flags.append(f"High OD utilisation ({od_utilisation_pct}%)")
        bank_score_penalty += 5

    if len(large_credits) >= 3:
        flags.append(f"{len(large_credits)} unusually large credit entries (>₹10L) — verify source")
        bank_score_penalty += 5

    # Positive signals
    positive = []
    if inflow_outflow_ratio >= 1.3:
        positive.append(f"Healthy cashflow surplus (ratio {inflow_outflow_ratio}x)")
    if avg_monthly_balance > 500_000:
        positive.append(f"Strong average monthly balance (₹{avg_monthly_balance/1e5:.1f}L)")
    if bounce_count == 0:
        positive.append("No cheque/ECS returns — clean payment record")
    if emi_count > 0:
        positive.append(f"Existing loan repayments active ({emi_count} EMI entries)")

    # Display helpers
    def fmt(val):
        if val >= 1e7:
            return f"₹{val/1e7:.2f} Cr"
        if val >= 1e5:
            return f"₹{val/1e5:.2f} L"
        return f"₹{val:,.0f}"

    return {
        "opening_balance":       opening_balance,
        "closing_balance":       closing_balance,
        "avg_monthly_balance":   avg_monthly_balance,
        "total_credits":         total_credits,
        "total_debits":          total_debits,
        "inflow_outflow_ratio":  inflow_outflow_ratio,
        "od_limit":              od_limit,
        "od_utilisation_pct":    od_utilisation_pct,
        "bounce_count":          bounce_count,
        "emi_count":             emi_count,
        "transaction_count":     txn_count,
        "monthly_breakdown":     monthly,
        "bank_flags":            flags,
        "bank_positive":         positive,
        "bank_score_penalty":    min(bank_score_penalty, 30),
        "large_credit_count":    len(large_credits),
        "large_debit_count":     len(large_debits),
        # Display strings
        "opening_balance_display":     fmt(opening_balance),
        "closing_balance_display":     fmt(closing_balance),
        "avg_monthly_balance_display": fmt(avg_monthly_balance),
        "total_credits_display":       fmt(total_credits),
        "total_debits_display":        fmt(total_debits),
        "od_limit_display":            fmt(od_limit) if od_limit else "N/A",
        "extraction_note": "Table extraction" if table_data["transaction_count"] > 0 else "Text regex fallback",
        "error": None,
    }


def _empty_result(reason: str) -> dict:
    return {
        "opening_balance": 0, "closing_balance": 0, "avg_monthly_balance": 0,
        "total_credits": 0, "total_debits": 0, "inflow_outflow_ratio": 0,
        "od_limit": 0, "od_utilisation_pct": 0, "bounce_count": 0,
        "emi_count": 0, "transaction_count": 0, "monthly_breakdown": {},
        "bank_flags": [], "bank_positive": [], "bank_score_penalty": 0,
        "large_credit_count": 0, "large_debit_count": 0,
        "opening_balance_display": "N/A", "closing_balance_display": "N/A",
        "avg_monthly_balance_display": "N/A", "total_credits_display": "N/A",
        "total_debits_display": "N/A", "od_limit_display": "N/A",
        "extraction_note": "Failed", "error": reason,
    }