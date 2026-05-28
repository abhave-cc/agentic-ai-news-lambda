import json
import os
import uuid

import boto3


AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "eu-west-2")
RAG_BUCKET = os.environ.get("RAG_BUCKET")
DOCS_PREFIX = os.environ.get("DOCS_PREFIX", "docs/")
INDEX_KEY = os.environ.get("INDEX_KEY", "index/rag_index.json")
EMBEDDING_MODEL_ID = os.environ.get(
    "EMBEDDING_MODEL_ID",
    "amazon.titan-embed-text-v2:0",
)

s3 = boto3.client("s3", region_name=AWS_REGION)
bedrock = boto3.client("bedrock-runtime", region_name=AWS_REGION)


def list_documents():
    response = s3.list_objects_v2(
        Bucket=RAG_BUCKET,
        Prefix=DOCS_PREFIX,
    )

    objects = response.get("Contents", [])

    return [
        obj["Key"]
        for obj in objects
        if obj["Key"].endswith(".md")
        or obj["Key"].endswith(".txt")
    ]


def load_document(key: str) -> str:
    response = s3.get_object(Bucket=RAG_BUCKET, Key=key)
    return response["Body"].read().decode("utf-8")


def chunk_text(text: str, chunk_size: int = 1200):
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]

        if len(chunk.strip()) > 100:
            chunks.append(chunk)

    return chunks


def generate_embedding(text: str):
    response = bedrock.invoke_model(
        modelId=EMBEDDING_MODEL_ID,
        body=json.dumps(
            {
                "inputText": text
            }
        ),
    )

    response_body = json.loads(response["body"].read())

    return response_body["embedding"]


def build_index():
    index = []

    documents = list_documents()

    print(f"Found {len(documents)} documents")

    for doc_key in documents:
        print(f"Processing {doc_key}")

        text = load_document(doc_key)

        chunks = chunk_text(text)

        print(f"Created {len(chunks)} chunks")

        for chunk in chunks:
            embedding = generate_embedding(chunk)

            index.append(
                {
                    "id": str(uuid.uuid4()),
                    "document": doc_key,
                    "text": chunk,
                    "embedding": embedding,
                }
            )

    return index


def upload_index(index):
    body = json.dumps(index)

    s3.put_object(
        Bucket=RAG_BUCKET,
        Key=INDEX_KEY,
        Body=body.encode("utf-8"),
        ContentType="application/json",
    )

    print(f"Uploaded index with {len(index)} chunks")


if __name__ == "__main__":
    rag_index = build_index()
    upload_index(rag_index)
