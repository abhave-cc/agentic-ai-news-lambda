import os

import pytest

from app import fetch_news


@pytest.mark.integration
def test_fetch_news_returns_real_articles(monkeypatch):
    api_key = os.environ.get("GNEWS_API_KEY")

    if not api_key:
        pytest.skip("GNEWS_API_KEY not provided")

    monkeypatch.setattr("app.get_gnews_api_key", lambda: api_key)

    articles = fetch_news("technology", max_results=3)

    print(articles)

    assert len(articles) > 0, "No articles returned"
    assert articles[0].get("title")
    assert articles[0].get("url")
