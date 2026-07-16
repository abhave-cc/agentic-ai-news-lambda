import json
import logging
import os
from typing import Any

from flask import Flask, jsonify, render_template, request

from app import handler


app = Flask(__name__)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)


@app.get("/")
def home():
    """
    Render the simple browser interface for the EC2-hosted application.
    """

    return render_template("index.html")


@app.get("/health")
def health():
    """
    Health endpoint for EC2 testing and later ECS health checks.
    """

    return jsonify(
        {
            "status": "healthy",
            "application": "agentic-news",
            "deployment": "legacy-ec2",
        }
    )


@app.post("/api/research")
def research() -> tuple[Any, int] | Any:
    """
    Convert a normal HTTP request into the event format expected by
    the existing Lambda handler.
    """

    request_body = request.get_json(silent=True) or {}

    topic = str(request_body.get("topic", "")).strip()

    if not topic:
        return jsonify({"error": "topic is required"}), 400

    try:
        max_results = int(request_body.get("max_results", 5))
    except (TypeError, ValueError):
        return jsonify(
            {
                "error": "max_results must be a number",
            }
        ), 400

    max_results = max(1, min(max_results, 10))

    lambda_event = {
        "body": json.dumps(
            {
                "topic": topic,
                "max_results": max_results,
            }
        )
    }

    try:
        lambda_response = handler(lambda_event, None)

        status_code = int(
            lambda_response.get("statusCode", 500)
        )

        response_body = lambda_response.get("body", "{}")

        if isinstance(response_body, str):
            try:
                parsed_body = json.loads(response_body)
            except json.JSONDecodeError:
                parsed_body = {
                    "raw_response": response_body,
                }
        else:
            parsed_body = response_body

        return jsonify(parsed_body), status_code

    except Exception as error:
        logger.exception(
            "Unexpected error while running Agentic News"
        )

        return jsonify(
            {
                "error": str(error),
            }
        ), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        debug=False,
    )
