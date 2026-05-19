# ============================================================
# models/application.py  —  NEW in Phase 2
# ORM models for CandidateProfile and Application tables.
#
# CandidateProfile  : person who fills the apply form
# Application       : links a candidate to a job with status
#
# These tables extend the existing Phase 1 schema without
# touching or breaking the jobs / candidates / scores tables.
# ============================================================

from sqlalchemy import (
    Column, Integer, String, Text,
    DateTime, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum


# ============================================================
# Application status enum
# Starts as SUBMITTED, admin updates it through Phase 1 panel
# ============================================================
class AppStatus(str, enum.Enum):
    SUBMITTED      = "SUBMITTED"
    UNDER_REVIEW   = "UNDER_REVIEW"
    SHORTLISTED    = "SHORTLISTED"
    REJECTED       = "REJECTED"


# ============================================================
# CandidateProfile
# Stores personal details submitted by the candidate.
# One person can apply to many jobs (one profile → many applications).
# Email is used as the unique identifier for status lookup.
# ============================================================
class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id         = Column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name  = Column(String(200), nullable=False)
    email      = Column(String(200), nullable=False, index=True)
    phone      = Column(String(30),  nullable=True)

    # Path to uploaded PDF CV (relative to /uploads directory)
    resume_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # One candidate profile → many applications
    applications = relationship(
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<CandidateProfile id={self.id} email='{self.email}'>"


# ============================================================
# Application
# Links a CandidateProfile to a Job.
# Also stores the optional cover message and current status.
# ============================================================
class Application(Base):
    __tablename__ = "applications"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Foreign key to the candidate who applied
    candidate_id = Column(
        Integer,
        ForeignKey("candidate_profiles.id"),
        nullable=False,
        index=True
    )

    # Foreign key to the job being applied for (from Phase 1 jobs table)
    job_id       = Column(
        Integer,
        ForeignKey("jobs.id"),
        nullable=False,
        index=True
    )

    # Optional message / cover letter from the candidate
    cover_message = Column(Text, nullable=True)

    # Current lifecycle status — admin updates this in Phase 1 panel
    status = Column(
        Enum(AppStatus),
        default=AppStatus.SUBMITTED,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    candidate = relationship("CandidateProfile", back_populates="applications")
    job       = relationship("Job")       # Back-ref to Phase 1 Job model

    def __repr__(self):
        return (
            f"<Application id={self.id} "
            f"candidate_id={self.candidate_id} "
            f"job_id={self.job_id} "
            f"status='{self.status}'>"
        )