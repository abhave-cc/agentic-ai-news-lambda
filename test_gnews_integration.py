import pytest

from app import fetch_news


@pytest.mark.integration
def test_fetch_news_returns_real_articles():
    articles = fetch_news("technology", max_results=3)

    print(articles)

    assert len(articles) > 0, "No articles returned"

    assert articles[0].get("title")
    assert articles[0].get("url")
