import json

from app import handler


def test_handler_returns_ai_summary_when_dependencies_mocked(monkeypatch):
    monkeypatch.setattr(
        "app.fetch_news",
        lambda topic, max_results: [
            {
                "title": "Test article",
                "description": "Test description",
                "source": {"name": "Test Source"},
                "url": "https://example.com",
            }
        ],
    )

    monkeypatch.setattr(
        "app.fetch_hacker_news",
        lambda topic, limit=5: [
            {
                "title": "Test HN story",
                "url": "https://news.ycombinator.com/item?id=123",
                "score": 100,
                "source": "Hacker News",
            }
        ],
    )

    monkeypatch.setattr(
        "app.fetch_arxiv",
        lambda topic, limit=5: [
            {
                "title": "Test arXiv paper",
                "summary": "Test paper summary",
                "url": "https://arxiv.org/abs/1234.56789",
                "published": "2026-01-01T00:00:00Z",
                "source": "arXiv",
            }
        ],
    )

    monkeypatch.setattr(
        "app.summarise_with_nova",
        lambda topic, articles, hacker_news_items, arxiv_items: (
            {
                "summary": "Test summary",
                "key_themes": ["Theme 1"],
                "risks": ["Risk 1"],
                "opportunities": ["Opportunity 1"],
                "enterprise_recommendations": ["Recommendation 1"],
                "follow_up_questions": ["Question 1"],
            },
            [
                {
                    "document": "docs/test.md",
                    "score": 0.91,
                    "text": "Test RAG context",
                }
            ],
        ),
    )

    response = handler({"topic": "aws", "max_results": 1}, None)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["topic"] == "aws"
    assert body["summary"]["summary"] == "Test summary"
    assert body["source_articles"][0]["title"] == "Test article"
    assert body["rag_context"][0]["document"] == "docs/test.md"
    assert body["hacker_news"][0]["title"] == "Test HN story"
    assert body["arxiv_papers"][0]["title"] == "Test arXiv paper"


def test_handler_continues_when_external_sources_fail(monkeypatch):
    def broken_fetch_news(topic, max_results):
        raise Exception("GNews failed")

    def broken_hacker_news(topic, limit=5):
        raise Exception("Hacker News failed")

    def broken_arxiv(topic, limit=5):
        raise Exception("arXiv failed")

    monkeypatch.setattr("app.fetch_news", broken_fetch_news)
    monkeypatch.setattr("app.fetch_hacker_news", broken_hacker_news)
    monkeypatch.setattr("app.fetch_arxiv", broken_arxiv)

    monkeypatch.setattr(
        "app.summarise_with_nova",
        lambda topic, articles, hacker_news_items, arxiv_items: (
            {
                "summary": "RAG-only summary",
                "key_themes": ["Theme 1"],
                "risks": [],
                "opportunities": [],
                "enterprise_recommendations": [],
                "follow_up_questions": [],
            },
            [
                {
                    "document": "docs/test.md",
                    "score": 0.91,
                    "text": "Test RAG context",
                }
            ],
        ),
    )

    response = handler({"topic": "aws", "max_results": 1}, None)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["summary"]["summary"] == "RAG-only summary"
    assert body["source_articles"] == []
    assert body["hacker_news"] == []
    assert body["arxiv_papers"] == []
    assert body["rag_context"][0]["document"] == "docs/test.md"
