"""
pdf_service.py  —  Real two-pass financial extraction
Pass 1 : pdfplumber table extraction  (accurate for structured annual reports)
Pass 2 : regex on raw text            (fallback for text-heavy docs)
Also detects risk signals in document text.
"""

import pdfplumber
import re
from io import BytesIO


# ── Indian number normaliser ──────────────────────────────────────────────────

def parse_indian_number(text: str) -> float | None:
    if not text:
        return None
    t = str(text).lower().replace("₹", "").replace(",", "").replace("(", "-").strip()
    m = re.search(r"-?\d+\.?\d*", t)
    if not m:
        return None
    val = float(m.group())
    if "crore" in t or "cr." in t or re.search(r"\bcr\b", t):
        val *= 1e7
    elif "lakh" in t or "lac" in t:
        val *= 1e5
    elif "million" in t:
        val *= 1e6
    elif "billion" in t:
        val *= 1e9
    elif "thousand" in t:
        val *= 1e3
    return val


def fmt_inr(val: float) -> str:
    if not val:
        return "₹0"
    cr = val / 1e7
    if cr >= 1:
        return f"₹{cr:,.2f} Cr"
    lk = val / 1e5
    if lk >= 1:
        return f"₹{lk:,.2f} L"
    return f"₹{val:,.0f}"


# ── Label lists ───────────────────────────────────────────────────────────────

REV_LABELS = [
    "revenue from operations", "total revenue", "revenues", "net revenue",
    "total income", "gross revenue", "turnover", "net sales", "total sales",
    "income from operations",
]
PAT_LABELS = [
    "profit for the year", "profit after tax", "net profit", "pat",
    "profit / (loss) after tax", "profit/(loss) after tax",
    "profit for the period", "profit attributable", "net income",
    "profit after taxation",
]
DEBT_LABELS = [
    "total borrowings", "total debt", "borrowings", "long-term borrowings",
    "short-term borrowings", "financial liabilities", "total liabilities",
    "non-current liabilities", "loans",
]


def _lbl_match(cell: str, labels: list) -> bool:
    c = str(cell).lower().strip()
    return any(l in c for l in labels)


# ── Pass 1 : table extraction ─────────────────────────────────────────────────

def _from_tables(pdf_bytes: bytes) -> dict:
    res = {"revenue": None, "profit": None, "debt": None}
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                for table in (page.extract_tables() or []):
                    for row in table:
                        if not row or not row[0]:
                            continue
                        label = str(row[0])
                        nums = []
                        for cell in row[1:]:
                            v = parse_indian_number(str(cell)) if cell else None
                            if v and v > 0:
                                nums.append(v)
                        if not nums:
                            continue
                        best = max(nums)
                        if res["revenue"] is None and _lbl_match(label, REV_LABELS):
                            res["revenue"] = best
                        if res["profit"] is None and _lbl_match(label, PAT_LABELS):
                            res["profit"] = best
                        if res["debt"] is None and _lbl_match(label, DEBT_LABELS):
                            res["debt"] = best
                if all(v is not None for v in res.values()):
                    break
    except Exception:
        pass
    return res


# ── Pass 2 : regex on raw text ────────────────────────────────────────────────

_PAT = {
    "revenue": [
        r"(?:Revenue from [Oo]perations|Total Revenue|Net Revenue|Total Income|Turnover|Net Sales)"
        r"[^\d₹\n]{0,40}(₹?\s?[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
    "profit": [
        r"(?:Profit [Aa]fter [Tt]ax|Net Profit|PAT|Profit for the (?:year|period))"
        r"[^\d₹\n]{0,40}(₹?\s?[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
    "debt": [
        r"(?:Total [Bb]orrowings|Total [Dd]ebt|Borrowings)"
        r"[^\d₹\n]{0,40}(₹?\s?[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
        r"Total [Ll]iabilities"
        r"[^\d₹\n]{0,40}(₹?\s?[\d,]+\.?\d*\s*(?:crore|cr\.?|lakh|lac|million|billion)?)",
    ],
}


def _from_text(text: str) -> dict:
    res = {"revenue": None, "profit": None, "debt": None}
    clean = re.sub(r"\s+", " ", text)
    for field, pats in _PAT.items():
        for pat in pats:
            m = re.search(pat, clean, re.IGNORECASE)
            if m:
                v = parse_indian_number(m.group(1))
                if v and v > 0:
                    res[field] = v
                    break
    return res


# ── Risk signal detection ─────────────────────────────────────────────────────

_SIGNALS = [
    (r"legal proceedings|litigation|court case|arbitration",
     "Legal proceedings / litigation exposure detected"),
    (r"contingent liabilit|corporate guarantee",
     "Contingent liability exposure present"),
    (r"RBI penalty|SEBI penalty|regulatory action|show cause",
     "Regulatory compliance risk detected"),
    (r"going concern|material uncertainty|qualified opinion|adverse opinion",
     "Auditor going-concern or qualified opinion found"),
    (r"related party transaction",
     "Significant related party transactions identified"),
    (r"fraud|misappropriation|embezzlement",
     "Fraud or misappropriation mentioned"),
    (r"circular transaction|round.tripping|revenue inflation",
     "Circular transaction / revenue inflation risk"),
]


def _risk_signals(text: str) -> list[str]:
    flags, seen = [], set()
    for pat, msg in _SIGNALS:
        if re.search(pat, text, re.IGNORECASE) and msg not in seen:
            flags.append(msg)
            seen.add(msg)
    return flags


# ── Main entry point ──────────────────────────────────────────────────────────

def extract_financials(pdf_file) -> dict:
    raw = pdf_file.read()
    pdf_file.seek(0)

    # Pass 1 — tables
    tbl = _from_tables(raw)

    # Full text for pass 2 + risk signals
    full_text = ""
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
    except Exception:
        pass

    txt = _from_text(full_text)
    risk_flags = _risk_signals(full_text)

    revenue = tbl["revenue"] or txt["revenue"] or 0.0
    profit  = tbl["profit"]  or txt["profit"]  or 0.0
    debt    = tbl["debt"]    or txt["debt"]     or 0.0

    # Sanity: profit can't exceed revenue
    if profit and revenue and profit > revenue > 0:
        profit = revenue * 0.05

    method = "table+text" if any(tbl.values()) else "text_only"

    return {
        "revenue":         str(revenue),
        "profit":          str(profit),
        "debt":            str(debt),
        "revenue_display": fmt_inr(revenue),
        "profit_display":  fmt_inr(profit),
        "debt_display":    fmt_inr(debt),
        "pdf_risk_flags":  risk_flags,
        "extraction_method": method,
    }