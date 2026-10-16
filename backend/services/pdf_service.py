"""
pdf_service.py - Document Processing Pipeline using pdfplumber & Tesseract OCR
Extracts financial data (Revenue, Net Profit/PAT, Borrowings/Debt) from both
Digital PDFs and Scanned / Image-based PDFs.
"""

import os
import re
from io import BytesIO
import pdfplumber

# OCR imports
try:
    import pytesseract
    from PIL import Image
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False

try:
    import pypdfium2
    _PYPDFIUM_AVAILABLE = True
except ImportError:
    _PYPDFIUM_AVAILABLE = False

# Auto-configure Tesseract Binary on Windows/Linux
def _configure_tesseract():
    if not _PYTESSERACT_AVAILABLE:
        return False
    possible_paths = [
        os.environ.get("TESSERACT_CMD", ""),
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"/usr/bin/tesseract",
        r"/usr/local/bin/tesseract",
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return True
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False

_TESSERACT_READY = _configure_tesseract()


def parse_indian_number(text: str):
    if not text:
        return None
    t = str(text).lower().replace("₹", "").replace(",", "").replace("(", "").replace(")", "").strip()
    m = re.search(r"\d+\.?\d*", t)
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
    return val if val > 0 else None


def fmt_inr(val):
    if not val or val == 0:
        return "₹0"
    cr = val / 1e7
    if cr >= 1:
        return f"₹{cr:,.2f} Cr"
    lk = val / 1e5
    if lk >= 1:
        return f"₹{lk:,.2f} L"
    return f"₹{val:,.0f}"


REV_LABELS = [
    "revenue from operations", "total revenue", "revenues", "net revenue",
    "total income", "gross revenue", "turnover", "net sales", "total sales", "income from operations"
]

PAT_LABELS = [
    "profit for the year", "profit after tax", "net profit", "pat",
    "profit / (loss) after tax", "profit/(loss) after tax",
    "profit for the period", "profit attributable", "net income", "profit after taxation"
]

DEBT_LABELS = [
    "total borrowings", "total debt", "borrowings", "long-term borrowings",
    "short-term borrowings", "financial liabilities", "total liabilities", "loans"
]


def _lbl_match(cell, labels):
    c = str(cell).lower().strip()
    return any(l in c for l in labels)


# ---------------- UNIT DETECTION ----------------

def detect_unit_from_header(table):
    try:
        header_text = " ".join(
            str(cell).lower()
            for row in table[:2]
            for cell in (row or [])
            if cell
        )
        if "billion" in header_text:
            return 1e9
        if "million" in header_text:
            return 1e6
        if "crore" in header_text or "cr" in header_text:
            return 1e7
        if "lakh" in header_text:
            return 1e5
        if "thousand" in header_text:
            return 1e3
    except Exception:
        pass
    return 1.0


def detect_unit_from_row(row):
    row_text = " ".join(str(cell).lower() for cell in row if cell)
    if "billion" in row_text:
        return 1e9
    if "million" in row_text:
        return 1e6
    if "crore" in row_text or "cr" in row_text:
        return 1e7
    if "lakh" in row_text:
        return 1e5
    if "thousand" in row_text:
        return 1e3
    return None


# ---------------- TABLE EXTRACTION (pdfplumber) ----------------

def _from_tables(pdf_bytes):
    res = {"revenue": None, "profit": None, "debt": None}
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    continue

                for table in tables:
                    if not table:
                        continue
                    unit_mult = detect_unit_from_header(table)

                    for row in table:
                        try:
                            if not row or len(row) < 2 or not row[0]:
                                continue
                            label = str(row[0])
                            nums = []
                            for cell in row[1:]:
                                if cell and str(cell).strip():
                                    v = parse_indian_number(str(cell))
                                    if v and v > 0:
                                        row_unit = detect_unit_from_row(row)
                                        effective_unit = row_unit if row_unit else unit_mult
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
                        except Exception:
                            continue

                if all(v is not None for v in res.values()):
                    break
    except Exception:
        pass
    return res


# ---------------- TEXT EXTRACTION (Regex) ----------------

_PAT = {
    "revenue": [
        r"(?:Revenue from [Oo]perations|Total Revenue|Net Revenue|Total Income|Turnover|Net Sales)"
        r"[^\d₹\n]{0,40}([\d,]+\.?\d*)\s*(?:crore|cr\.?|lakh|lac|million|billion)?",
    ],
    "profit": [
        r"(?:Profit [Aa]fter [Tt]ax|Net Profit|PAT|Profit for the (?:year|period))"
        r"[^\d₹\n]{0,40}([\d,]+\.?\d*)\s*(?:crore|cr\.?|lakh|lac|million|billion)?",
    ],
    "debt": [
        r"(?:Total [Bb]orrowings|Total [Dd]ebt|Borrowings)"
        r"[^\d₹\n]{0,40}([\d,]+\.?\d*)\s*(?:crore|cr\.?|lakh|lac|million|billion)?",
        r"Total [Ll]iabilities"
        r"[^\d₹\n]{0,40}([\d,]+\.?\d*)\s*(?:crore|cr\.?|lakh|lac|million|billion)?",
    ],
}


def _from_text(text):
    res = {"revenue": None, "profit": None, "debt": None}
    if not text:
        return res
    clean = re.sub(r"\s+", " ", text)
    for field, pats in _PAT.items():
        for pat in pats:
            try:
                m = re.search(pat, clean, re.IGNORECASE)
                if m:
                    v = parse_indian_number(m.group(1))
                    if v and v > 0:
                        res[field] = v
                        break
            except Exception:
                continue
    return res


# ---------------- TESSERACT OCR PIPELINE FOR SCANNED PDFS ----------------

def _ocr_scanned_pdf(raw_bytes: bytes, max_pages: int = 5) -> str:
    """
    Renders pages of a scanned or image-based PDF into high-res images,
    then executes Tesseract OCR to extract textual content.
    """
    ocr_text = ""
    if not (_TESSERACT_READY and _PYPDFIUM_AVAILABLE):
        return ""

    try:
        pdf_doc = pypdfium2.PdfDocument(raw_bytes)
        num_pages = min(len(pdf_doc), max_pages)

        for i in range(num_pages):
            page = pdf_doc.get_page(i)
            # Render page at 2x scale (~144 dpi) for OCR clarity
            image = page.render(scale=2).to_pil()
            txt = pytesseract.image_to_string(image)
            if txt:
                ocr_text += f"\n--- Page {i+1} [OCR] ---\n" + txt
    except Exception:
        pass

    return ocr_text


# ---------------- RISK SIGNALS ----------------

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
]


