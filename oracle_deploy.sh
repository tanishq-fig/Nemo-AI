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

env_get() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" .env | tail -n 1 || true)"
  echo "${line#*=}"
}

env_set() {
  local key="$1"
  local value="$2"
  if grep -q -E "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${value}|" .env
  else
    echo "${key}=${value}" >> .env
  fi
}

is_placeholder() {
  local value="$1"
  case "$value" in
    ""|"app.example.com"|"api.example.com"|"admin@example.com"|"your-secret-key-change-in-production"|"replace-with-long-random-secret-min-32-chars"|"http://localhost:8000"|"http://localhost:5173,http://127.0.0.1:5173")
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    tr -dc 'A-Za-z0-9' </dev/urandom | head -c 64
    echo
  fi
}

prompt_value() {
  local prompt="$1"
  local default_value="$2"
  local user_value
  read -r -p "$prompt [$default_value]: " user_value
  echo "${user_value:-$default_value}"
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
fi

# Ensure database defaults exist.
env_set POSTGRES_USER "$(env_get POSTGRES_USER || true)"
env_set POSTGRES_PASSWORD "$(env_get POSTGRES_PASSWORD || true)"
env_set POSTGRES_DB "$(env_get POSTGRES_DB || true)"

if [ -z "$(env_get POSTGRES_USER)" ]; then
  env_set POSTGRES_USER "argo_user"
fi
if [ -z "$(env_get POSTGRES_PASSWORD)" ]; then
  env_set POSTGRES_PASSWORD "argo_pass"
fi
if [ -z "$(env_get POSTGRES_DB)" ]; then
  env_set POSTGRES_DB "argo_db"
fi

# Ask for core domain values if missing or placeholders.
app_domain="$(env_get APP_DOMAIN)"
if is_placeholder "$app_domain"; then
  app_domain="$(prompt_value "Enter app domain (no protocol)" "app.example.com")"
  env_set APP_DOMAIN "$app_domain"
fi

api_domain="$(env_get API_DOMAIN)"
if is_placeholder "$api_domain"; then
  api_domain="$(prompt_value "Enter API domain (no protocol)" "api.example.com")"
  env_set API_DOMAIN "$api_domain"
fi

acme_email="$(env_get ACME_EMAIL)"
if is_placeholder "$acme_email"; then
  acme_email="$(prompt_value "Enter ACME/Let's Encrypt email" "admin@example.com")"
  env_set ACME_EMAIL "$acme_email"
fi

# Derive API and CORS defaults from domains if unset.
vite_api_url="$(env_get VITE_API_URL)"
if is_placeholder "$vite_api_url"; then
  env_set VITE_API_URL "https://${api_domain}"
fi

cors_origins="$(env_get CORS_ORIGINS)"
if is_placeholder "$cors_origins"; then
  env_set CORS_ORIGINS "https://${app_domain}"
fi

secret_key="$(env_get SECRET_KEY)"
if is_placeholder "$secret_key"; then
  secret_key="$(generate_secret)"
  env_set SECRET_KEY "$secret_key"
  echo "Generated SECRET_KEY"
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin is unavailable. Verify Docker installation and group permissions."
  exit 1
fi

echo "Starting production stack..."
docker compose -f docker-compose.prod.yml up -d --build

if [ "${FORCE_INIT:-0}" = "1" ] || [ ! -f .deploy_initialized ]; then
  echo "Running one-time data initialization..."
  docker compose -f docker-compose.prod.yml exec -T backend python ingest.py || true
  docker compose -f docker-compose.prod.yml exec -T backend python build_index.py || true
  docker compose -f docker-compose.prod.yml exec -T backend python seed.py || true
  touch .deploy_initialized
else
  echo "Skipping data initialization (already completed)."
  echo "Set FORCE_INIT=1 to run ingest/index/seed again."
fi

echo "Deployment complete"
docker compose -f docker-compose.prod.yml ps
