#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

cleanup() {
  # kill both children on exit / ctrl+c
  kill "$BACKEND_PID" "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# backend (flask on 5050 - airplay steals 5000)
cd backend
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install -q -r requirements.txt
.venv/bin/python app.py &
BACKEND_PID=$!
cd ..

# frontend (vite on 5173, proxies /api -> :5050)
cd frontend
# skip install if node_modules already there
if [ ! -d node_modules ]; then
  npm install
fi
npm run dev &
FRONT_PID=$!
cd ..

# brief pause so flask/vite can bind before opening the browser
sleep 3
if command -v open >/dev/null 2>&1; then
  open "http://localhost:5173"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:5173"
fi

echo "backend pid: $BACKEND_PID  frontend pid: $FRONT_PID"
echo "trading strategy backtester: http://localhost:5173"
echo "api: http://127.0.0.1:5050"
echo "press ctrl+c to stop both."
# wait until either child dies (or ctrl+c)
wait $FRONT_PID $BACKEND_PID 2>/dev/null || true
