# ============================================================
# services/job_service.py
# Business logic layer for all job operations.
# This separates DB/embedding logic from the API route handlers.
# ============================================================

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime
import logging

from models.job import Job, JobRequirement, JobStatus
from schemas.job import JobCreate, JobUpdate, JobRequirementCreate, JobRequirementUpdate

logger = logging.getLogger(__name__)


# ============================================================
# CREATE JOB
# Inserts a new job record and its requirements into SQLite.
# Marks embedding_needs_update = True so the embedding service
# knows to generate and sync to Pinecone.
# ============================================================
def create_job(db: Session, job_data: JobCreate) -> Job:
    # Create the Job ORM object from schema data
    new_job = Job(
        title=job_data.title,
        department=job_data.department,
        description=job_data.description,
        required_skills=job_data.required_skills,
        experience=job_data.experience,
        education=job_data.education,
        status=job_data.status,
        embedding_needs_update=True  # Flag for Pinecone sync
    )

    db.add(new_job)
    db.flush()  # Get the new job ID before committing

    # Add job requirements if provided
    for req_data in (job_data.requirements or []):
        requirement = JobRequirement(
            job_id=new_job.id,
            category=req_data.category,
            description=req_data.description,
            is_mandatory=req_data.is_mandatory
        )
        db.add(requirement)

    db.commit()
    db.refresh(new_job)

    logger.info(f"Created job: id={new_job.id} title='{new_job.title}'")
    return new_job


# ============================================================
# GET ALL JOBS
# Returns all jobs with optional status filter and search.
# This powers both the job list page and dashboard stats.
# ============================================================
def get_all_jobs(
    db: Session,
    status: Optional[JobStatus] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[Job]:
    query = db.query(Job)

    # Filter by status if provided (e.g. only OPEN jobs)
    if status:
        query = query.filter(Job.status == status)

    # Full-text search across title, department, description, skills
    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_term),
                Job.department.ilike(search_term),
                Job.description.ilike(search_term),
                Job.required_skills.ilike(search_term)
            )
        )

    # Order by newest first
    query = query.order_by(Job.created_at.desc())

    return query.offset(skip).limit(limit).all()


# ============================================================
# GET SINGLE JOB BY ID
# Returns full job detail including requirements.
# Raises 404 if job does not exist.
# ============================================================
def get_job_by_id(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with id={job_id} not found")
    return job


# ============================================================
# UPDATE JOB
# INCREMENTAL SYNC LOGIC:
# - Track which fields were actually modified
# - Only mark embedding_needs_update = True if embedding-relevant
#   fields changed (title, description, required_skills, experience)
# ============================================================
def update_job(db: Session, job_id: int, update_data: JobUpdate) -> tuple[Job, list[str]]:
    job = get_job_by_id(db, job_id)

    # Fields that affect semantic embedding
    embedding_sensitive_fields = {"title", "description", "required_skills", "experience", "education"}

    # Track which fields were actually changed
    modified_fields = []
    embedding_fields_changed = []

    # Apply only non-None values from the update schema
    for field, new_value in update_data.model_dump(exclude_none=True).items():
        current_value = getattr(job, field)
        if current_value != new_value:
            setattr(job, field, new_value)
            modified_fields.append(field)
            if field in embedding_sensitive_fields:
                embedding_fields_changed.append(field)

    # Mark embedding for re-generation ONLY if semantically relevant fields changed
    # This implements the INCREMENTAL SYNC requirement
    if embedding_fields_changed:
        job.embedding_needs_update = True
        logger.info(
            f"Job {job_id}: embedding flagged for update "
            f"due to changes in: {embedding_fields_changed}"
        )

    if modified_fields:
        db.commit()
        db.refresh(job)
        logger.info(f"Job {job_id} updated. Modified fields: {modified_fields}")
    else:
        logger.info(f"Job {job_id}: no changes detected, skipping update")

    return job, modified_fields


# ============================================================
# DELETE JOB
# Removes job and all related records from SQLite.
# Returns the pinecone_vector_id so the caller can
# also delete the vector from Pinecone.
# ============================================================
def delete_job(db: Session, job_id: int) -> Optional[str]:
    job = get_job_by_id(db, job_id)

    # Save Pinecone vector ID before deleting (for Pinecone cleanup)
    vector_id = job.pinecone_vector_id

    # SQLAlchemy cascade="all, delete-orphan" handles requirements + candidates
    db.delete(job)
    db.commit()

    logger.info(f"Deleted job id={job_id}, vector_id={vector_id}")
    return vector_id


# ============================================================
# ADD REQUIREMENT TO EXISTING JOB
# ============================================================
def add_job_requirement(
    db: Session, job_id: int, req_data: JobRequirementCreate
) -> JobRequirement:
    # Verify job exists
    get_job_by_id(db, job_id)

    requirement = JobRequirement(
        job_id=job_id,
        category=req_data.category,
        description=req_data.description,
        is_mandatory=req_data.is_mandatory
    )
    db.add(requirement)
    db.commit()
    db.refresh(requirement)
    return requirement


# ============================================================
# UPDATE AN EXISTING REQUIREMENT
# ============================================================
def update_job_requirement(
    db: Session, job_id: int, req_id: int, update_data: JobRequirementUpdate
) -> JobRequirement:
    req = (
        db.query(JobRequirement)
        .filter(JobRequirement.id == req_id, JobRequirement.job_id == job_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Requirement id={req_id} not found for job id={job_id}"
        )

    for field, value in update_data.model_dump(exclude_none=True).items():
        setattr(req, field, value)

    db.commit()
    db.refresh(req)
    return req


# ============================================================
# DELETE A REQUIREMENT
# ============================================================
def delete_job_requirement(db: Session, job_id: int, req_id: int) -> bool:
    req = (
        db.query(JobRequirement)
        .filter(JobRequirement.id == req_id, JobRequirement.job_id == job_id)
        .first()
    )
    if not req:
        raise HTTPException(
            status_code=404,
            detail=f"Requirement id={req_id} not found for job id={job_id}"
        )
    db.delete(req)
    db.commit()
    return True