import json
import os
from functools import lru_cache

import boto3
import requests


@lru_cache(maxsize=1)
def get_gnews_api_key() -> str:
    secret_name = os.environ.get("GNEWS_SECRET_NAME", "agentic-ai/gnews")
    region_name = os.environ.get("AWS_REGION", "eu-west-2")

    client = boto3.client("secretsmanager", region_name=region_name)
    response = client.get_secret_value(SecretId=secret_name)

    secret = json.loads(response["SecretString"])
    return secret["GNEWS_API_KEY"]


def search_gnews(query: str, api_key: str, max_results: int = 5) -> dict:
    response = requests.get(
        "https://gnews.io/api/v4/search",
        params={
            "q": query,
            "lang": "en",
            "country": "gb",
            "max": max_results,
            "apikey": api_key,
        },
        timeout=10,
    )

    response.raise_for_status()
    return response.json()


def lambda_handler(event, context):
    query = event.get("query", "artificial intelligence")

    try:
        api_key = get_gnews_api_key()
        data = search_gnews(query, api_key)

        articles = data.get("articles", [])

        results = [
            {
                "title": article.get("title"),
                "source": article.get("source", {}).get("name"),
                "url": article.get("url"),
                "publishedAt": article.get("publishedAt"),
            }
            for article in articles
        ]

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "query": query,
                    "count": len(results),
                    "articles": results,
                }
            ),
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
