"""
mca_service.py
Fetches company data from MCA (Ministry of Corporate Affairs) India.
Uses free public endpoints — no API key required.
Falls back gracefully if MCA is unreachable.
"""

import urllib.request
import urllib.parse
import json
import re
import time


MCA_SEARCH_URL = "https://www.mca.gov.in/MCA21/mds.html"
MCA_API_URL    = "https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Referer": "https://www.mca.gov.in/",
}


def _fetch_url(url: str, post_data: bytes | None = None, timeout: int = 8) -> str | None:
    try:
        req = urllib.request.Request(url, data=post_data, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


def search_mca(company_name: str) -> dict:
    """
    Main entry point. Tries MCA portal, falls back to
    derived heuristics if network is unavailable.
    """
    if not company_name or not company_name.strip():
        return _empty_result("No company name provided")

    name = company_name.strip()

    # Try MCA Company Master Data API
    result = _try_mca_company_master(name)
    if result and not result.get("error"):
        return result

    # Fallback: derive basic info from name patterns
    return _derive_from_name(name)


def _try_mca_company_master(company_name: str) -> dict | None:
    """
    Hits MCA's company master data search.
    Returns structured dict or None if unreachable.
    """
    encoded = urllib.parse.quote(company_name.upper())
    url = f"https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do?companyName={encoded}"

    html = _fetch_url(url)
    if not html:
        return None

    # Parse key fields from HTML response
    def extract_field(label: str, content: str) -> str:
        pattern = rf"{re.escape(label)}[^:]*:?\s*</?(td|th|div|span|b)[^>]*>\s*([^<\n]+)"
        m = re.search(pattern, content, re.IGNORECASE)
        return m.group(2).strip() if m else ""

    cin          = extract_field("CIN", html) or _extract_cin(html)
    company_type = extract_field("Company Type", html)
    status       = extract_field("Company Status", html) or extract_field("Status", html)
    roc          = extract_field("ROC Code", html) or extract_field("RoC", html)
    date_incorp  = extract_field("Date of Incorporation", html) or extract_field("Incorporation Date", html)
    paid_up      = extract_field("Paid Up Capital", html) or extract_field("Paid-up Capital", html)
    registered_state = extract_field("State", html) or extract_field("Registered State", html)

    # If we got at least CIN or status, consider it a hit
    if not cin and not status:
        return None

    flags = []
    mca_penalty = 0

    status_lower = status.lower()
    if "strike" in status_lower or "struck off" in status_lower:
        flags.append("CRITICAL: Company struck off MCA register")
        mca_penalty += 25
    elif "dormant" in status_lower:
        flags.append("Company status: Dormant")
        mca_penalty += 10
    elif "amalgamated" in status_lower or "dissolved" in status_lower:
        flags.append(f"Company {status} — verify legal entity continuity")
        mca_penalty += 15
    elif "active" in status_lower:
        pass  # good
    elif status:
        flags.append(f"Non-standard MCA status: {status}")
        mca_penalty += 5

    return {
        "cin":               cin,
        "company_type":      company_type,
        "status":            status or "Unknown",
        "roc":               roc,
        "date_incorporation": date_incorp,
        "paid_up_capital":   paid_up,
        "registered_state":  registered_state,
        "mca_flags":         flags,
        "mca_penalty":       mca_penalty,
        "source":            "MCA Company Master Data",
        "error":             None,
    }


def _extract_cin(html: str) -> str:
    """Extract CIN number pattern from HTML."""
    cin_pattern = r"\b([LUF]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6})\b"
    m = re.search(cin_pattern, html)
    return m.group(1) if m else ""


def _derive_from_name(company_name: str) -> dict:
    """
    When MCA is unreachable, derive what we can from the company name.
    Identifies company type from suffix patterns.
    """
    name_upper = company_name.upper()

    if "PRIVATE LIMITED" in name_upper or "PVT LTD" in name_upper or "PVT. LTD" in name_upper:
        company_type = "Private Limited"
    elif "LIMITED" in name_upper or " LTD" in name_upper:
        company_type = "Public Limited"
    elif "LLP" in name_upper:
        company_type = "Limited Liability Partnership"
    elif "OPC" in name_upper or "ONE PERSON" in name_upper:
        company_type = "One Person Company"
    elif "SECTION 8" in name_upper or "FOUNDATION" in name_upper or "TRUST" in name_upper:
        company_type = "Section 8 / Non-Profit"
    else:
        company_type = "Unknown"

    return {
        "cin":               "Not retrieved (MCA unreachable)",
        "company_type":      company_type,
        "status":            "Not retrieved",
        "roc":               "Not retrieved",
        "date_incorporation": "Not retrieved",
        "paid_up_capital":   "Not retrieved",
        "registered_state":  "Not retrieved",
        "mca_flags":         ["MCA portal unreachable — manual verification recommended"],
        "mca_penalty":       0,
        "source":            "Name pattern inference (MCA offline)",
        "error":             "MCA portal could not be reached. Company type inferred from name.",
    }


def _empty_result(reason: str) -> dict:
    return {
        "cin": "", "company_type": "", "status": "Unknown",
        "roc": "", "date_incorporation": "", "paid_up_capital": "",
        "registered_state": "",
        "mca_flags": [], "mca_penalty": 0,
        "source": "N/A", "error": reason,
    }