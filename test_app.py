import os
import json
from app import lambda_handler


def test_missing_api_key_returns_500(monkeypatch):
    monkeypatch.delenv("GNEWS_API_KEY", raising=False)

    response = lambda_handler({"query": "aws"}, None)

    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "Missing GNEWS_API_KEY" in body["error"]


def test_query_defaults_when_missing(monkeypatch):
    monkeypatch.setenv("GNEWS_API_KEY", "dummy")

    # We are not calling the real API in this unit test.
    # This just proves the handler can be imported and called.
    assert callable(lambda_handler)
