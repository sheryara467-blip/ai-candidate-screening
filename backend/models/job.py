# ============================================================
# models/job.py
# SQLAlchemy ORM models for Job and JobRequirement tables.
# These define the actual database schema stored in SQLite.
# ============================================================

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum


# ============================================================
# Enum for job status values
# ============================================================
class JobStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    DRAFT = "DRAFT"


# ============================================================
# Job table: stores all job postings
# ============================================================
class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic job information
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)

    # Comma-separated skills string (e.g. "Python, FastAPI, Docker")
    required_skills = Column(Text, nullable=False)

    # Experience requirement (e.g. "2+ years", "Senior Level")
    experience = Column(String(100), nullable=True)

    # Education requirement (e.g. "Bachelor's in CS")
    education = Column(String(200), nullable=True)

    # Job lifecycle status
    status = Column(
        Enum(JobStatus),
        default=JobStatus.DRAFT,
        nullable=False
    )

    # Pinecone vector ID for this job's embedding
    # Stored here so we can update/delete the vector when job changes
    pinecone_vector_id = Column(String(100), nullable=True)

    # Track which fields have been updated since last embedding sync
    # This enables INCREMENTAL sync — only re-embed what changed
    embedding_needs_update = Column(Boolean, default=True, nullable=False)

    # Timestamps — auto-set on insert/update
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship to requirements (one job → many requirements)
    requirements = relationship(
        "JobRequirement",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    # Relationship to candidates (one job → many candidates)
    candidates = relationship(
        "Candidate",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job id={self.id} title='{self.title}' status='{self.status}'>"


# ============================================================
# JobRequirement table: detailed requirements per job
# Separate from the main skills string to allow structured storage
# ============================================================
class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key links requirement to its parent job
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Requirement category (e.g. "Technical", "Soft Skills", "Certifications")
    category = Column(String(100), nullable=False)

    # The actual requirement description
    description = Column(Text, nullable=False)

    # Is this requirement mandatory or just preferred?
    is_mandatory = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Back-reference to parent job
    job = relationship("Job", back_populates="requirements")

    def __repr__(self):
        return f"<JobRequirement id={self.id} job_id={self.job_id} category='{self.category}'>"