# ============================================================
# EXACT FILE LOCATION: backend/services/vector_service.py
# ============================================================
# PURPOSE: Phase 4 — Generate and manage embeddings for both
# jobs and candidates, sync them to Pinecone, and track
# metadata in SQLite via EmbeddingMetadata table.
#
# IMPORTANT FIX:
# ------------------------------------------------------------
# Original code directly imported:
#
#     from services.pinecone_service import pinecone_service
#
# But  NEW optimized pinecone_service.py now uses:
#
#     get_pinecone_service()
#
# because PineconeService is lazy-loaded to prevent
# Render free-tier memory crashes.
#
# Without this fix:
# ------------------------------------------------------------
# pinecone_service becomes None
#
# causing errors like:
#
# 'NoneType' object has no attribute 'upsert_vector'
# 'NoneType' object has no attribute 'build_job_embedding_text'
# 'NoneType' object has no attribute 'fetch_vector'
#
# SOLUTION:
# ------------------------------------------------------------
# Keep old code structure intact.
# Only replace direct singleton usage with lazy getter.
#
# No functionality removed.
# ============================================================

from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone
import logging

from models.job import Job
from models.ai_models import ResumeData, EmbeddingMetadata, EmbeddingType

# ============================================================
# ORIGINAL IMPORT (COMMENTED — OLD IMPLEMENTATION)
# ------------------------------------------------------------
# This no longer works because pinecone_service now starts as:
#
# pinecone_service = None
#
# from services.pinecone_service import pinecone_service
# ============================================================

# ============================================================
# NEW IMPORT — LAZY LOADED SERVICE
# ============================================================
from services.pinecone_service import get_pinecone_service

logger = logging.getLogger(__name__)


# ============================================================
# Build a rich text representation of a candidate for embedding.
# Combines all extracted fields into one semantic string.
# Better input text → better embedding → better matching.
# ============================================================
def build_candidate_embedding_text(resume_data: ResumeData) -> str:
    parts = []

    if resume_data.extracted_skills:
        parts.append(f"Skills: {resume_data.extracted_skills}")

    if resume_data.extracted_education:
        parts.append(f"Education: {resume_data.extracted_education}")

    if resume_data.extracted_experience:
        parts.append(f"Experience: {resume_data.extracted_experience}")

    if resume_data.extracted_certifications:
        parts.append(f"Certifications: {resume_data.extracted_certifications}")

    # Also include portion of cleaned resume text for semantic richness
    if resume_data.cleaned_text:
        # Use first 500 characters to avoid exceeding token limits
        parts.append(f"Resume: {resume_data.cleaned_text[:500]}")

    return " | ".join(parts) if parts else ""


# ============================================================
# Generate and store embedding for a CANDIDATE
# Vector ID format: "candidate-{candidate_profile_id}"
# ============================================================
def generate_candidate_embedding(
    db: Session,
    candidate_profile_id: int,
    force: bool = False
) -> dict:

    # ========================================================
    # NEW: Get lazy-loaded Pinecone service instance
    # ========================================================
    pinecone_service = get_pinecone_service()

    # Load the candidate's processed resume data
    resume_data = (
        db.query(ResumeData)
        .filter(ResumeData.candidate_profile_id == candidate_profile_id)
        .first()
    )

    if not resume_data:
        raise HTTPException(
            status_code=404,
            detail=f"No processed resume for candidate {candidate_profile_id}. "
                   "Run POST /resume/process first."
        )

    # Check existing embedding metadata
    vector_id = f"candidate-{candidate_profile_id}"

    existing = (
        db.query(EmbeddingMetadata)
        .filter(
            EmbeddingMetadata.entity_type == EmbeddingType.CANDIDATE,
            EmbeddingMetadata.entity_id == candidate_profile_id
        )
        .first()
    )

    # Skip if already synced and force is False
    if (
        existing
        and existing.is_synced
        and not force
        and not resume_data.embedding_needs_update
    ):
        logger.info(
            f"Candidate {candidate_profile_id} embedding already in sync, skipping"
        )

        return {
            "entity_type": "CANDIDATE",
            "entity_id": candidate_profile_id,
            "vector_id": vector_id,
            "dimension": 384,
            "model_name": "all-MiniLM-L6-v2",
            "is_synced": True,
            "message": "Embedding already up-to-date"
        }

    # Build embedding text from all resume fields
    embedding_text = build_candidate_embedding_text(resume_data)

    if not embedding_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Resume has no extractable content for embedding"
        )

    # Build Pinecone metadata stored alongside the vector
    metadata = {
        "entity_type": "candidate",
        "candidate_id": candidate_profile_id,
        "extracted_skills": resume_data.extracted_skills or "",
        "extracted_education": resume_data.extracted_education or "",
        "extracted_experience": resume_data.extracted_experience or "",
    }

    # Generate embedding and upsert to Pinecone
    logger.info(f"Generating embedding for candidate {candidate_profile_id}")

    pinecone_service.upsert_vector(
        vector_id,
        embedding_text,
        metadata
    )

    # Save or update EmbeddingMetadata in SQLite
    now = datetime.now(timezone.utc)

    if existing:
        existing.is_synced = True
        existing.last_synced_at = now

    else:
        embedding_meta = EmbeddingMetadata(
            entity_type=EmbeddingType.CANDIDATE,
            entity_id=candidate_profile_id,
            vector_id=vector_id,
            dimension=384,
            model_name="all-MiniLM-L6-v2",
            is_synced=True,
            last_synced_at=now
        )

        db.add(embedding_meta)

    # Clear the update flag on resume data
    resume_data.embedding_needs_update = False

    db.commit()

    logger.info(
        f"Candidate {candidate_profile_id} embedding synced: {vector_id}"
    )

    return {
        "entity_type": "CANDIDATE",
        "entity_id": candidate_profile_id,
        "vector_id": vector_id,
        "dimension": 384,
        "model_name": "all-MiniLM-L6-v2",
        "is_synced": True,
        "message": "Candidate embedding generated and synced to Pinecone"
    }


