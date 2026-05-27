import json
import os

import boto3
import requests


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


def fetch_news(topic: str, max_results: int = 5) -> list:
    api_key = get_gnews_api_key()

    url = "https://gnews.io/api/v4/search"
    params = {
        "q": topic,
        "lang": "en",
        "max": max_results,
        "apikey": api_key,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json().get("articles", [])


def parse_model_json(output_text: str) -> dict:
    clean_output = output_text.strip()

    if "```json" in clean_output:
        clean_output = clean_output.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in clean_output:
        clean_output = clean_output.split("```", 1)[1].split("```", 1)[0].strip()

    try:
        return json.loads(clean_output)
    except json.JSONDecodeError:
        return {"raw_model_output": output_text}


def summarise_with_nova(topic: str, articles: list) -> dict:
    article_text = "\n\n".join(
        [
            f"Title: {article.get('title', '')}\n"
            f"Description: {article.get('description', '')}\n"
            f"Source: {article.get('source', {}).get('name', '')}\n"
            f"URL: {article.get('url', '')}"
            for article in articles
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

    return parse_model_json(output_text)

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
                            "title": article.get("title"),
                            "source": article.get("source", {}).get("name"),
                            "url": article.get("url"),
                        }
                        for article in articles
                    ],
                }
            ),
        }

    except Exception as error:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(error)}),
        }
