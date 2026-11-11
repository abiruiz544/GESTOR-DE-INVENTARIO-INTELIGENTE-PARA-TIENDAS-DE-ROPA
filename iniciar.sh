#!/usr/bin/env bash
set -e
[ -f .env ] || cp .env.example .env
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