# ============================================================
# Generate and store embedding for a JOB
# Extends Phase 1 job embedding — adds EmbeddingMetadata record
# ============================================================
def generate_job_embedding(
    db: Session,
    job_id: int,
    force: bool = False
) -> dict:

    # ========================================================
    # NEW: Get lazy-loaded Pinecone service instance
    # ========================================================
    pinecone_service = get_pinecone_service()

    # Load job from SQLite
    job = db.query(Job).filter(Job.id == job_id).first()

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job id={job_id} not found"
        )

    vector_id = f"job-{job_id}"

    # Check existing metadata
    existing = (
        db.query(EmbeddingMetadata)
        .filter(
            EmbeddingMetadata.entity_type == EmbeddingType.JOB,
            EmbeddingMetadata.entity_id == job_id
        )
        .first()
    )

    # Skip if already synced
    if (
        existing
        and existing.is_synced
        and not force
        and not job.embedding_needs_update
    ):
        return {
            "entity_type": "JOB",
            "entity_id": job_id,
            "vector_id": vector_id,
            "dimension": 384,
            "model_name": "all-MiniLM-L6-v2",
            "is_synced": True,
            "message": "Job embedding already up-to-date"
        }

    # Build embedding text from job fields
    job_data = {
        "title": job.title,
        "department": job.department,
        "description": job.description,
        "required_skills": job.required_skills,
        "experience": job.experience,
        "education": job.education,
    }

    embedding_text = pinecone_service.build_job_embedding_text(
        job_data
    )

    metadata = {
        "entity_type": "job",
        "job_id": job_id,
        "title": job.title,
        "department": job.department,
        "required_skills": job.required_skills or "",
        "status": job.status.value,
    }

    # Upsert to Pinecone
    logger.info(f"Generating embedding for job {job_id}")

    pinecone_service.upsert_vector(
        vector_id,
        embedding_text,
        metadata
    )

    # Update SQLite
    now = datetime.now(timezone.utc)

    if existing:
        existing.is_synced = True
        existing.last_synced_at = now

    else:
        db.add(
            EmbeddingMetadata(
                entity_type=EmbeddingType.JOB,
                entity_id=job_id,
                vector_id=vector_id,
                dimension=384,
                model_name="all-MiniLM-L6-v2",
                is_synced=True,
                last_synced_at=now
            )
        )

    job.pinecone_vector_id = vector_id
    job.embedding_needs_update = False

    db.commit()

    logger.info(f"Job {job_id} embedding synced: {vector_id}")

    return {
        "entity_type": "JOB",
        "entity_id": job_id,
        "vector_id": vector_id,
        "dimension": 384,
        "model_name": "all-MiniLM-L6-v2",
        "is_synced": True,
        "message": "Job embedding generated and synced to Pinecone"
    }


# ============================================================
# Batch sync — process all pending embeddings for jobs + candidates
# ============================================================
def sync_all_pending_embeddings(db: Session) -> dict:

    from models.job import Job
    from models.ai_models import ResumeData

    synced_jobs = []
    synced_candidates = []
    failed = []

    # Sync all jobs with pending embedding updates
    pending_jobs = (
        db.query(Job)
        .filter(Job.embedding_needs_update == True)  # noqa: E712
        .all()
    )

    for job in pending_jobs:

        try:
            generate_job_embedding(db, job.id, force=True)
            synced_jobs.append(job.id)

        except Exception as e:
            failed.append({
                "type": "job",
                "id": job.id,
                "error": str(e)
            })

    # Sync all candidates with pending embedding updates
    pending_resumes = (
        db.query(ResumeData)
        .filter(ResumeData.embedding_needs_update == True)  # noqa: E712
        .all()
    )

    for resume in pending_resumes:

        try:
            generate_candidate_embedding(
                db,
                resume.candidate_profile_id,
                force=True
            )

            synced_candidates.append(
                resume.candidate_profile_id
            )

        except Exception as e:
            failed.append({
                "type": "candidate",
                "id": resume.candidate_profile_id,
                "error": str(e)
            })

    return {
        "synced_jobs": synced_jobs,
        "synced_candidates": synced_candidates,
        "failed": failed,
        "message": (
            f"Synced {len(synced_jobs)} jobs, "
            f"{len(synced_candidates)} candidates"
        )
    }


# ============================================================
# Get embedding sync status summary
# ============================================================
def get_embedding_status(db: Session) -> dict:

    from models.job import Job
    from models.ai_models import ResumeData

    total_jobs = db.query(Job).count()

    jobs_synced = (
        db.query(Job)
        .filter(Job.embedding_needs_update == False)
        .count()
    )

    total_cands = db.query(ResumeData).count()

    cands_synced = (
        db.query(ResumeData)
        .filter(ResumeData.embedding_needs_update == False)
        .count()
    )

    return {
        "total_jobs": total_jobs,
        "jobs_synced": jobs_synced,
        "jobs_pending": total_jobs - jobs_synced,
        "total_candidates": total_cands,
        "candidates_synced": cands_synced,
        "candidates_pending": total_cands - cands_synced,
        "last_checked": datetime.now(timezone.utc),
    }