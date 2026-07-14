# Agentic News Legacy EC2 Deployment

## Overview

This branch represents the application running as a traditional long-lived Python web application on a virtual machine.

## Runtime

- Ubuntu Linux virtual machine
- Python 3
- Flask
- Gunicorn
- systemd
- TCP port 8000

## Application entry point

The EC2 web application is started with:

```bash
gunicorn --bind 0.0.0.0:8000 web_app:app
```

## Required environment variables

- AWS_REGION
- BEDROCK_REGION
- BEDROCK_MODEL_ID
- GNEWS_SECRET_NAME
- PORT
- LOG_LEVEL

## AWS dependencies

- Amazon Bedrock
- AWS Secrets Manager
- Optional Amazon S3 RAG artefacts

## Manual deployment process

1. Provision an Ubuntu virtual machine.
2. Install Python and Git.
3. Clone this repository.
4. Create a Python virtual environment.
5. Install `requirements.txt`.
6. Configure environment variables.
7. Start Gunicorn.
8. Configure systemd for automatic restart.

## Target modernisation state

Use AWS Transform to containerise the application and deploy it to Amazon ECS Fargate.
