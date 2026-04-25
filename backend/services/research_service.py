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


def analyze_company_news(company_name: str) -> dict:
    """
    Fetches real news from Google News RSS for the company.
    Searches multiple query angles to maximize signal.
    """
    if not company_name or not company_name.strip():
        return _empty_result()

    name = company_name.strip()
    search_queries = [
        f"{name} fraud OR scam OR investigation OR NCLT OR default",
        f"{name} penalty OR fine OR lawsuit OR regulatory",
        f"{name} financial results OR profit OR revenue",
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

    for article in all_articles:
        headline = article["title"]
        severity, keyword = classify_headline(headline)

        clean_title = re.sub(r" - [^-]+$", "", headline).strip()

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
            "severity": severity or "neutral"
        })

    overall_sentiment = _compute_sentiment(severity_counts, len(positive_signals))

    return {
        "news_checked": [a["title"] for a in all_articles],
        "news_details": news_summary,
        "external_flags": flags,
        "external_penalty": total_penalty,
        "positive_signals": positive_signals[:3],
        "severity_counts": severity_counts,
        "overall_sentiment": overall_sentiment,
        "articles_analyzed": len(all_articles)
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