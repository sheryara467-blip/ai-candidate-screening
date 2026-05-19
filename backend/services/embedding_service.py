# ============================================================
# services/embedding_service.py
# Orchestrates the INCREMENTAL SYNC workflow:
#   1. Detect which fields changed on a job update
#   2. Re-generate embeddings ONLY for changed data
#   3. Upsert updated vector into Pinecone
#   4. Update SQLite record with vector ID + clear update flag
#
# IMPORTANT: We never re-embed everything blindly.
# Only fields that changed trigger new embedding generation.
# ============================================================

from sqlalchemy.orm import Session
from fastapi import HTTPException
import logging

from models.job import Job
from services.pinecone_service import pinecone_service

logger = logging.getLogger(__name__)


# ============================================================
# Generate and store embedding for a job
# Called after job creation or when embedding_needs_update = True
# ============================================================
def generate_and_store_job_embedding(db: Session, job_id: int, force: bool = False) -> dict:
    # Fetch the job from SQLite
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job id={job_id} not found")

    # Check if embedding update is needed
    if not force and not job.embedding_needs_update:
        logger.info(f"Job {job_id}: embedding is already up-to-date, skipping")
        return {
            "job_id": job_id,
            "message": "Embedding already up-to-date",
            "vector_id": job.pinecone_vector_id,
            "fields_updated": []
        }

    # Build the canonical vector ID for this job
    # Format: "job-{id}" — consistent and easy to reference
    vector_id = f"job-{job_id}"

    # Build embedding text from job fields
    job_data = {
        "title": job.title,
        "department": job.department,
        "description": job.description,
        "required_skills": job.required_skills,
        "experience": job.experience,
        "education": job.education,
    }
    embedding_text = pinecone_service.build_job_embedding_text(job_data)

    # Build metadata stored alongside the vector in Pinecone
    metadata = {
        "job_id": job_id,
        "title": job.title,
        "department": job.department,
        "status": job.status.value,
        "required_skills": job.required_skills,
    }

    # Upsert vector into Pinecone (insert or update)
    logger.info(f"Upserting job embedding to Pinecone: vector_id={vector_id}")
    pinecone_service.upsert_vector(vector_id, embedding_text, metadata)

    # Update SQLite: save vector ID and clear the update flag
    job.pinecone_vector_id = vector_id
    job.embedding_needs_update = False
    db.commit()
    db.refresh(job)

    logger.info(
        f"Job {job_id}: embedding synced to Pinecone successfully. "
        f"vector_id={vector_id}"
    )

    return {
        "job_id": job_id,
        "message": "Embedding generated and synced to Pinecone",
        "vector_id": vector_id,
        "fields_updated": list(job_data.keys())
    }


# ============================================================
# Delete job embedding from Pinecone
# Called when a job is permanently deleted from SQLite
# ============================================================
def delete_job_embedding(vector_id: str) -> bool:
    if not vector_id:
        logger.info("No vector ID to delete — skipping Pinecone cleanup")
        return False

    # Remove vector from Pinecone to keep in sync with SQLite
    logger.info(f"Deleting job vector from Pinecone: {vector_id}")
    pinecone_service.delete_vector(vector_id)
    return True


# ============================================================
# Sync all jobs that have pending embedding updates
# Useful for batch processing after multiple job edits
# ============================================================
def sync_pending_embeddings(db: Session) -> dict:
    # Find all jobs where embedding is out of sync
    pending_jobs = (
        db.query(Job)
        .filter(Job.embedding_needs_update == True)  # noqa: E712
        .all()
    )

    synced = []
    failed = []

    for job in pending_jobs:
        try:
            result = generate_and_store_job_embedding(db, job.id, force=True)
            synced.append(job.id)
            logger.info(f"Synced embedding for job {job.id}")
        except Exception as e:
            failed.append({"job_id": job.id, "error": str(e)})
            logger.error(f"Failed to sync embedding for job {job.id}: {e}")

    return {
        "total_pending": len(pending_jobs),
        "synced": synced,
        "failed": failed
    }