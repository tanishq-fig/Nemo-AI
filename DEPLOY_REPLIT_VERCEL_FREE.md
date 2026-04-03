# Free Deployment Without a Card: Replit + Vercel

This is the easiest no-card path if Hugging Face signup is blocked.

- Frontend: Vercel free
- Backend: Replit free

## What this repo now contains

- [requirements.txt](requirements.txt) - Replit-friendly backend dependencies
- [.replit](.replit) - Run command for Replit
- [replit.nix](replit.nix) - Python runtime definition
- [frontend/vercel.json](frontend/vercel.json) - SPA rewrites for Vercel

## 1) Deploy backend on Replit

1. Create a free Replit account.
2. Import this GitHub repo.
3. Replit should detect the Python config files in the repo root.
4. In Replit, run the app with the provided run command:
   - `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. If Replit asks to install dependencies, it will read [requirements.txt](requirements.txt).
6. Open the deployed backend URL.
7. Check health endpoint:
   - `/health`

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
