# Free Deployment Without a Card: Replit + Vercel

This is the easiest no-card path if Hugging Face signup is blocked.

- Frontend: Vercel free
- Backend: Replit free

## What this repo now contains

- [requirements.txt](requirements.txt) - Replit-friendly backend dependencies
- [.replit](.replit) - Run command for Replit
- [frontend/vercel.json](frontend/vercel.json) - SPA rewrites for Vercel

## 1) Deploy backend on Replit

1. Create a free Replit account.
2. Import this GitHub repo.
3. If Replit shows recovery mode, click **Recover original configuration files** once, then re-import the GitHub repo or refresh the workspace.
4. Replit should detect the Python config files in the repo root.
5. In Replit, click Run. The repo now uses [replit_run.sh](replit_run.sh) to install dependencies and start uvicorn automatically.
6. If Replit asks to install dependencies, it will read [requirements.txt](requirements.txt).
7. Open the deployed backend URL.
8. Check health endpoint:
   - `/health`

You should see logs ending with a uvicorn line similar to:

- `Uvicorn running on http://0.0.0.0:3000` (or the provided `PORT`)

Notes:
- This backend uses SQLite by default, so no database card or external DB is needed.
- Heavy scientific ingestion packages are intentionally excluded from the free requirements.
- The app still works with fallback RAG and local SQL mode.

## 2) Deploy frontend on Vercel

1. Create/import the same GitHub repo into Vercel.
2. Set root directory to `frontend`.
3. Set env var:
   - `VITE_API_URL=<your Replit backend URL>`
4. Deploy.

## 3) If you need to refresh data later

Use the backend routes or local scripts only on a machine with the scientific dependencies installed. The free Replit backend is optimized for serving the app, not heavy batch ingestion.

## 4) Verify

1. Open the Vercel URL.
2. Log in or register.
3. Confirm API requests go to Replit backend.
4. Confirm `/health` returns healthy JSON.
