# Agentic News Legacy EC2 Deployment

## Overview

This branch represents the application running as a traditional
long-lived Python web application on a virtual machine.

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
