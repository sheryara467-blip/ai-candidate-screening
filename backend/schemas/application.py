# ============================================================
# EXACT FILE LOCATION: backend/schemas/application.py
# ============================================================
# PURPOSE: Defines API REQUEST and RESPONSE shapes using Pydantic.
# This file does NOT touch the database.
# It only validates what comes IN and formats what goes OUT.
#
# Contains schemas for:
#   - Submitting an application (ApplicationCreate)
#   - Returning application data (ApplicationResponse)
#   - Checking status by email (ApplicationStatusResponse)
#   - CV upload response (CVUploadResponse)
#   - Public job listing for candidates (PublicJobResponse)
# ============================================================

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from models.application import AppStatus


# ============================================================
# SCHEMA 1: CandidateProfileCreate
# What the candidate sends when filling their personal details
# ============================================================
class CandidateProfileCreate(BaseModel):
    full_name : str           = Field(..., min_length=2, max_length=200, example="Ali Hassan")
    email     : str           = Field(..., example="ali@example.com")
    phone     : Optional[str] = Field(None, max_length=30, example="+92-300-1234567")

    @validator("email")
    def email_lowercase(cls, v):
        return v.strip().lower()

    @validator("full_name")
    def name_strip(cls, v):
        return v.strip()


# ============================================================
# SCHEMA 2: CandidateProfileResponse
# What the API returns when showing candidate profile data
# ============================================================
class CandidateProfileResponse(BaseModel):
    id          : int
    full_name   : str
    email       : str
    phone       : Optional[str]
    resume_path : Optional[str]
    created_at  : datetime

    class Config:
        from_attributes = True   # allows converting SQLAlchemy object → Pydantic


# ============================================================
# SCHEMA 3: ApplicationCreate
# The full payload candidate sends when submitting the apply form.
# Includes personal details + job_id + optional CV path + message.
# ============================================================
class ApplicationCreate(BaseModel):
    full_name     : str           = Field(..., min_length=2, example="Ali Hassan")
    email         : str           = Field(..., example="ali@example.com")
    phone         : Optional[str] = Field(None, example="+92-300-1234567")
    job_id        : int           = Field(..., example=1)
    cover_message : Optional[str] = Field(None, example="I am very interested in this role...")
    resume_path   : Optional[str] = Field(None, example="uploads/abc123_cv.pdf")

    @validator("email")
    def email_lowercase(cls, v):
        return v.strip().lower()


# ============================================================
# SCHEMA 4: ApplicationResponse
# Full application data returned after submit or detail lookup.
# Includes nested candidate profile info.
# ============================================================
class ApplicationResponse(BaseModel):
    id            : int
    job_id        : int
    cover_message : Optional[str]
    status        : AppStatus
    created_at    : datetime
    updated_at    : datetime

    # Nested candidate profile inside the response
    candidate     : CandidateProfileResponse

    class Config:
        from_attributes = True


# ============================================================
# SCHEMA 5: ApplicationStatusResponse
# Lightweight response used on the status page.
# Candidate looks up their applications by email.
#
# UPDATED: Added interview_session_id — set automatically
# once the AI pipeline completes after submission.
# Frontend uses this to show the "Start Interview" button.
# ============================================================
class ApplicationStatusResponse(BaseModel):
    application_id : int
    job_id         : int
    job_title      : str
    department     : str
    status         : AppStatus
    applied_on     : datetime
    # None until AI pipeline (matching + interview generation) completes
    interview_session_id : Optional[int] = None


# ============================================================
# SCHEMA 6: CVUploadResponse
# Returned after a successful PDF upload.
# The resume_path from this response is sent in ApplicationCreate.
# ============================================================
class CVUploadResponse(BaseModel):
    message     : str
    resume_path : str
    filename    : str


# ============================================================
# SCHEMA 7: PublicJobResponse
# Job data shown to candidates on the careers page.
# Does NOT expose admin-only fields like embedding_needs_update.
# ============================================================
class PublicJobResponse(BaseModel):
    id              : int
    title           : str
    department      : str
    description     : str
    required_skills : str
    experience      : Optional[str]
    education       : Optional[str]
    status          : str
    created_at      : datetime

    class Config:
        from_attributes = True