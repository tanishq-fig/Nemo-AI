$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Write-Error "ERROR: .env not found. Copy .env.example to .env and fill production values first."
}

$envText = Get-Content .env -Raw
$required = @("SECRET_KEY", "CORS_ORIGINS", "VITE_API_URL", "APP_DOMAIN", "API_DOMAIN", "ACME_EMAIL")

foreach ($key in $required) {
    if ($envText -notmatch "(?m)^$key=") {
        Write-Error "ERROR: Missing $key in .env"
    }
}

Write-Host "Bringing up production stack..."
docker compose -f docker-compose.prod.yml up -d --build

Write-Host "Running one-time data initialization..."
docker compose -f docker-compose.prod.yml exec -T backend python ingest.py
if ($LASTEXITCODE -ne 0) { Write-Warning "ingest.py exited non-zero; continuing" }
docker compose -f docker-compose.prod.yml exec -T backend python build_index.py
if ($LASTEXITCODE -ne 0) { Write-Warning "build_index.py exited non-zero; continuing" }
docker compose -f docker-compose.prod.yml exec -T backend python seed.py
if ($LASTEXITCODE -ne 0) { Write-Warning "seed.py exited non-zero; continuing" }

Write-Host "Deployment complete."
docker compose -f docker-compose.prod.yml ps
