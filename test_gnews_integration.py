import os

import pytest

from app import search_gnews


@pytest.mark.integration
def test_gnews_api_returns_real_articles():
    api_key = os.environ.get("GNEWS_API_KEY")

    if not api_key:
        pytest.skip("GNEWS_API_KEY not provided")

    data = search_gnews("AWS generative AI", api_key, max_results=3)

    articles = data.get("articles", [])

    assert len(articles) > 0
    assert articles[0].get("title")
    assert articles[0].get("url")
    assert articles[0].get("source")
