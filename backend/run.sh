#!/usr/bin/env bash
# one-shot backend launcher: creates .venv if needed, installs deps, runs the api
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
python -m pip install -r requirements.txt -q
exec python app.py
