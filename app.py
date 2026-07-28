import json
import os

import boto3
import requests

from rag import retrieve_context


BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "eu-west-2")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
# GNEWS_SECRET_NAME = os.environ.get("GNEWS_SECRET_NAME", "agentic-ai/gnews")
GNEWS_SECRET_NAME = os.environ.get("GNEWS_SECRET_NAME", "agentic-ai/gnews")
GNEWS_API_KEY = os.environ.get("GNEWS_API_KEY")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
secretsmanager = boto3.client("secretsmanager", region_name=BEDROCK_REGION)


def _extract_gnews_api_key(secret_string: str) -> str:
    """
    Extract the GNews API key from either:

    1. A plain-text secret value, or
    2. A JSON secret containing one of the recognised key names.
    """
    try:
        secret_json = json.loads(secret_string)
    except json.JSONDecodeError:
        api_key = secret_string.strip()

        if not api_key:
            raise ValueError("The GNews API key is empty.")

        return api_key

    if not isinstance(secret_json, dict):
        raise ValueError("The GNews secret JSON must contain an object.")

    api_key = (
        secret_json.get("GNEWS_API_KEY")
        or secret_json.get("api_key")
        or secret_json.get("apikey")
    )

    if not api_key or not isinstance(api_key, str):
        raise ValueError("GNews API key not found in secret JSON.")

    return api_key.strip()


def get_gnews_api_key() -> str:
    """
    Resolve the GNews API key using either of the supported deployment modes.

    Preferred ECS mode:
        GNEWS_API_KEY contains the actual secret value injected by ECS from
        AWS Secrets Manager.

    Existing EC2/local mode:
        GNEWS_SECRET_NAME contains the Secrets Manager secret name or ARN,
        and the application retrieves the secret at runtime.

    Compatibility mode:
        Some generated ECS configurations inject the actual secret value into
        GNEWS_SECRET_NAME. If GNEWS_API_KEY is absent, this function first
        checks whether GNEWS_SECRET_NAME looks like a secret name/ARN. If it
        does not, it treats the value as the API key.
    """

    # Cleanest ECS configuration: secret value injected into GNEWS_API_KEY.
    if GNEWS_API_KEY:
        return _extract_gnews_api_key(GNEWS_API_KEY)

    configured_value = GNEWS_SECRET_NAME.strip()

    if not configured_value:
        raise ValueError(
            "Neither GNEWS_API_KEY nor GNEWS_SECRET_NAME has been configured."
        )

    looks_like_secret_identifier = (
        configured_value.startswith("arn:aws:secretsmanager:")
        or configured_value.startswith("agentic-ai/")
        or configured_value.startswith("/")
    )

    if looks_like_secret_identifier:
        secret = secretsmanager.get_secret_value(SecretId=configured_value)
        secret_string = secret.get("SecretString")

        if not secret_string:
            raise ValueError(
                "The configured GNews secret does not contain SecretString."
            )

        return _extract_gnews_api_key(secret_string)

    # Compatibility with AWS Transform injecting the actual secret value
    # into GNEWS_SECRET_NAME.
    return _extract_gnews_api_key(configured_value)

def sanitize_gnews_query(query: str) -> str:
    cleaned = query.lower()

    for char in [
        "?",
        ":",
        ",",
        ".",
        "/",
        "\\",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
        '"',
        "'",
        "’",
        "“",
        "”",
        "-",
        "_",
        ";",
        "|",
    ]:
        cleaned = cleaned.replace(char, " ")

    return " ".join(cleaned.split())


def parse_model_json(output_text: str) -> dict:
    clean_output = output_text.strip()

    if "```json" in clean_output:
        clean_output = (
            clean_output
            .split("```json", 1)[1]
            .split("```", 1)[0]
            .strip()
        )

    elif "```" in clean_output:
        clean_output = (
            clean_output
            .split("```", 1)[1]
            .split("```", 1)[0]
            .strip()
        )

    try:
        return json.loads(clean_output)

    except json.JSONDecodeError:
        return {"raw_model_output": output_text}


def build_news_query(topic: str) -> str:
    stop_words = {
        "what",
        "does",
        "the",
        "a",
        "an",
        "about",
        "and",
        "or",
        "for",
        "to",
        "of",
        "in",
        "on",
        "with",
        "how",
        "should",
        "can",
        "could",
        "would",
        "is",
        "are",
        "be",
        "by",
        "from",
        "that",
        "this",
        "it",
        "say",
        "recommend",
        "compare",
        "current",
        "landing",
        "zone",
        "gw",
        "gw1",
    }

    cleaned = sanitize_gnews_query(topic)

    words = [
        word.strip()
        for word in cleaned.split()
        if word.strip() and word.strip() not in stop_words
    ]

    if "jwt" in words or "authorization" in words or "authorisation" in words:
        return "AI security authorization"

    if "zero" in words and "trust" in words:
        return "zero trust AI"

    if "rag" in words or "vector" in words:
        return "enterprise RAG AI"

    if "guardrails" in words:
        return "AI guardrails enterprise"

    if not words:
        return "enterprise AI"

    return " ".join(words[:3])


