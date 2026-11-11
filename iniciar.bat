@echo off
if not exist .env copy .env.example .env
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
pip install -q -r requirements.txt
start http://127.0.0.1:8000
uvicorn app.main:app --host 127.0.0.1 --port 8000
