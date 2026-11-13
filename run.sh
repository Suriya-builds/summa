#!/usr/bin/env bash
# One-command local start: installs dependencies on first run, builds the frontend, starts the server.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -d backend/.venv ]; then
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q -r backend/requirements.txt
fi
if [ ! -d frontend/node_modules ]; then (cd frontend && npm ci --no-audit --no-fund); fi
(cd frontend && npm run build)
[ -f .env ] || cp .env.example .env
echo "Summa is starting at http://localhost:${PORT:-8000}"
cd backend && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}"
