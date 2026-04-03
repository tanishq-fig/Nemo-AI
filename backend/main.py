"""
FastAPI Main Application
ARGO Oceanographic Intelligence Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager

from config import settings
from database import init_db
from routes import auth_routes, chat_routes, data_routes, visualization_routes, live_routes, api_routes, analytics_routes
from error_handlers import custom_http_exception_handler, validation_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print("=" * 60)
    print("Starting ARGO Intelligence Platform")
    print("=" * 60)
    
    # Initialize database
    try:
        init_db()
        print("[OK] Database initialized")
    except Exception as e:
        print(f"[WARN] Database initialization warning: {e}")
    
    # Initialize RAG pipeline
    try:
        from rag import get_rag_pipeline
        get_rag_pipeline()
        print("[OK] RAG pipeline loaded")
    except Exception as e:
        print(f"[WARN] RAG pipeline warning: {e}")
    
    print("=" * 60)
    print(f"Server running on http://{settings.BACKEND_HOST}:{settings.BACKEND_PORT}")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("\nShutting down...")


# Create FastAPI app
app = FastAPI(
    title="ARGO Oceanographic Intelligence Platform",
    description="AI-powered conversational platform for ARGO float data analysis",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(data_routes.router)
app.include_router(visualization_routes.router)
app.include_router(live_routes.router)
app.include_router(api_routes.router)
app.include_router(analytics_routes.router)

# Register error handlers
app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, custom_http_exception_handler)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "ARGO Oceanographic Intelligence Platform API",
        "version": "1.0.0",
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "api": "operational"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True
    )
