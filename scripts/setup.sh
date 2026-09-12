#!/usr/bin/env bash
# One-shot setup: Python venv + deps, dataset, model training, and Node deps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Backend: virtualenv + requirements"
cd "$ROOT/backend"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
[ -f .env ] || cp .env.example .env

echo "==> Backend: dataset (API if API_KEY is set, otherwise mock)"
.venv/bin/python -m app.fetch_data

echo "==> Backend: train model"
.venv/bin/python -m app.train

echo "==> Frontend: npm install"
cd "$ROOT/frontend"
npm install
[ -f .env ] || cp .env.example .env

echo "==> Root: npm install (concurrently)"
cd "$ROOT"
npm install

echo
echo "Done. Start both servers with:  npm run dev"
echo "  UI:  http://localhost:5173"
echo "  API: http://127.0.0.1:8000/docs"
