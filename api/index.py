import os
import sys
from pathlib import Path
import traceback
from fastapi import FastAPI

# Ensure backend package imports resolve when running as a Vercel function.
ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Use ephemeral writable storage on serverless runtime if no DB URL is provided.
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/argo_data.db")

app: FastAPI

try:
    from main import app as backend_app
    app = backend_app
except Exception as exc:
    app = FastAPI(title="Vercel Backend Bootstrap Error")
    _err = str(exc)
    _trace = traceback.format_exc()

    @app.get("/health")
    async def health_error():
        return {
            "status": "bootstrap_error",
            "error": _err,
            "trace": _trace,
        }

    @app.get("/")
    async def root_error():
        return {
            "message": "Backend failed to initialize",
            "error": _err,
        }
