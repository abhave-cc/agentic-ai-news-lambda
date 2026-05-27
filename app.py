import json
import os
import boto3
import requests

GNEWS_API_KEY = os.environ.get("GNEWS_SECRET_NAME")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "eu-west-2")
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-lite-v1:0")

bedrock = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def fetch_news(topic: str, max_results: int = 5):
    url = "https://gnews.io/api/v4/search"
    params = {
        "q": topic,
        "lang": "en",
        "max": max_results,
        "apikey": GNEWS_API_KEY,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("articles", [])


def summarise_with_nova(topic: str, articles: list):
    article_text = "\n\n".join(
        [
            f"Title: {a.get('title', '')}\n"
            f"Description: {a.get('description', '')}\n"
            f"Source: {a.get('source', {}).get('name', '')}\n"
            f"URL: {a.get('url', '')}"
            for a in articles
        ]
    )

    prompt = f"""
You are a concise research assistant.

Topic: {topic}

News articles:
{article_text}

Return valid JSON only with these fields:
summary: string
key_themes: list of strings
risks: list of strings
opportunities: list of strings
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
            "maxTokens": 800,
            "temperature": 0.3,
            "topP": 0.9,
        },
    )

    output_text = response["output"]["message"]["content"][0]["text"]

    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        return {"raw_model_output": output_text}


def handler(event, context):
    try:
        body = event.get("body")

        if isinstance(body, str):
            body = json.loads(body)
        elif not body:
            body = event

        topic = body.get("topic", "agentic AI")
        max_results = int(body.get("max_results", 5))

        articles = fetch_news(topic, max_results)
        ai_summary = summarise_with_nova(topic, articles)

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
                            "title": a.get("title"),
                            "source": a.get("source", {}).get("name"),
                            "url": a.get("url"),
                        }
                        for a in articles
                    ],
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
