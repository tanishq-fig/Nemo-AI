# Alternate Deployment (No Docker): Render Blueprint

Use this method if local Docker Desktop is unstable. Render builds and runs everything in the cloud directly from your Git repo.

## What this deploys

- Managed PostgreSQL database
- FastAPI backend service
- Static React frontend service

Deployment config is in [render.yaml](render.yaml).

## Steps

1. Push current branch to your Git provider.
2. Sign in to Render and choose New > Blueprint.
3. Select your repository.
4. Render detects [render.yaml](render.yaml) and shows 3 resources:
   - argo-postgres
   - argo-backend
   - argo-frontend
5. Set required manual environment values before deploy:
   - For argo-backend:
     - CORS_ORIGINS = https://<your-frontend-domain>
   - For argo-frontend:
     - VITE_API_URL = https://<your-backend-domain>
   - Optional keys on backend:
     - OPENAI_API_KEY
     - GEMINI_API_KEY
6. Deploy blueprint.
7. After backend is live, run one-time data initialization from Render Shell for argo-backend:
   - python ingest.py
   - python build_index.py
   - python seed.py
8. Open frontend URL and test:
   - / loads app
   - login works
   - backend health endpoint returns healthy

## Post-deploy checks

- Backend health: https://<your-backend-domain>/health
- Frontend can call API without CORS errors
- Chat endpoint returns response
- Data endpoints return records

## Notes

- This path avoids local Docker entirely.
- Backend start command is managed in [render.yaml](render.yaml).
- Frontend SPA routing is handled by rewrite rule in [render.yaml](render.yaml).
