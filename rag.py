import json
import math
import os

import boto3


AWS_REGION = os.environ.get("BEDROCK_REGION", "eu-west-2")
RAG_BUCKET = os.environ.get("RAG_BUCKET")
INDEX_KEY = os.environ.get("INDEX_KEY", "index/rag_index.json")
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0",
)

s3 = boto3.client("s3", region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def load_rag_index():
    response = s3.get_object(
        Bucket=RAG_BUCKET,
        Key=INDEX_KEY,
    )

    body = response["Body"].read().decode("utf-8")
    return json.loads(body)


def generate_embedding(text: str):
    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps({"inputText": text}),
        accept="application/json",
        contentType="application/json",
    )

    response_body = json.loads(response["body"].read())
    return response_body["embedding"]


def cosine_similarity(vec1, vec2):
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0

    return dot_product / (magnitude1 * magnitude2)


def retrieve_context(query: str, top_k: int = 3):
    query_embedding = generate_embedding(query)
    index = load_rag_index()

    scored = []

    for item in index:
        similarity = cosine_similarity(
            query_embedding,
            item["embedding"],
        )

        scored.append(
            {
                "score": similarity,
                "text": item["text"],
                "document": item["document"],
            }
        )

    scored.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    return scored[:top_k]
