# ============================================================
# EXACT FILE LOCATION: backend/main.py
# ============================================================
# AI Candidate Screening System — Main Entry Point (v4.0.0)
#
# FEATURES:
# - Admin, Candidate, Resume, Embeddings, Matching APIs
# - Interview + Voice modules (Phase 6/7/8)
# - Static file serving for uploads + audio
# - Startup DB init + backfill sync
# ============================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env
load_dotenv()

# Logging configuration (shared across app lifecycle)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================
# FastAPI Application Initialization
# ============================================================
app = FastAPI(
    title="AI Candidate Screening System",
    description=(
        "Phase 1: Admin Dashboard   — /api/*\n"
        "Phase 2: Candidate Portal  — /portal/*\n"
        "Phase 3: Resume Processing — /resume/*\n"
        "Phase 4: Embeddings        — /embeddings/*\n"
        "Phase 5: Semantic Matching — /matching/*\n"
        "Phase 6/7/8: Interview     — /interview/*, /voice/*"
    ),
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# ============================================================
# CORS Configuration
# ============================================================

# OLD CODE (kept for reference)
# allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

# ============================================================
# UPDATED CORS CONFIGURATION
# ============================================================
# FIX:
# Your frontend is deployed on Vercel and backend on Render.
# Browser blocked requests because frontend domain was not
# included properly in Access-Control-Allow-Origin.
#
# This new config:
# - keeps localhost support
# - supports multiple deployed frontend URLs
# - safely strips spaces
# ============================================================

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        (
            "http://localhost:3000,"
            "https://ai-candidate-screening-three.vercel.app,"
            "https://ai-candidate-screening-673im1rjw-sheryara467-blips-projects.vercel.app"
        )
    ).split(",")
]

logger.info(f"CORS Allowed Origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Static File Storage Setup
# ============================================================
# uploads/           → CVs, resumes, documents
# audio/questions/   → generated interview questions audio
# audio/recordings/  → candidate voice responses
# ============================================================
os.makedirs("uploads", exist_ok=True)
os.makedirs("audio/questions", exist_ok=True)
os.makedirs("audio/recordings", exist_ok=True)

# Expose uploaded files via /files URL path
app.mount("/files", StaticFiles(directory="uploads"), name="uploads")

# Expose all audio assets via /audio URL path
app.mount("/audio", StaticFiles(directory="audio"), name="audio")


# ============================================================
# API Router Registration
# ============================================================
# Core system modules (Phases 1–5)
from api.jobs         import router as jobs_router
from api.candidates   import router as candidates_router
from api.applications import router as applications_router
from api.resume       import router as resume_router
from api.embeddings   import router as embeddings_router
from api.matching     import router as matching_router

# Extended modules (Phases 6–8)
from api.interview    import router as interview_router   # Interview engine
from api.voice        import router as voice_router       # Voice processing

# Register all API routes
app.include_router(jobs_router)
app.include_router(candidates_router)
app.include_router(applications_router)
app.include_router(resume_router)
app.include_router(embeddings_router)
app.include_router(matching_router)
app.include_router(interview_router)
app.include_router(voice_router)


# ============================================================
# Startup Event Handler
# ============================================================
# Executes once when server starts:
# 1. Initializes database schema
# 2. Runs backfill to sync legacy Phase 2 applications
#    into Phase 1 Candidate table (safe idempotent operation)
# ============================================================
@app.on_event("startup")
async def startup_event():
    logger.info("Starting AI Candidate Screening API v4.0 ...")

    # Import locally to avoid circular dependencies
    from database.database import SessionLocal, init_db

    # Step 1: Ensure all DB tables exist
    init_db()
    logger.info("All database tables initialized")

    # Step 2: Backfill missing candidate records from applications
    from services.application_service import backfill_admin_candidates

    db = SessionLocal()
    try:
        result = backfill_admin_candidates(db)
        logger.info(
            f"Backfill: {result['created']} created, "
            f"{result['skipped']} skipped"
        )
    finally:
        db.close()

    logger.info("Docs: http://localhost:8000/docs")


# ============================================================
# Health Check Endpoint
# ============================================================
@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "ok",
        "version": "4.0.0"
    }


# ============================================================
# Entry Point (local development only)
# ============================================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("APP_PORT", 8000))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )