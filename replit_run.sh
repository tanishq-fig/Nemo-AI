#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

cd backend
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-3000}"
