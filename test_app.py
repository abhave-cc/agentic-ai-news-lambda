import json

from app import handler


def test_handler_returns_ai_summary_when_selected_tools_succeed(monkeypatch):
    monkeypatch.setattr(
        "app.plan_tools_with_nova",
        lambda topic: {
            "use_rag": True,
            "use_gnews": True,
            "use_hacker_news": True,
            "use_arxiv": True,
            "reason": "Test planner selected all tools.",
        },
    )

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
        lambda topic, articles, hacker_news_items, arxiv_items, use_rag=True: (
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

    assert body["tool_plan"]["reason"] == "Test planner selected all tools."
    assert body["tools_used"] == ["rag", "gnews", "hacker_news", "arxiv"]

    assert body["source_articles"][0]["title"] == "Test article"
    assert body["hacker_news"][0]["title"] == "Test HN story"
    assert body["arxiv_papers"][0]["title"] == "Test arXiv paper"
    assert body["rag_context"][0]["document"] == "docs/test.md"


def test_handler_skips_tools_when_planner_says_so(monkeypatch):
    monkeypatch.setattr(
        "app.plan_tools_with_nova",
        lambda topic: {
            "use_rag": True,
            "use_gnews": False,
            "use_hacker_news": False,
            "use_arxiv": False,
            "reason": "Internal knowledge question.",
        },
    )

    def should_not_call_gnews(topic, max_results):
        raise AssertionError("GNews should not have been called")

    def should_not_call_hn(topic, limit=5):
        raise AssertionError("Hacker News should not have been called")

    def should_not_call_arxiv(topic, limit=5):
        raise AssertionError("arXiv should not have been called")

    monkeypatch.setattr("app.fetch_news", should_not_call_gnews)
    monkeypatch.setattr("app.fetch_hacker_news", should_not_call_hn)
    monkeypatch.setattr("app.fetch_arxiv", should_not_call_arxiv)

    monkeypatch.setattr(
        "app.summarise_with_nova",
        lambda topic, articles, hacker_news_items, arxiv_items, use_rag=True: (
            {
                "summary": "RAG-only summary",
                "key_themes": ["Internal guidance"],
                "risks": [],
                "opportunities": [],
                "enterprise_recommendations": [],
                "follow_up_questions": [],
            },
            [
                {
                    "document": "docs/internal.md",
                    "score": 0.88,
                    "text": "Internal RAG context",
                }
            ],
        ),
    )

    response = handler(
        {"topic": "What does our AI landing zone say about JWT?", "max_results": 1},
        None,
    )

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["tools_used"] == ["rag"]
    assert body["source_articles"] == []
    assert body["hacker_news"] == []
    assert body["arxiv_papers"] == []
    assert body["summary"]["summary"] == "RAG-only summary"


def test_handler_continues_when_selected_external_tools_fail(monkeypatch):
    monkeypatch.setattr(
        "app.plan_tools_with_nova",
        lambda topic: {
            "use_rag": True,
            "use_gnews": True,
            "use_hacker_news": True,
            "use_arxiv": True,
            "reason": "Test planner selected all tools.",
        },
    )

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
        lambda topic, articles, hacker_news_items, arxiv_items, use_rag=True: (
            {
                "summary": "RAG-only fallback summary",
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

    response = handler({"topic": "agentic AI", "max_results": 1}, None)

    assert response["statusCode"] == 200

    body = json.loads(response["body"])

    assert body["summary"]["summary"] == "RAG-only fallback summary"
    assert body["source_articles"] == []
    assert body["hacker_news"] == []
    assert body["arxiv_papers"] == []
    assert body["rag_context"][0]["document"] == "docs/test.md"
