# Free Deployment Without Card

This route avoids Oracle and Render billing setup.

- Frontend: Vercel (free hobby)
- Backend: Hugging Face Spaces Docker (free CPU)

## Fastest path (automated from your machine)

Use [deploy_free.ps1](deploy_free.ps1) after setting two tokens.

PowerShell:

```powershell
$env:HF_TOKEN="hf_xxx"
$env:VERCEL_TOKEN="vercel_xxx"
./deploy_free.ps1 -HfSpaceId "yourname/argo-backend"
```

What it does:

- uploads backend bundle to Hugging Face Space via [scripts/deploy_free_backend.py](scripts/deploy_free_backend.py)
- deploys frontend to Vercel with VITE_API_URL pointing at your hf.space backend

## 1) Deploy backend on Hugging Face Spaces (free)

1. Create a free Hugging Face account.
2. Click New Space.
3. Choose:
   - SDK: Docker
   - Visibility: Public (free)
4. In the new Space repo, upload the full contents of [backend](backend), but use:
   - [backend/Dockerfile.free](backend/Dockerfile.free) renamed to Dockerfile
   - [backend/requirements_free.txt](backend/requirements_free.txt) renamed to requirements.txt
5. In Space Settings, add Variables:
   - CORS_ORIGINS=https://your-vercel-app.vercel.app
   - SECRET_KEY=any-long-random-string
   - OPENAI_API_KEY=optional
   - GEMINI_API_KEY=optional
6. Let the Space build and start.
7. Copy backend URL, example:
   - https://your-space-name.hf.space
8. Check backend health:
   - https://your-space-name.hf.space/health

Notes:
- Free Spaces sleep when idle; first request may be slow.
- This free backend mode skips FAISS vector search automatically if unavailable.

## 2) Deploy frontend on Vercel (free)

1. Create a free Vercel account.
2. Import GitHub repo.
3. Set Project Root Directory to frontend.
4. Framework preset: Vite.
5. Add env var:
   - VITE_API_URL=https://your-space-name.hf.space
6. Deploy.

Optional: [frontend/vercel.json](frontend/vercel.json) is already included for SPA rewrites.

## 3) Verify

1. Open your Vercel URL.
2. Open browser devtools network and ensure API calls target your hf.space URL.
3. Check backend health URL directly.

## 4) If CORS error appears

Update Hugging Face variable CORS_ORIGINS to your exact Vercel origin, for example:

- https://myapp.vercel.app

Then restart the Space.