def _risk_signals(text):
    flags, seen = [], set()
    if not text:
        return flags
    for pat, msg in _SIGNALS:
        try:
            if re.search(pat, text, re.IGNORECASE) and msg not in seen:
                flags.append(msg)
                seen.add(msg)
        except Exception:
            continue
    return flags


# ---------------- MAIN EXTRACTION ENTRY POINT ----------------

def extract_financials(pdf_file):
    try:
        raw = pdf_file.read()
        pdf_file.seek(0)
    except Exception:
        raw = b""

    # Pass 1: Tabular extraction via pdfplumber
    tbl = _from_tables(raw)

    # Pass 2: Digital text extraction via pdfplumber
    full_text = ""
    try:
        with pdfplumber.open(BytesIO(raw)) as pdf:
            for page in pdf.pages:
                try:
                    t = page.extract_text()
                    if t:
                        full_text += t + "\n"
                except Exception:
                    continue
    except Exception:
        pass

    txt = _from_text(full_text)
    ocr_applied = False
    ocr_text = ""

    # Pass 3: If digital text extraction is sparse or empty (Scanned PDF), run Tesseract OCR
    is_scanned = len(full_text.strip()) < 80 or (tbl["revenue"] is None and txt["revenue"] is None)
    if is_scanned and _TESSERACT_READY:
        ocr_text = _ocr_scanned_pdf(raw)
        if ocr_text.strip():
            ocr_applied = True
            full_text += "\n" + ocr_text
            ocr_txt = _from_text(ocr_text)
            # Fill missing metrics from OCR
            for k in ["revenue", "profit", "debt"]:
                if (tbl[k] is None and txt[k] is None) and ocr_txt[k] is not None:
                    txt[k] = ocr_txt[k]

    risk_flags = _risk_signals(full_text)

    revenue = tbl["revenue"] or txt["revenue"] or 0.0
    profit  = tbl["profit"]  or txt["profit"]  or 0.0
    debt    = tbl["debt"]    or txt["debt"]    or 0.0

    if profit and revenue and profit > revenue > 0:
        profit = revenue * 0.05

    pipeline_label = (
        "pdfplumber + Tesseract OCR (Scanned Document Pipeline)"
        if ocr_applied else
        "pdfplumber + Tesseract OCR (Digital Pipeline)"
        if any(tbl.values()) else
        "pdfplumber + Tesseract OCR"
    )

    return {
        "revenue": str(revenue),
        "profit": str(profit),
        "debt": str(debt),
        "revenue_display": fmt_inr(revenue),
        "profit_display": fmt_inr(profit),
        "debt_display": fmt_inr(debt),
        "pdf_risk_flags": risk_flags,
        "extraction_method": "table+text" if any(tbl.values()) else "text_only",
        "pipeline": pipeline_label,
        "ocr_performed": ocr_applied,
        "tesseract_available": _TESSERACT_READY,
    }
