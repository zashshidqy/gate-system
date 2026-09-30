#!/usr/bin/env bash
# Start Gate Dashboard backend + frontend for local development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

cleanup() {
  trap - EXIT INT TERM
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [[ -n "${FRONTEND_PID:-}" ]] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Preparing backend"
cd "$BACKEND"

if [[ ! -x .venv/bin/python ]]; then
  echo "    Creating virtualenv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if ! python -c "import fastapi, uvicorn, alembic" 2>/dev/null; then
  echo "    Installing Python dependencies..."
  pip install -r requirements.txt
fi

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "    Copied .env.example -> .env (edit JWT_SECRET / serial ports if needed)"
  else
    echo "ERROR: backend/.env is missing and there is no .env.example" >&2
    exit 1
  fi
fi

echo "    Running migrations..."
alembic upgrade head

echo "==> Starting API on 127.0.0.1:8000"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait until /health responds (serial ports may be missing — that is OK)
for i in {1..30}; do
  if curl -sf --connect-timeout 1 http://127.0.0.1:8000/health >/dev/null; then
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "ERROR: backend exited before becoming healthy" >&2
    exit 1
  fi
  sleep 0.5
done

if ! curl -sf --connect-timeout 1 http://127.0.0.1:8000/health >/dev/null; then
  echo "ERROR: backend did not become healthy on 127.0.0.1:8000" >&2
  exit 1
fi

echo "==> Preparing frontend"
cd "$FRONTEND"

if [[ ! -d node_modules ]]; then
  echo "    Installing npm dependencies..."
  npm install
fi

echo "==> Starting Vite on 127.0.0.1:5173"
npm run dev -- --host 127.0.0.1 --port 5173 &
FRONTEND_PID=$!

echo
echo "=============================================="
echo "  Frontend: http://localhost:5173"
echo "  API:      http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo
echo "  Default login (fresh DB only):"
echo "    Username: admin"
echo "    Password: admin1234"
echo "=============================================="
echo
echo "Press Ctrl+C to stop both processes."

wait
