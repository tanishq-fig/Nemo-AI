#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and fill production values first."
  exit 1
fi

required=(SECRET_KEY CORS_ORIGINS VITE_API_URL APP_DOMAIN API_DOMAIN ACME_EMAIL)
for key in "${required[@]}"; do
  if ! grep -q "^${key}=" .env; then
    echo "ERROR: Missing ${key} in .env"
    exit 1
  fi
done

echo "Bringing up production stack..."
docker compose -f docker-compose.prod.yml up -d --build

echo "Running one-time data initialization..."
docker compose -f docker-compose.prod.yml exec -T backend python ingest.py || true
docker compose -f docker-compose.prod.yml exec -T backend python build_index.py || true
docker compose -f docker-compose.prod.yml exec -T backend python seed.py || true

echo "Deployment complete."
docker compose -f docker-compose.prod.yml ps
