"""
DualTrust AI — FastAPI Application Entry Point
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.routes import applications, documents, analysis, reviews, audit, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup + shutdown lifecycle."""
    # Validate critical env vars at startup — fail loud, fail early
    settings.validate_required()
    # Create tables (Alembic handles migrations in prod; this is for dev convenience)
    Base.metadata.create_all(bind=engine)
    print("[OK] DualTrust AI backend started")
    print(f"   Mode: {'DEMO' if settings.DEMO_MODE else 'PRODUCTION'}")
    print(f"   Groq model: {settings.GROQ_MODEL}")
    print(f"   External verification: {settings.EXTERNAL_VERIFICATION_ENABLED}")
    yield
    print("[SHUTDOWN] DualTrust AI backend shutting down")


app = FastAPI(
    title="DualTrust AI",
    description=(
        "Dual-pipeline AI loan document verification system. "
        "AI-assisted routing only — no automated approve/reject decisions."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["Applications"])
app.include_router(documents.router, prefix="/api/applications", tags=["Documents"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(reviews.router, prefix="/api/applications", tags=["Reviews"])
app.include_router(audit.router, prefix="/api/audit-logs", tags=["Audit"])


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "service": "DualTrust AI Backend",
        "demo_mode": settings.DEMO_MODE,
    }
