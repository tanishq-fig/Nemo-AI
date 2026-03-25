# 🚀 Deployment Guide - ARGO Ocean Intelligence Platform

## Table of Contents
1. [Production Deployment Checklist](#production-deployment-checklist)
2. [Environment Configuration](#environment-configuration)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Security Hardening](#security-hardening)
7. [Monitoring & Logging](#monitoring--logging)
8. [Backup & Recovery](#backup--recovery)

---

## Production Deployment Checklist

### Pre-Deployment
- [ ] Update all dependencies to latest stable versions
- [ ] Run security audit (`npm audit`, `pip-audit`)
- [ ] Set strong SECRET_KEY in production
- [ ] Configure production database (PostgreSQL)
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Set up environment variables securely
- [ ] Create backup strategy
- [ ] Set up monitoring and logging
- [ ] Load test the application
- [ ] Review and enable rate limiting

### Post-Deployment
- [ ] Verify all API endpoints
- [ ] Test authentication flows
- [ ] Verify database connections
- [ ] Check CORS configuration
- [ ] Test RAG pipeline with real queries
- [ ] Monitor error logs for 24 hours
- [ ] Set up automated backups
- [ ] Configure CDN for frontend assets
- [ ] Set up uptime monitoring
- [ ] Document incident response procedures

---

## Environment Configuration

### Backend `.env` (Production)

```bash
# Database
DATABASE_URL=postgresql://username:password@your-db-host:5432/argo_production
POSTGRES_USER=argo_admin
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=argo_production

# JWT Authentication
SECRET_KEY=your-super-secret-key-min-32-chars-here-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI API (Optional)
OPENAI_API_KEY=sk-your-production-api-key-here

# Application Settings
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### Frontend `.env.production`

```bash
VITE_API_URL=https://api.yourdomain.com
VITE_ENVIRONMENT=production
```

---

## Database Setup

### 1. PostgreSQL with PostGIS (Production)

#### Using Managed Service (Recommended)
- **AWS RDS**: PostgreSQL with PostGIS extension
- **Google Cloud SQL**: PostgreSQL with extensions
- **Heroku Postgres**: PostGIS addon
- **DigitalOcean Managed Database**: PostgreSQL cluster

#### Self-Hosted Setup
```bash
# Install PostgreSQL 15+
sudo apt update
sudo apt install postgresql-15 postgresql-contrib postgresql-15-postgis-3

# Enable PostGIS extension
sudo -u postgres psql argo_production
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

### 2. Database Migrations
```bash
cd backend
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Create tables
python -c "from database import init_db; init_db()"

# Seed demo data
python seed.py
```

### 3. Database Security
```sql
-- Create read-only user for analytics
CREATE USER argo_readonly WITH PASSWORD 'readonly_password';
GRANT CONNECT ON DATABASE argo_production TO argo_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO argo_readonly;

-- Revoke public access
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO argo_admin;
```

---

## Backend Deployment

### Option 1: Docker (Recommended)

#### Create `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 argo && chown -R argo:argo /app
USER argo

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### Build and Run
```bash
cd backend
docker build -t argo-backend:latest .
docker run -d \
  --name argo-backend \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  argo-backend:latest
```

### Option 2: Systemd Service (Linux)

#### Create `/etc/systemd/system/argo-backend.service`
```ini
[Unit]
Description=ARGO Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=argo
WorkingDirectory=/opt/argo/backend
Environment="PATH=/opt/argo/backend/venv/bin"
EnvironmentFile=/opt/argo/backend/.env
ExecStart=/opt/argo/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable argo-backend
sudo systemctl start argo-backend
sudo systemctl status argo-backend
```

### Option 3: Cloud Platforms

#### Heroku
```bash
# Install Heroku CLI
heroku login
heroku create argo-backend

# Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# Deploy
git push heroku main
```

#### AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 argo-backend
eb create argo-production

# Deploy
eb deploy
```

#### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/argo-backend
gcloud run deploy argo-backend \
  --image gcr.io/PROJECT_ID/argo-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

---

## Frontend Deployment

### Option 1: Vercel (Recommended for React)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from frontend directory
cd frontend
vercel --prod
```

#### `vercel.json`
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "env": {
    "VITE_API_URL": "https://api.yourdomain.com"
  }
}
```

### Option 2: Netlify

```bash
# Install Netlify CLI
npm install -g netlify-cli

# Deploy
cd frontend
npm run build
netlify deploy --prod --dir=dist
```

#### `netlify.toml`
```toml
[build]
  command = "npm run build"
  publish = "dist"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

### Option 3: Static Hosting (S3 + CloudFront)

```bash
# Build
cd frontend
npm run build

# Deploy to S3
aws s3 sync dist/ s3://your-bucket-name --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id YOUR_DIST_ID \
  --paths "/*"
```

---

## Security Hardening

### 1. Backend Security

#### Rate Limiting (Add to `backend/main.py`)
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/data")
@limiter.limit("100/minute")
async def get_data(request: Request):
    # Your endpoint
    pass
```

#### HTTPS Enforcement
```python
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

if config.ENVIRONMENT == "production":
    app.add_middleware(HTTPSRedirectMiddleware)
```

#### Security Headers
```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["yourdomain.com", "*.yourdomain.com"]
)
```

### 2. Database Security
- Use strong passwords (min 20 characters)
- Enable SSL connections
- Configure firewall rules (only backend IP)
- Regular security patches
- Encrypted backups

### 3. API Key Security
- Never commit API keys to git
- Use environment variables
- Rotate keys regularly
- Monitor API usage
- Set usage limits

---

## Monitoring & Logging

### 1. Application Logging

#### Backend (Python)
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'logs/argo.log',
    maxBytes=10485760,  # 10MB
    backupCount=5
)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler]
)
```

### 2. Error Tracking
- **Sentry**: Real-time error monitoring
- **Rollbar**: Exception tracking
- **LogRocket**: Session replay

### 3. Performance Monitoring
- **New Relic**: APM monitoring
- **Datadog**: Infrastructure monitoring
- **Prometheus + Grafana**: Metrics dashboard

### 4. Uptime Monitoring
- **UptimeRobot**: Free uptime checks
- **Pingdom**: Detailed performance
- **StatusCake**: Global monitoring

---

## Backup & Recovery

### 1. Database Backups

#### Automated Daily Backups
```bash
#!/bin/bash
# /usr/local/bin/backup-argo.sh

BACKUP_DIR="/backups/argo"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="argo_backup_${TIMESTAMP}.sql"

pg_dump -U argo_admin -h localhost argo_production > "${BACKUP_DIR}/${FILENAME}"
gzip "${BACKUP_DIR}/${FILENAME}"

# Upload to S3
aws s3 cp "${BACKUP_DIR}/${FILENAME}.gz" s3://your-backup-bucket/

# Delete local backups older than 7 days
find ${BACKUP_DIR} -name "*.sql.gz" -mtime +7 -delete
```

#### Cron Job
```bash
# Run daily at 2 AM
0 2 * * * /usr/local/bin/backup-argo.sh
```

### 2. Recovery Procedure
```bash
# Download latest backup
aws s3 cp s3://your-backup-bucket/latest.sql.gz .

# Restore database
gunzip latest.sql.gz
psql -U argo_admin -h localhost argo_production < latest.sql
```

### 3. Disaster Recovery Checklist
1. Restore database from latest backup
2. Redeploy backend from git repository
3. Rebuild frontend and redeploy
4. Verify all services operational
5. Check data integrity
6. Notify users of any downtime

---

## Performance Optimization

### 1. Backend Optimization
- Use connection pooling (SQLAlchemy)
- Enable response caching (Redis)
- Optimize database queries (indexes)
- Use CDN for static assets
- Enable gzip compression

### 2. Frontend Optimization
- Code splitting (lazy loading)
- Image optimization
- Asset compression
- CDN for assets
- Service worker caching

### 3. Database Optimization
```sql
-- Create indexes for common queries
CREATE INDEX idx_profiles_temp ON argo_profiles(temperature);
CREATE INDEX idx_profiles_location ON argo_profiles USING GIST(location);
CREATE INDEX idx_chat_user ON chat_history(user_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM argo_profiles WHERE temperature > 20;
```

---

## Health Checks

### Backend Health Endpoint
```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for load balancers."""
    try:
        # Check database connection
        db.execute("SELECT 1")
        
        # Check RAG pipeline
        rag = get_rag_pipeline()
        
        return {
            "status": "healthy",
            "database": "connected",
            "rag": "loaded",
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )
```

---

## Production Checklist

### Before Going Live
- [ ] All environment variables set securely
- [ ] Database backups configured and tested
- [ ] SSL certificates installed and valid
- [ ] CORS configured for production domains
- [ ] Rate limiting enabled
- [ ] Error tracking set up (Sentry)
- [ ] Uptime monitoring configured
- [ ] Load testing completed
- [ ] Security audit performed
- [ ] Documentation reviewed and updated

### After Launch
- [ ] Monitor logs for first 24 hours
- [ ] Verify backup completion
- [ ] Test disaster recovery procedure
- [ ] Set up alerts for errors
- [ ] Document any issues
- [ ] Plan first maintenance window

---

## Support & Maintenance

### Regular Maintenance Tasks
- **Daily**: Review error logs
- **Weekly**: Check performance metrics, review backups
- **Monthly**: Security updates, dependency updates
- **Quarterly**: Security audit, load testing
- **Annually**: Disaster recovery drill

### Incident Response
1. Identify issue from monitoring alerts
2. Check logs for error details
3. Apply hotfix if critical
4. Schedule maintenance window for non-critical
5. Document incident and resolution
6. Review and improve monitoring

---

## Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Vite Deployment](https://vitejs.dev/guide/static-deploy.html)
- [PostgreSQL Security](https://www.postgresql.org/docs/current/security.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)

**Deployment Questions?** Check logs, review configuration, test locally first!
