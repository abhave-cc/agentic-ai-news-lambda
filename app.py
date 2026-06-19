import json
import os

import boto3
import requests

from rag import retrieve_context
from external_sources import fetch_hacker_news, fetch_arxiv


BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "eu-west-2")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")
GNEWS_SECRET_NAME = os.environ.get("GNEWS_SECRET_NAME", "agentic-ai/gnews")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
secretsmanager = boto3.client("secretsmanager", region_name=BEDROCK_REGION)


def get_gnews_api_key() -> str:
    secret = secretsmanager.get_secret_value(SecretId=GNEWS_SECRET_NAME)
    secret_string = secret["SecretString"]

    try:
        secret_json = json.loads(secret_string)

        api_key = (
            secret_json.get("GNEWS_API_KEY")
            or secret_json.get("api_key")
            or secret_json.get("apikey")
        )

        if not api_key:
            raise ValueError("GNews API key not found in secret JSON.")

        return api_key

    except json.JSONDecodeError:
        return secret_string


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


def summarise_with_nova(
    topic: str,
    articles: list,
    hacker_news_items: list,
    arxiv_items: list,
    use_rag: bool = True,
) -> tuple:

    if use_rag:
        try:
            rag_context = retrieve_context(topic)
        except Exception as rag_error:
            print(f"RAG retrieval failed, continuing without RAG: {rag_error}")
            rag_context = []
    else:
        print("Planner skipped RAG")
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

    hn_text = "\n\n".join(
        [
            f"Title: {item.get('title', '')}\n"
            f"Score: {item.get('score', '')}\n"
            f"URL: {item.get('url', '')}"
            for item in hacker_news_items
        ]
    )

    arxiv_text = "\n\n".join(
        [
            f"Title: {item.get('title', '')}\n"
            f"Summary: {item.get('summary', '')}\n"
            f"URL: {item.get('url', '')}"
            for item in arxiv_items
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

Hacker News engineering discussion:
{hn_text}

arXiv research papers:
{arxiv_text}

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


def plan_tools_with_nova(topic: str) -> dict:
    prompt = f"""
You are a tool-selection planner for an enterprise AI research assistant.

Available tools:
- rag: internal enterprise knowledge base
- gnews: current news
- hacker_news: engineering community discussion
- arxiv: research papers

Decide which tools should be used for the user question.

Rules:
- Return valid JSON only.
- Use this exact shape:
{{
  "use_rag": true,
  "use_gnews": true,
  "use_hacker_news": true,
  "use_arxiv": true,
  "reason": "short reason"
}}
- Use RAG when the question mentions internal guidance, landing zone, architecture, governance, policy, standards, or recommendations.
- Use GNews when the question asks about latest, current, trends, market, news, industry developments, regulation, security developments.
- Use Hacker News when the question asks about engineering sentiment, developer adoption, tools, frameworks, implementation, or community discussion.
- Use arXiv when the question asks about research, papers, academic direction, emerging techniques, evaluation, RAG, agents, or model behaviour.
- If unsure, use rag and gnews.

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
                "maxTokens": 300,
                "temperature": 0.1,
                "topP": 0.9,
            },
        )

        output_text = response["output"]["message"]["content"][0]["text"]
        plan = parse_model_json(output_text)

        return {
            "use_rag": bool(plan.get("use_rag", True)),
            "use_gnews": bool(plan.get("use_gnews", True)),
            "use_hacker_news": bool(plan.get("use_hacker_news", False)),
            "use_arxiv": bool(plan.get("use_arxiv", False)),
            "reason": plan.get(
                "reason",
                "Planner selected tools based on the question.",
            ),
        }

    except Exception as error:
        print(f"Tool planner failed, using safe default: {error}")
        return {
            "use_rag": True,
            "use_gnews": True,
            "use_hacker_news": False,
            "use_arxiv": False,
            "reason": "Planner failed; defaulted to RAG and GNews.",
        }

def handler(event, context):
    print("V5A BUILD WITH HACKERNEWS + ARXIV")
    try:
        body = parse_event_body(event)

        topic = body.get("topic", "agentic AI")

        max_results = int(body.get("max_results", 5))

        tool_plan = plan_tools_with_nova(topic)
        print(f"Tool plan: {json.dumps(tool_plan)}")

       if tool_plan["use_gnews"]:
            try:
                articles = fetch_news(topic, max_results)
            except Exception as news_error:
                print(
                    "GNews lookup failed, "
                    f"continuing without GNews: {news_error}"
                )
                articles = []
        else:
                print("Planner skipped GNews")
                articles = []

            articles = []
        
        print("ABOUT TO CALL HACKER NEWS")
       if tool_plan["use_hacker_news"]:
            try:
                hacker_news_items = fetch_hacker_news(topic, limit=5)
            except Exception as hn_error:
                print(f"Hacker News lookup failed, continuing: {hn_error}")
                hacker_news_items = []
      else:
                print("Planner skipped Hacker News")
                hacker_news_items = [] 
       
        print("HACKER NEWS CALL FINISHED")
        
        if tool_plan["use_arxiv"]:
            try:
                arxiv_items = fetch_arxiv(topic, limit=5)
            except Exception as arxiv_error:
                print(f"arXiv lookup failed, continuing: {arxiv_error}")
                arxiv_items = []
        else:
            print("Planner skipped arXiv")
            arxiv_items = []


        ai_summary, rag_context = summarise_with_nova(
            topic,
            articles,
            hacker_news_items,
            arxiv_items,
            use_rag=tool_plan["use_rag"],
        )
        
        print(f"Hacker News items returned: {len(hacker_news_items)}")
        print(f"arXiv items returned: {len(arxiv_items)}")

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "topic": topic,
                    "model": MODEL_ID,
                    "tool_plan": tool_plan,
                    "tools_used": [
                        tool
                        for tool, used in {
                            "rag": tool_plan["use_rag"],
                            "gnews": tool_plan["use_gnews"],
                            "hacker_news": tool_plan["use_hacker_news"],
                            "arxiv": tool_plan["use_arxiv"],
                        }.items()
                        if used
                    ],
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

                    "hacker_news": hacker_news_items,
                    "arxiv_papers": arxiv_items,
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
