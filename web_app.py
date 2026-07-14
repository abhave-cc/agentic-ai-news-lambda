import json
import logging
import os
from typing import Any

from flask import Flask, jsonify, request

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
    Simple browser interface for the EC2-hosted version.
    """

    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8">
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1"
        >

        <title>Agentic News - Legacy EC2</title>

        <style>
          body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
            line-height: 1.5;
          }

          input {
            width: 70%;
            padding: 10px;
            font-size: 16px;
          }

          button {
            padding: 10px 18px;
            font-size: 16px;
            cursor: pointer;
          }

          pre {
            background: #f4f4f4;
            border: 1px solid #dddddd;
            padding: 16px;
            overflow-x: auto;
            white-space: pre-wrap;
          }

          .subtitle {
            color: #555555;
          }
        </style>
      </head>

      <body>
        <h1>Agentic News</h1>

        <p class="subtitle">
          Legacy EC2-hosted demonstration version
        </p>

        <p>
          Enter a topic to search recent news and internal RAG content.
        </p>

        <input
          id="topic"
          type="text"
          value="AWS container modernisation"
        >

        <button onclick="runResearch()">
          Research
        </button>

        <pre id="result">
Enter a topic and select Research.
        </pre>

        <script>
          async function runResearch() {
            const topicInput = document.getElementById("topic");
            const resultElement = document.getElementById("result");

            const topic = topicInput.value.trim();

            if (!topic) {
              resultElement.textContent = "Please enter a topic.";
              return;
            }

            resultElement.textContent = "Researching...";

            try {
              const response = await fetch("/api/research", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json"
                },
                body: JSON.stringify({
                  topic: topic,
                  max_results: 5
                })
              });

              const data = await response.json();

              if (!response.ok) {
                throw new Error(
                  data.error || "The research request failed."
                );
              }

              resultElement.textContent =
                JSON.stringify(data, null, 2);

            } catch (error) {
              resultElement.textContent =
                "Error: " + error.message;
            }
          }
        </script>
      </body>
    </html>
    """


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
