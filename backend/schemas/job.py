# ============================================================
# schemas/job.py
# Pydantic models for request validation and response serialization.
# These define what data the API accepts and returns — NOT the DB schema.
# ============================================================

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from models.job import JobStatus


# ============================================================
# JobRequirement schemas
# ============================================================

class JobRequirementCreate(BaseModel):
    """Schema for creating a single job requirement."""
    category: str = Field(..., min_length=1, max_length=100, example="Technical")
    description: str = Field(..., min_length=1, example="Must have 3+ years of Python experience")
    is_mandatory: bool = Field(default=True)


class JobRequirementUpdate(BaseModel):
    """Schema for updating a job requirement — all fields optional."""
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_mandatory: Optional[bool] = None


class JobRequirementResponse(BaseModel):
    """Schema for returning job requirement data in API responses."""
    id: int
    job_id: int
    category: str
    description: str
    is_mandatory: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Enables ORM → Pydantic conversion


# ============================================================
# Job schemas
# ============================================================

class JobCreate(BaseModel):
    """Schema for creating a new job posting."""
    title: str = Field(..., min_length=2, max_length=255, example="Senior Python Developer")
    department: str = Field(..., min_length=1, max_length=100, example="Engineering")
    description: str = Field(..., min_length=10, example="We are looking for a senior developer...")
    required_skills: str = Field(..., min_length=1, example="Python, FastAPI, Docker, PostgreSQL")
    experience: Optional[str] = Field(None, example="3+ years")
    education: Optional[str] = Field(None, example="Bachelor's in Computer Science")
    status: JobStatus = Field(default=JobStatus.DRAFT)

    # Optional: embed requirements at creation time
    requirements: Optional[List[JobRequirementCreate]] = Field(default=[])

    @validator("required_skills")
    def skills_not_empty(cls, v):
        # Ensure skills string is not just whitespace
        if not v.strip():
            raise ValueError("required_skills cannot be empty")
        return v.strip()


class JobUpdate(BaseModel):
    """Schema for updating an existing job — all fields optional."""
    title: Optional[str] = Field(None, max_length=255)
    department: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    required_skills: Optional[str] = None
    experience: Optional[str] = None
    education: Optional[str] = None
    status: Optional[JobStatus] = None


class JobResponse(BaseModel):
    """Schema for returning full job data — includes related requirements."""
    id: int
    title: str
    department: str
    description: str
    required_skills: str
    experience: Optional[str]
    education: Optional[str]
    status: JobStatus
    pinecone_vector_id: Optional[str]
    embedding_needs_update: bool
    created_at: datetime
    updated_at: datetime
    requirements: List[JobRequirementResponse] = []

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """Lightweight schema used when listing many jobs (no requirements)."""
    id: int
    title: str
    department: str
    status: JobStatus
    required_skills: str
    experience: Optional[str]
    education: Optional[str]
    embedding_needs_update: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Embedding request/response schemas
# ============================================================

class EmbeddingRegenerateRequest(BaseModel):
    """Request body for manual embedding regeneration."""
    force_full: bool = Field(
        default=False,
        description="If True, regenerate entire embedding even if nothing changed"
    )


class EmbeddingRegenerateResponse(BaseModel):
    """Response after triggering embedding regeneration."""
    job_id: int
    message: str
    vector_id: str
    fields_updated: List[str]