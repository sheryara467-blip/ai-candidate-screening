# ============================================================
# EXACT FILE LOCATION: backend/api/embeddings.py
# ============================================================
# PURPOSE: Phase 4 API routes for embedding generation and sync.
#
# Routes:
#   POST /embeddings/job/{job_id}               → embed one job
#   POST /embeddings/candidate/{candidate_id}   → embed one candidate
#   POST /embeddings/sync                       → sync all pending
#   GET  /embeddings/status                     → sync status summary
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from database.database import get_db
from schemas.ai_schemas import (
    EmbeddingGenerateRequest,
    EmbeddingResponse,
    EmbeddingStatusResponse,
    EmbeddingSyncResponse,
)
import services.vector_service as vec_svc

router = APIRouter(prefix="/embeddings", tags=["Phase 4 - Embeddings"])


# ============================================================
# POST /embeddings/job/{job_id}
# Generate and store embedding for a single job in Pinecone
# ============================================================
@router.post("/job/{job_id}", response_model=EmbeddingResponse)
def embed_job(
    job_id: int,
    request: EmbeddingGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a semantic embedding for a job and upsert it to Pinecone.
    Set force=true to regenerate even if already synced.
    """
    result = vec_svc.generate_job_embedding(db, job_id, force=request.force)
    return result


# ============================================================
# POST /embeddings/candidate/{candidate_id}
# Generate and store embedding for a candidate resume in Pinecone
# ============================================================
@router.post("/candidate/{candidate_id}", response_model=EmbeddingResponse)
def embed_candidate(
    candidate_id: int,
    request: EmbeddingGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a semantic embedding for a candidate's processed resume.
    The resume must be processed first via POST /resume/process/{id}.
    Set force=true to regenerate even if already synced.
    """
    result = vec_svc.generate_candidate_embedding(
        db, candidate_id, force=request.force
    )
    return result


# ============================================================
# POST /embeddings/sync
# Batch sync all jobs and candidates with pending embedding updates
# ============================================================
@router.post("/sync", response_model=EmbeddingSyncResponse)
def sync_all_embeddings(db: Session = Depends(get_db)):
    """
    Find all records with embedding_needs_update=True and sync them.
    Useful after bulk job edits or after processing many resumes.
    """
    result = vec_svc.sync_all_pending_embeddings(db)
    return result


# ============================================================
# GET /embeddings/status
# Returns a summary of current embedding sync status
# ============================================================
@router.get("/status", response_model=EmbeddingStatusResponse)
def get_embedding_status(db: Session = Depends(get_db)):
    """
    Returns count of synced vs pending embeddings for both jobs and candidates.
    Use this to check if the system is in sync with Pinecone.
    """
    status = vec_svc.get_embedding_status(db)
    return EmbeddingStatusResponse(**status)