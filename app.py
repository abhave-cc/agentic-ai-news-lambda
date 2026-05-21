import json
import os
import urllib.parse
import urllib.request


def lambda_handler(event, context):
    query = event.get("query", "artificial intelligence")

    api_key = os.environ.get("GNEWS_API_KEY")
    if not api_key:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Missing GNEWS_API_KEY environment variable"
            })
        }

    encoded_query = urllib.parse.quote(query)

    url = (
        "https://gnews.io/api/v4/search"
        f"?q={encoded_query}"
        "&lang=en"
        "&country=gb"
        "&max=5"
        f"&apikey={api_key}"
    )

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        articles = data.get("articles", [])

        results = [
            {
                "title": article.get("title"),
                "source": article.get("source", {}).get("name"),
                "url": article.get("url")
            }
            for article in articles
        ]

        return {
            "statusCode": 200,
            "body": json.dumps({
                "query": query,
                "count": len(results),
                "articles": results
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            })
        }
