import html
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import requests


HN_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
ARXIV_SEARCH_URL = "https://export.arxiv.org/api/query"


def _extract_keywords(query: str) -> list[str]:
    stop_words = {
        "what", "does", "the", "a", "an", "about", "and", "or", "for",
        "to", "of", "in", "on", "with", "how", "should", "can", "could",
        "would", "is", "are", "be", "by", "from", "that", "this", "it",
        "say", "recommend", "compare", "current", "latest"
    }

    cleaned = (
        query.lower()
        .replace("?", " ")
        .replace(":", " ")
        .replace(",", " ")
        .replace(".", " ")
        .replace("/", " ")
        .replace("-", " ")
    )

    return [
        word.strip()
        for word in cleaned.split()
        if word.strip() and word.strip() not in stop_words
    ]


def _keyword_score(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def fetch_hacker_news(query: str, limit: int = 5) -> list[dict]:
    keywords = _extract_keywords(query)

    response = requests.get(HN_TOP_STORIES_URL, timeout=10)
    response.raise_for_status()

    story_ids = response.json()[:80]
    stories = []

    for item_id in story_ids:
        item_response = requests.get(
            HN_ITEM_URL.format(item_id=item_id),
            timeout=10,
        )
        item_response.raise_for_status()

        item = item_response.json() or {}

        if item.get("type") != "story":
            continue

        title = item.get("title", "")
        url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
        score = _keyword_score(title, keywords)

        if score > 0:
            stories.append(
                {
                    "title": title,
                    "url": url,
                    "score": item.get("score", 0),
                    "source": "Hacker News",
                    "keyword_score": score,
                }
            )

    stories.sort(
        key=lambda item: (item["keyword_score"], item["score"]),
        reverse=True,
    )

    return stories[:limit]


def fetch_arxiv(query: str, limit: int = 5) -> list[dict]:
    keywords = _extract_keywords(query)
    search_query = " ".join(keywords[:5]) if keywords else "artificial intelligence"

    params = {
        "search_query": f"all:{quote_plus(search_query)}",
        "start": 0,
        "max_results": limit,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    response = requests.get(
        ARXIV_SEARCH_URL,
        params=params,
        timeout=10,
    )
    response.raise_for_status()

    root = ET.fromstring(response.text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    results = []

    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        summary = entry.findtext("atom:summary", default="", namespaces=ns)
        link = entry.findtext("atom:id", default="", namespaces=ns)
        published = entry.findtext("atom:published", default="", namespaces=ns)

        results.append(
            {
                "title": " ".join(html.unescape(title).split()),
                "summary": " ".join(html.unescape(summary).split())[:600],
                "url": link,
                "published": published,
                "source": "arXiv",
            }
        )

    return results
