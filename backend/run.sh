#!/usr/bin/env bash
# venv + deps then flask
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
# -q keeps the install noise down on every restart
python -m pip install -r requirements.txt -q
# exec so ctrl+c hits flask cleanly
exec python app.py
