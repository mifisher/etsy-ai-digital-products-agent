from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from collections import Counter


@dataclass
class CompetitorListing:
    title: str
    url: str = ""
    price: float | None = None
    description: str = ""
    site_name: str = ""


def _extract_price(text: str) -> float | None:
    """Extract a price from search snippet text like 'Price:$6.20' or '$11.89'."""
    matches = re.findall(r"[Pp]rice[:\s]*\$?([0-9]+\.[0-9]{2})", text)
    if matches:
        return float(matches[0])
    matches = re.findall(r"\$([0-9]+\.[0-9]{2})", text)
    if matches:
        return float(matches[0])
    return None


def parse_search_results(raw_results: list[dict]) -> list[CompetitorListing]:
    """Convert raw web_search results into CompetitorListing objects."""
    listings = []
    for r in raw_results:
        title = r.get("title", "").strip()
        url = r.get("url", "").strip()
        desc = r.get("description", "").strip()
        price = _extract_price(desc) or _extract_price(title)
        listings.append(
            CompetitorListing(
                title=title,
                url=url,
                price=price,
                description=desc,
                site_name=r.get("siteName", ""),
            )
        )
    return listings


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    words = [w for w in text.split() if len(w) > 2]
    return words


def _extract_keywords(listings: list[CompetitorListing], top_n: int = 20) -> list[tuple[str, int]]:
    all_text = " ".join([l.title + " " + l.description for l in listings])
    words = _tokenize(all_text)
    stop = {
        "the", "and", "for", "you", "with", "your", "this", "that", "from", "can",
        "our", "are", "not", "all", "any", "had", "her", "was", "one", "our", "out",
        "day", "get", "has", "him", "his", "how", "its", "may", "new", "now", "old",
        "see", "two", "who", "boy", "did", "she", "use", "her", "way", "many", "oil",
        "sit", "set", "run", "eat", "far", "sea", "eye", "ago", "off", "too", "any",
        "say", "man", "try", "ask", "end", "why", "let", "put", "say", "she", "try",
        "way", "own", "say", "too", "old", "tell", "very", "when", "much", "would",
        "there", "their", "what", "said", "each", "which", "will", "about", "could",
        "other", "after", "first", "never", "these", "think", "where", "being",
        "every", "great", "might", "shall", "still", "those", "while", "digital",
        "download", "template", "etsy", "listing", "seller", "shop", "item",
    }
    filtered = [w for w in words if w not in stop]
    return Counter(filtered).most_common(top_n)


def analyze_competitors(listings: list[CompetitorListing]) -> dict:
    """Analyze competitor listings and return structured insights."""
    if not listings:
        return {"error": "No competitor listings provided."}

    prices = [l.price for l in listings if l.price is not None]
    price_stats = {}
    if prices:
        prices_sorted = sorted(prices)
        n = len(prices_sorted)
        price_stats = {
            "count": n,
            "min": min(prices),
            "max": max(prices),
            "mean": round(sum(prices) / n, 2),
            "median": round(prices_sorted[n // 2], 2) if n % 2 else round((prices_sorted[n // 2 - 1] + prices_sorted[n // 2]) / 2, 2),
            "recommended": round(sum(prices) / n, 2),
        }

    keywords = _extract_keywords(listings, top_n=20)

    title_patterns = []
    for l in listings:
        t = l.title.lower()
        if "|" in t:
            title_patterns.append("pipe_separator")
        if "-" in t:
            title_patterns.append("dash_separator")
        if any(x in t for x in ["notion", "template", "planner", "tracker"]):
            title_patterns.append("format_keyword")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "listing_count": len(listings),
        "price_stats": price_stats,
        "top_keywords": [{"word": w, "count": c} for w, c in keywords],
        "title_patterns": list(set(title_patterns)),
        "sample_titles": [l.title for l in listings[:5]],
    }


def suggest_title(niche: str, format_str: str, tone: str, insights: dict) -> str:
    """Suggest a title based on competitor analysis."""
    keywords = [k["word"] for k in insights.get("top_keywords", [])[:5]]
    keyword_str = ", ".join(keywords) if keywords else niche

    tone_prefix = ""
    if "premium" in tone.lower() or "luxury" in tone.lower():
        tone_prefix = "Premium "
    elif "simple" in tone.lower() or "minimal" in tone.lower():
        tone_prefix = "Minimal "
    elif "pro" in tone.lower() or "operator" in tone.lower():
        tone_prefix = "Pro "

    fmt = format_str.split("+")[0].strip()
    title = f"{tone_prefix}{niche.title()} | {fmt.title()} Template"
    if len(title) > 140:
        title = title[:137] + "..."
    return title


def suggest_tags(niche: str, format_str: str, insights: dict) -> list[str]:
    """Suggest tags based on competitor keyword frequency."""
    top = [k["word"] for k in insights.get("top_keywords", [])]
    fmt_words = [w for w in format_str.lower().split() if len(w) > 2]
    niche_words = [w for w in niche.lower().split() if len(w) > 2]

    tags = list(dict.fromkeys([t for t in top + fmt_words + niche_words if len(t) > 2]))
    base = ["digital download", "printable", "instant download"]
    tags = tags + [b for b in base if b not in tags]
    return tags[:13]


def suggest_price(insights: dict, floor: int = 5) -> int:
    """Suggest a price based on competitor median/mean."""
    stats = insights.get("price_stats", {})
    rec = stats.get("recommended")
    if rec is None:
        return 19
    price = max(int(rec), floor)
    # Round to common price points
    if price < 5:
        return 5
    if price < 10:
        return price
    if price < 15:
        return 12
    if price < 20:
        return 17
    if price < 25:
        return 22
    return round(price / 5) * 5


def load_competitor_data(path: Path) -> list[CompetitorListing]:
    """Load competitor listings from a JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return [CompetitorListing(**item) for item in data]
    if isinstance(data, dict) and "results" in data:
        return parse_search_results(data["results"])
    return []


def save_insights(insights: dict, path: Path) -> None:
    path.write_text(json.dumps(insights, indent=2) + "\n", encoding="utf-8")
