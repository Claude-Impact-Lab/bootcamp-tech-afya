#!/usr/bin/env bash
cd "$(dirname "$0")"

if command -v fuser >/dev/null 2>&1; then
  echo "Stopping server on port 8000..."
  fuser -k 8000/tcp || true
elif command -v lsof >/dev/null 2>&1; then
  echo "Stopping server on port 8000..."
  lsof -ti tcp:8000 | xargs -r kill
elif command -v pkill >/dev/null 2>&1; then
  echo "Stopping uvicorn process..."
  pkill -f 'uvicorn app.main:app' || true
else
  echo "No supported kill tool found. Use pkill, fuser, or lsof." >&2
  exit 1
fi

echo "Server stopped."
