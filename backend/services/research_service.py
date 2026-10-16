import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import re
import time


RISK_KEYWORDS = {
    "critical": [
        "fraud", "scam", "arrest", "FIR", "SFIO", "ED probe", "money laundering",
        "Enforcement Directorate", "CBI", "chargesheet", "bankrupt", "insolvency",
        "NCLT", "liquidation", "wilful defaulter", "RBI ban", "SEBI ban",
        "NPA", "loan default", "debt restructuring"
    ],
    "high": [
        "investigation", "inquiry", "notice", "penalty", "fine", "lawsuit",
        "legal action", "court case", "litigation", "contempt", "raid",
        "Income Tax", "GST evasion", "accounting irregularities", "misappropriation",
        "corporate governance", "whistleblower", "forensic audit"
    ],
    "medium": [
        "downgrade", "rating cut", "management change", "CEO resign", "exits",
        "layoffs", "plant shutdown", "factory fire", "regulatory concern",
        "compliance issue", "profit warning", "revenue miss", "supply chain"
    ],
    "positive": [
        "expansion", "new contract", "record profit", "strong growth", "acquisition",
        "partnership", "IPO", "fundraise", "award", "recognized", "export order"
    ]
}

PENALTY_MAP = {"critical": 20, "high": 10, "medium": 5}


def fetch_google_news(query: str, max_articles: int = 10) -> list[dict]:
    """Fetch news from Google News RSS — no API key required."""
    encoded = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=en-IN&gl=IN&ceid=IN:en"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read()

        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return []

        articles = []
        for item in channel.findall("item")[:max_articles]:
            title = item.findtext("title", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            source_el = item.find("{http://purl.org/dc/elements/1.1/}creator")
            source = source_el.text.strip() if source_el is not None else "Unknown"
            articles.append({
                "title": title,
                "pub_date": pub_date,
                "source": source
            })

        return articles

    except Exception as e:
        return [{"title": f"[RSS fetch error: {e}]", "pub_date": "", "source": ""}]


def classify_headline(headline: str) -> tuple[str | None, str | None]:
    """Returns (severity, matched_keyword) for a headline."""
    lower = headline.lower()
    for severity in ["critical", "high", "medium"]:
        for kw in RISK_KEYWORDS[severity]:
            if kw.lower() in lower:
                return severity, kw
    for kw in RISK_KEYWORDS["positive"]:
        if kw.lower() in lower:
            return "positive", kw
    return None, None


def is_relevant_to_company(headline: str, company_name: str) -> bool:
    """
    Verifies that the headline directly mentions the borrower entity or its
    core distinctive name tokens, preventing generic national/international
    news (e.g. Disney, ABC, Adani) from incorrectly penalizing the borrower.
    """
    if not headline or not company_name:
        return False

    hl = headline.lower()
    comp_clean = company_name.lower().strip()

    # Exact full name match
    if comp_clean in hl:
        return True

    # Strip generic legal suffixes
    noise_words = {
        "pvt", "ltd", "limited", "private", "inc", "corp", "corporation",
        "llp", "global", "solutions", "services", "technologies", "enterprises",
        "india", "international", "holdings", "group", "co", "company"
    }
    raw_tokens = [w for w in re.split(r"[\s,.\-_/]+", comp_clean) if len(w) >= 3]
    distinctive_tokens = [w for w in raw_tokens if w not in noise_words]

    # If no distinctive tokens remain, fall back to any token >= 4 chars
    search_tokens = distinctive_tokens if distinctive_tokens else [w for w in raw_tokens if len(w) >= 4]

    if not search_tokens:
        return comp_clean in hl

    # Check if any distinctive token appears as a word in the headline
    for tok in search_tokens:
        if re.search(r"\b" + re.escape(tok) + r"\b", hl):
            return True

    return False


def analyze_company_news(company_name: str) -> dict:
    """
    Fetches real news from Google News RSS for the company.
    Strictly filters out irrelevant stories using entity verification.
    """
    if not company_name or not company_name.strip():
        return _empty_result()

    name = company_name.strip()
    # Strip suffixes for query builder
    core_name = re.sub(
        r"\b(pvt|ltd|limited|private|inc|corp|corporation|llp)\b",
        "", name, flags=re.IGNORECASE
    ).strip()
    if not core_name:
        core_name = name

    # Use strict quotes and grouping in Google News queries
    search_queries = [
        f'"{name}" (fraud OR scam OR investigation OR NCLT OR default)',
        f'"{core_name}" (penalty OR fine OR lawsuit OR regulatory OR CBI OR ED)',
        f'"{core_name}" (financial results OR profit OR revenue OR expansion)',
    ]

    all_articles = []
    seen_titles = set()

    for query in search_queries:
        articles = fetch_google_news(query, max_articles=6)
        for a in articles:
            title_key = a["title"][:60].lower()
            if title_key not in seen_titles and a["title"]:
                seen_titles.add(title_key)
                all_articles.append(a)
        time.sleep(0.3)

    flags = []
    total_penalty = 0
    news_summary = []
    positive_signals = []
    severity_counts = {"critical": 0, "high": 0, "medium": 0}
    verified_articles_count = 0

    for article in all_articles:
        headline = article["title"]
        clean_title = re.sub(r" - [^-]+$", "", headline).strip()

        # CRITICAL FILTER: Verify article actually mentions the borrower entity
        is_relevant = is_relevant_to_company(headline, name)

        severity, keyword = classify_headline(headline)

        # Only apply penalties and risk flags if headline is VERIFIED to be about borrower
        if is_relevant:
            verified_articles_count += 1
            if severity in ("critical", "high", "medium"):
                penalty = PENALTY_MAP[severity]
                total_penalty = min(total_penalty + penalty, 40)
                severity_counts[severity] += 1
                flag_msg = f"[{severity.upper()}] {clean_title}"
                if flag_msg not in flags:
                    flags.append(flag_msg)

            elif severity == "positive":
                positive_signals.append(clean_title)

            news_summary.append({
                "title": clean_title,
                "pub_date": article["pub_date"],
                "source": article["source"],
                "severity": severity or "neutral",
                "verified_borrower_match": True,
            })
        else:
            # Irrelevant / ambient national news (e.g. Disney, ABC) - do NOT penalize!
            # Keep in summary with non-penalty flag for transparency if needed
            pass

    overall_sentiment = _compute_sentiment(severity_counts, len(positive_signals))

    return {
        "news_checked": [a["title"] for a in news_summary],
        "news_details": news_summary,
        "external_flags": flags,
        "external_penalty": total_penalty,
        "positive_signals": positive_signals[:3],
        "severity_counts": severity_counts,
        "overall_sentiment": overall_sentiment,
        "articles_analyzed": verified_articles_count,
    }



def _compute_sentiment(severity_counts: dict, positive_count: int) -> str:
    if severity_counts["critical"] >= 1:
        return "High Risk"
    if severity_counts["high"] >= 2:
        return "Elevated Risk"
    if severity_counts["high"] >= 1 or severity_counts["medium"] >= 2:
        return "Moderate Risk"
    if positive_count >= 2:
        return "Positive"
    return "Neutral"


def _empty_result() -> dict:
    return {
        "news_checked": [],
        "news_details": [],
        "external_flags": [],
        "external_penalty": 0,
        "positive_signals": [],
        "severity_counts": {"critical": 0, "high": 0, "medium": 0},
        "overall_sentiment": "Neutral",
        "articles_analyzed": 0
    }
