# Deployment Guide - ARGO Ocean Intelligence Platform

This repo now includes two Docker deployment modes:

- Local stack for testing: [docker-compose.yml](docker-compose.yml)
- Production stack with HTTPS reverse proxy: [docker-compose.prod.yml](docker-compose.prod.yml)

## 1) Prerequisites

- Docker Engine 24+
- Docker Compose plugin (docker compose)
- Public DNS records for your domains (production only)

Check:

```bash
docker --version
docker compose version
```

## 2) Configure environment

Copy [.env.example](.env.example) to `.env` and set real values.

Required for production:

- SECRET_KEY
- CORS_ORIGINS
- VITE_API_URL
- APP_DOMAIN
- API_DOMAIN
- ACME_EMAIL

Example production values:

```env
POSTGRES_USER=argo_user
POSTGRES_PASSWORD=use-a-strong-password
POSTGRES_DB=argo_db

SECRET_KEY=replace-with-a-long-random-secret-at-least-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

GEMINI_API_KEY=
OPENAI_API_KEY=

CORS_ORIGINS=https://app.example.com
VITE_API_URL=https://api.example.com
APP_DOMAIN=app.example.com
API_DOMAIN=api.example.com
ACME_EMAIL=admin@example.com
```

## 3) Local Docker deployment

Use this on your machine for validation.

```bash
docker compose up -d --build
```

Open:

- Frontend: http://localhost:5173
- API health: http://localhost:8000/health

One-time data init (if needed):

```bash
docker compose exec backend python ingest.py
docker compose exec backend python build_index.py
docker compose exec backend python seed.py
```

## 4) Production deployment (HTTPS)

Use this on a Linux server or VM with ports 80/443 open.

### Linux/macOS

```bash
chmod +x deploy_prod.sh
./deploy_prod.sh
```

### Windows PowerShell

```powershell
./deploy_prod.ps1
```

This uses [docker-compose.prod.yml](docker-compose.prod.yml) + [Caddyfile](Caddyfile) to:

- serve frontend at https://APP_DOMAIN
- serve backend at https://API_DOMAIN
- auto-issue TLS certificates via Let's Encrypt

## 5) Verify deployment

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs --tail=100 caddy
docker compose -f docker-compose.prod.yml logs --tail=100 backend
```

API check:

```bash
curl https://api.example.com/health
```

## 6) Update and rollback

Update:

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Rollback (to previous commit):

```bash
git checkout <previous-commit>
docker compose -f docker-compose.prod.yml up -d --build
```

## 7) Backup and restore Postgres

Backup:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```

Restore:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U "$POSTGRES_USER" "$POSTGRES_DB" < backup.sql
```

## Notes

- In production mode, database and app containers are not exposed directly to the public internet.
- Only Caddy binds host ports 80/443.
- If your DNS is not pointed to the server yet, TLS issuance will fail until DNS is correct.
