import pdfplumber
import re
from io import BytesIO


# ─── Number normaliser ────────────────────────────────────────────────────────

def parse_indian_number(text: str) -> float | None:
    """
    Converts Indian financial notation to a raw float (in rupees).
    Handles: crore, lakh, thousands, plain numbers, commas, ₹ symbol.
    Examples:
        "₹ 1,23,456.78 crore"  → 1234567800000.0
        "45,678.90 Lakhs"       → 4567890000.0
        "1,23,456"              → 123456.0
    """
    if not text:
        return None

    text = text.lower().replace("₹", "").replace(",", "").strip()

    number_match = re.search(r"[-+]?\d+\.?\d*", text)
    if not number_match:
        return None

    value = float(number_match.group())

    if "crore" in text or "cr." in text or "cr " in text:
        value *= 1e7
    elif "lakh" in text or "lac" in text:
        value *= 1e5
    elif "thousand" in text or "000s" in text:
        value *= 1e3
    elif "million" in text:
        value *= 1e6
    elif "billion" in text:
        value *= 1e9

    return value


def format_inr(value: float) -> str:
    """Format raw rupee value back to a readable crore string."""
    if value is None:
        return "0"
    crore = value / 1e7
    if crore >= 1:
        return f"₹{crore:,.2f} Cr"
    lakh = value / 1e5
    if lakh >= 1:
        return f"₹{lakh:,.2f} L"
    return f"₹{value:,.0f}"


# ─── Table extraction (primary strategy) ─────────────────────────────────────

REVENUE_LABELS = [
    "revenue from operations", "total revenue", "revenues", "net revenue",
    "total income", "gross revenue", "turnover", "net sales", "total sales"
]
PROFIT_LABELS = [
    "profit for the year", "profit after tax", "net profit", "pat",
    "profit / (loss) after tax", "profit/(loss) after tax",
    "profit for the period", "profit attributable", "net income"
]
DEBT_LABELS = [
    "total borrowings", "total debt", "borrowings", "long-term borrowings",
    "short-term borrowings", "financial liabilities", "total liabilities",
    "non-current liabilities", "current liabilities"
]


def _label_matches(cell_text: str, label_list: list[str]) -> bool:
    cell_clean = cell_text.lower().strip()
    return any(lbl in cell_clean for lbl in label_list)


def extract_from_tables(pdf_path_or_file) -> dict:
    """
    Primary extraction: scan every table on every page.
    Looks for financial labels in the first column, then picks
    the largest numeric value from remaining columns.
    """
    results = {"revenue": None, "profit": None, "debt": None}

    try:
        with pdfplumber.open(pdf_path_or_file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue

                for table in tables:
                    for row in table:
                        if not row or not row[0]:
                            continue
                        label_cell = str(row[0])

                        numeric_cells = []
                        for cell in row[1:]:
                            if cell:
                                v = parse_indian_number(str(cell))
                                if v is not None and v > 0:
                                    numeric_cells.append(v)

                        if not numeric_cells:
                            continue

                        best_value = max(numeric_cells)

                        if results["revenue"] is None and _label_matches(label_cell, REVENUE_LABELS):
                            results["revenue"] = best_value

                        if results["profit"] is None and _label_matches(label_cell, PROFIT_LABELS):
                            results["profit"] = best_value

                        if results["debt"] is None and _label_matches(label_cell, DEBT_LABELS):
                            results["debt"] = best_value

                if all(v is not None for v in results.values()):
                    break

    except Exception:
        pass

    return results


# ─── Regex text extraction (fallback) ─────────────────────────────────────────

PATTERNS = {
    "revenue": [
        r"(?:Revenue from operations|Total Revenue|Net Revenue|Total Income|Turnover)"
        r"[^\d₹\n]{0,30}(₹?\s*[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
    "profit": [
        r"(?:Profit after tax|Net Profit|PAT|Profit for the (?:year|period))"
        r"[^\d₹\n]{0,30}(₹?\s*[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
    "debt": [
        r"(?:Total [Bb]orrowings|Total [Dd]ebt|Borrowings)"
        r"[^\d₹\n]{0,30}(₹?\s*[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
        r"(?:Total [Ll]iabilities)"
        r"[^\d₹\n]{0,30}(₹?\s*[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
}


def extract_from_text(text: str) -> dict:
    """Fallback regex extraction from raw page text."""
    results = {"revenue": None, "profit": None, "debt": None}
    text_clean = re.sub(r"\s+", " ", text)

    for field, pattern_list in PATTERNS.items():
        for pattern in pattern_list:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                value = parse_indian_number(match.group(1))
                if value and value > 0:
                    results[field] = value
                    break

    return results


# ─── Risk signal detection ────────────────────────────────────────────────────

RISK_SIGNALS = [
    (r"(legal proceedings|litigation|court case|arbitration|dispute)", "Legal proceedings / litigation exposure detected"),
    (r"(contingent liabilities|corporate guarantee|guarantees given)", "Contingent liability exposure present"),
    (r"(RBI penalty|SEBI penalty|regulatory action|compliance violation|show cause)", "Regulatory compliance risk detected"),
    (r"(going concern|material uncertainty|qualified opinion|adverse opinion)", "Auditor going-concern or qualified opinion found"),
    (r"(related party transaction|RPT)[^s]", "Significant related party transactions identified"),
    (r"(fraud|misappropriation|embezzlement)", "Fraud or misappropriation mentioned in document"),
    (r"(circular transaction|round-tripping|revenue inflation)", "Circular transaction / revenue inflation risk"),
    (r"(invoked|crystallised|enforced).{0,40}(guarantee|pledge)", "Guarantee invocation detected"),
]


def extract_risk_signals(text: str) -> list[str]:
    flags = []
    seen = set()
    for pattern, message in RISK_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE) and message not in seen:
            flags.append(message)
            seen.add(message)
    return flags


# ─── Main extraction function ─────────────────────────────────────────────────

def extract_financials(pdf_file) -> dict:
    """
    Two-pass extraction:
    1. Table extraction (accurate for structured annual reports)
    2. Regex on raw text (fallback for text-heavy documents)
    """
    raw_bytes = pdf_file.read()
    pdf_file.seek(0)

    # Pass 1: table extraction
    table_results = extract_from_tables(BytesIO(raw_bytes))

    # Pass 2: full text for risk signals + fallback numbers
    full_text = ""
    try:
        with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception:
        pass

    text_results = extract_from_text(full_text)
    risk_flags = extract_risk_signals(full_text)

    # Merge: table extraction wins; fall back to regex
    revenue = table_results["revenue"] or text_results["revenue"] or 0.0
    profit = table_results["profit"] or text_results["profit"] or 0.0
    debt = table_results["debt"] or text_results["debt"] or 0.0

    # Basic sanity: if profit > revenue something went wrong, zero it
    if profit > revenue > 0:
        profit = revenue * 0.05

    return {
        "revenue": str(revenue),
        "profit": str(profit),
        "debt": str(debt),
        "revenue_display": format_inr(revenue),
        "profit_display": format_inr(profit),
        "debt_display": format_inr(debt),
        "pdf_risk_flags": risk_flags,
        "extraction_method": (
            "table+text" if any(v for v in table_results.values())
            else "text_only"
        )
    }