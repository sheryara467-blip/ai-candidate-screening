# ============================================================
# api/jobs.py
# FastAPI router for all job-related endpoints.
# Handles: CRUD, search, requirements, embedding regeneration.
# ============================================================

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database.database import get_db
from schemas.job import (
    JobCreate, JobUpdate, JobResponse, JobListResponse,
    JobRequirementCreate, JobRequirementUpdate, JobRequirementResponse,
    EmbeddingRegenerateRequest, EmbeddingRegenerateResponse
)
from models.job import JobStatus
import services.job_service as job_svc
import services.embedding_service as emb_svc

# Create a namespaced router — all routes prefixed with /api/jobs
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ============================================================
# POST /api/jobs
# Create a new job posting.
# After creation, automatically generate and store embedding.
# ============================================================
@router.post("/", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """
    Create a new job with requirements.
    Automatically triggers Pinecone embedding generation on creation.
    """
    # Step 1: Save job to SQLite
    new_job = job_svc.create_job(db, job_data)

    # Step 2: Generate and store embedding in Pinecone
    # Non-blocking: if Pinecone fails, job is still saved
    try:
        emb_svc.generate_and_store_job_embedding(db, new_job.id)
    except Exception as e:
        # Log the error but don't fail the job creation
        # The job is marked embedding_needs_update=True, so sync can retry later
        pass

    # Re-fetch to include latest pinecone_vector_id
    return job_svc.get_job_by_id(db, new_job.id)


# ============================================================
# GET /api/jobs
# Retrieve all jobs with optional filtering and search.
# Supports: ?status=OPEN&search=python&skip=0&limit=20
# ============================================================
@router.get("/", response_model=List[JobListResponse])
def get_jobs(
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    search: Optional[str] = Query(None, description="Search in title, department, description, skills"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    db: Session = Depends(get_db)
):
    """
    List all jobs. Supports filtering by status and keyword search.
    """
    return job_svc.get_all_jobs(db, status=status, search=search, skip=skip, limit=limit)


# ============================================================
# GET /api/jobs/{job_id}
# Get full detail for a single job including requirements.
# ============================================================
@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """
    Get complete job detail including all requirements.
    """
    return job_svc.get_job_by_id(db, job_id)


# ============================================================
# PUT /api/jobs/{job_id}
# Update an existing job.
# INCREMENTAL SYNC: only re-embeds if semantic fields changed.
# ============================================================
@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, update_data: JobUpdate, db: Session = Depends(get_db)):
    """
    Update job fields. Automatically re-syncs Pinecone if semantic
    fields (title, description, skills, experience) were changed.
    """
    # Step 1: Update SQLite record and get list of changed fields
    updated_job, modified_fields = job_svc.update_job(db, job_id, update_data)

    # Step 2: Re-generate embedding ONLY if content-relevant fields changed
    # This is the INCREMENTAL SYNC — we don't re-embed status-only changes
    if updated_job.embedding_needs_update:
        try:
            emb_svc.generate_and_store_job_embedding(db, job_id)
        except Exception as e:
            # Embedding failed — it will be retried on next sync
            pass

    return job_svc.get_job_by_id(db, job_id)


# ============================================================
# DELETE /api/jobs/{job_id}
# Delete a job from SQLite and remove its vector from Pinecone.
# ============================================================
@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Permanently delete a job. Also removes its embedding from Pinecone.
    Cascades to delete all requirements and candidate records.
    """
    # Step 1: Delete from SQLite, retrieve vector ID for cleanup
    vector_id = job_svc.delete_job(db, job_id)

    # Step 2: Delete vector from Pinecone to maintain sync
    if vector_id:
        try:
            emb_svc.delete_job_embedding(vector_id)
        except Exception as e:
            pass  # Pinecone cleanup failure doesn't block job deletion


# ============================================================
# POST /api/jobs/{job_id}/requirements
# Add a new requirement to an existing job.
# ============================================================
@router.post("/{job_id}/requirements", response_model=JobRequirementResponse, status_code=status.HTTP_201_CREATED)
def add_requirement(
    job_id: int,
    req_data: JobRequirementCreate,
    db: Session = Depends(get_db)
):
    """Add a structured requirement to a job posting."""
    return job_svc.add_job_requirement(db, job_id, req_data)


# ============================================================
# PUT /api/jobs/{job_id}/requirements/{req_id}
# Update a specific job requirement.
# ============================================================
@router.put("/{job_id}/requirements/{req_id}", response_model=JobRequirementResponse)
def update_requirement(
    job_id: int,
    req_id: int,
    update_data: JobRequirementUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing job requirement."""
    return job_svc.update_job_requirement(db, job_id, req_id, update_data)


# ============================================================
# DELETE /api/jobs/{job_id}/requirements/{req_id}
# Remove a specific requirement from a job.
# ============================================================
@router.delete("/{job_id}/requirements/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_requirement(job_id: int, req_id: int, db: Session = Depends(get_db)):
    """Delete a specific job requirement."""
    job_svc.delete_job_requirement(db, job_id, req_id)


# ============================================================
# POST /api/jobs/{job_id}/regenerate-embedding
# Manually trigger embedding regeneration for a specific job.
# Use force=True to re-generate even if no fields changed.
# ============================================================
@router.post("/{job_id}/regenerate-embedding", response_model=EmbeddingRegenerateResponse)
def regenerate_embedding(
    job_id: int,
    request: EmbeddingRegenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Manually trigger embedding regeneration for a job.
    Use this when Pinecone and SQLite become out of sync,
    or when you want to force a full re-embed.
    """
    result = emb_svc.generate_and_store_job_embedding(
        db, job_id, force=request.force_full
    )
    return result


# ============================================================
# POST /api/jobs/sync-embeddings
# Batch sync all jobs that have pending embedding updates.
# ============================================================
@router.post("/sync-embeddings", response_model=dict)
def sync_all_embeddings(db: Session = Depends(get_db)):
    """
    Sync all jobs that have embedding_needs_update=True.
    Use this to catch up after multiple job edits or Pinecone outages.
    """
    return emb_svc.sync_pending_embeddings(db)