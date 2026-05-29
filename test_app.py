def test_handler_continues_when_gnews_fails(monkeypatch):
    def broken_fetch_news(topic, max_results):
        raise Exception("GNews failed")

    monkeypatch.setattr("app.fetch_news", broken_fetch_news)

    monkeypatch.setattr(
        "app.summarise_with_nova",
        lambda topic, articles: (
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
    assert body["rag_context"][0]["document"] == "docs/test.md"
