import json

from app import lambda_handler


def test_lambda_handler_returns_articles_when_gnews_mocked(monkeypatch):
    monkeypatch.setattr("app.get_gnews_api_key", lambda: "dummy-key")

    monkeypatch.setattr(
        "app.search_gnews",
        lambda query, api_key: {
            "articles": [
                {
                    "title": "Test article",
                    "source": {"name": "Test Source"},
                    "url": "https://example.com",
                    "publishedAt": "2026-01-01T00:00:00Z",
                }
            ]
        },
    )

    response = lambda_handler({"query": "aws"}, None)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["query"] == "aws"
    assert body["count"] == 1
    assert body["articles"][0]["title"] == "Test article"


def test_lambda_handler_handles_errors(monkeypatch):
    monkeypatch.setattr("app.get_gnews_api_key", lambda: "dummy-key")

    def broken_search(query, api_key):
        raise Exception("GNews failed")

    monkeypatch.setattr("app.search_gnews", broken_search)

    response = lambda_handler({"query": "aws"}, None)

    assert response["statusCode"] == 500
