# Oracle Always Free Deployment

This path avoids Render and runs on Oracle Cloud Always Free using your existing production stack.

Uses:

- [docker-compose.prod.yml](docker-compose.prod.yml)
- [Caddyfile](Caddyfile)
- [deploy_prod.sh](deploy_prod.sh)
- [oracle_vm_setup.sh](oracle_vm_setup.sh)
- [oracle_deploy.sh](oracle_deploy.sh)

## 1. Create Always Free VM

Create an Ubuntu 22.04 VM in Oracle Cloud Always Free.

Recommended:

- Shape: Ampere A1 (Always Free)
- At least 2 OCPU / 8 GB RAM
- Assign a public IPv4

## 2. Open network ports

In Oracle VCN security rules, allow inbound:

- 22 (SSH)
- 80 (HTTP)
- 443 (HTTPS)

## 3. Point DNS

Create these A records to your VM public IP:

- app.yourdomain.com
- api.yourdomain.com

## 4. SSH and bootstrap server

SSH into VM, then run:

```bash
curl -fsSL https://raw.githubusercontent.com/tanishq-fig/Nemo-AI/main/oracle_vm_setup.sh -o oracle_vm_setup.sh
chmod +x oracle_vm_setup.sh
./oracle_vm_setup.sh
```

Log out and back in once after script completes.

## 5. Deploy app

Run:

```bash
curl -fsSL https://raw.githubusercontent.com/tanishq-fig/Nemo-AI/main/oracle_deploy.sh -o oracle_deploy.sh
chmod +x oracle_deploy.sh
./oracle_deploy.sh
```

On first run it creates .env then exits.

## 6. Configure .env

Edit $HOME/Nemo-AI/.env and set real values:

```env
POSTGRES_USER=argo_user
POSTGRES_PASSWORD=strong-db-password
POSTGRES_DB=argo_db

SECRET_KEY=replace-with-long-random-secret-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

CORS_ORIGINS=https://app.yourdomain.com
VITE_API_URL=https://api.yourdomain.com
APP_DOMAIN=app.yourdomain.com
API_DOMAIN=api.yourdomain.com
ACME_EMAIL=you@yourdomain.com

OPENAI_API_KEY=
GEMINI_API_KEY=
```

Run deployment again:

```bash
cd $HOME/Nemo-AI
./oracle_deploy.sh
```

## 7. Verify

```bash
docker compose -f docker-compose.prod.yml ps
curl https://api.yourdomain.com/health
```

Expected:

- Frontend works at https://app.yourdomain.com
- API responds at https://api.yourdomain.com/health

## 8. Updates

```bash
cd $HOME/Nemo-AI
./oracle_deploy.sh
```

## 9. Backups

```bash
cd $HOME/Nemo-AI
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup.sql
```