def build_news_query_with_nova(topic: str) -> str:
    prompt = f"""
Rewrite the following user question into a SHORT public news search query.

Rules:
- Return valid JSON only.
- Use this exact shape:
{{"query": "..."}}
- MAXIMUM 3 WORDS.
- Prefer broad public-news phrases.
- Remove internal project terminology.
- No punctuation.
- No hyphens.
- No quotes.

User question:
{topic}
"""

    try:
        response = bedrock.converse(
            modelId=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
            inferenceConfig={
                "maxTokens": 60,
                "temperature": 0.1,
                "topP": 0.9,
            },
        )

        output_text = response["output"]["message"]["content"][0]["text"]

        parsed = parse_model_json(output_text)

        rewritten_query = parsed.get("query", topic)

        sanitized = sanitize_gnews_query(rewritten_query)

        if sanitized:
            return " ".join(sanitized.split()[:3])

    except Exception as error:
        print(
            f"Nova news-query rewrite failed, "
            f"falling back to local rewrite: {error}"
        )

    fallback = build_news_query(topic)

    return " ".join(fallback.split()[:3])


def fetch_news(topic: str, max_results: int = 5) -> list:
    api_key = get_gnews_api_key()

    safe_topic = build_news_query_with_nova(topic)

    print(f"GNews rewritten query: {safe_topic}")

    url = "https://gnews.io/api/v4/search"

    params = {
        "q": safe_topic,
        "lang": "en",
        "max": max_results,
        "apikey": api_key,
    }

    response = requests.get(url, params=params, timeout=10)

    response.raise_for_status()

    return response.json().get("articles", [])


def summarise_with_nova(topic: str, articles: list) -> tuple:
    try:
        rag_context = retrieve_context(topic)

    except Exception as rag_error:
        print(f"RAG retrieval failed, continuing without RAG: {rag_error}")
        rag_context = []

    article_text = "\n\n".join(
        [
            f"Title: {article.get('title', '')}\n"
            f"Description: {article.get('description', '')}\n"
            f"Source: {article.get('source', {}).get('name', '')}\n"
            f"URL: {article.get('url', '')}"
            for article in articles
        ]
    )

    rag_text = "\n\n".join(
        [
            f"Document: {item['document']}\n"
            f"Content: {item['text']}"
            for item in rag_context
        ]
    )

    prompt = f"""
You are an enterprise AI research assistant.

Use BOTH:
1. Internal enterprise knowledge base context
2. Recent news articles

If recent news articles are empty,
continue using the internal knowledge base context.

Topic:
{topic}

Internal enterprise knowledge base context:
{rag_text}

Recent news articles:
{article_text}

Return valid JSON only.

Required fields:
summary: string
key_themes: list of strings
risks: list of strings
opportunities: list of strings
enterprise_recommendations: list of strings
follow_up_questions: list of strings
"""

    response = bedrock.converse(
        modelId=MODEL_ID,
        messages=[
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ],
        inferenceConfig={
            "maxTokens": 1200,
            "temperature": 0.3,
            "topP": 0.9,
        },
    )

    output_text = response["output"]["message"]["content"][0]["text"]

    parsed = parse_model_json(output_text)

    return parsed, rag_context


def parse_event_body(event) -> dict:
    body = event.get("body")

    if isinstance(body, str):
        return json.loads(body)

    if isinstance(body, dict):
        return body

    return event


def handler(event, context):
    try:
        body = parse_event_body(event)

        topic = body.get("topic", "agentic AI")

        max_results = int(body.get("max_results", 5))

        try:
            articles = fetch_news(topic, max_results)

        except Exception as news_error:
            print(
                "GNews lookup failed, "
                f"continuing with RAG-only answer: {news_error}"
            )

            articles = []

        ai_summary, rag_context = summarise_with_nova(topic, articles)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "topic": topic,
                    "model": MODEL_ID,
                    "summary": ai_summary,
                    "source_articles": [
                        {
                            "title": article.get("title"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                        }
                        for article in articles
                    ],
                    "rag_context": [
                        {
                            "document": item["document"],
                            "score": round(item["score"], 4),
                            "text": item["text"][:500],
                        }
                        for item in rag_context
                    ],
                }
            ),
        }

    except Exception as error:
        print(f"Unhandled application error: {error}")

        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(error)}),
        }
