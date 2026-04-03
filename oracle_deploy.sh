#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/tanishq-fig/Nemo-AI.git}"
APP_DIR="${APP_DIR:-$HOME/Nemo-AI}"
BRANCH="${BRANCH:-main}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_cmd git
require_cmd docker

if [ ! -d "$APP_DIR/.git" ]; then
  echo "Cloning repository into $APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

echo "Fetching latest code from $BRANCH"
git fetch --all --prune
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
  echo "Edit .env now with real values, then re-run this script."
  exit 1
fi

required=(SECRET_KEY CORS_ORIGINS VITE_API_URL APP_DOMAIN API_DOMAIN ACME_EMAIL)
for key in "${required[@]}"; do
  if ! grep -q "^${key}=" .env; then
    echo "Missing ${key} in .env"
    exit 1
  fi
done

echo "Starting production stack..."
docker compose -f docker-compose.prod.yml up -d --build

echo "Running one-time data initialization..."
docker compose -f docker-compose.prod.yml exec -T backend python ingest.py || true
docker compose -f docker-compose.prod.yml exec -T backend python build_index.py || true
docker compose -f docker-compose.prod.yml exec -T backend python seed.py || true

echo "Deployment complete"
docker compose -f docker-compose.prod.yml ps
