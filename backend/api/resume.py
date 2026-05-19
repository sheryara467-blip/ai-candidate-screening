# ============================================================
# EXACT FILE LOCATION: backend/api/resume.py
# ============================================================
# PURPOSE: Phase 3 API routes for resume extraction.
#
# Routes:
#   POST /resume/process/{candidate_id}  → extract + parse resume
#   GET  /resume/{candidate_id}          → get stored resume data
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.ai_schemas import ResumeExtractResponse, ResumeDataResponse
import services.resume_service as resume_svc

router = APIRouter(prefix="/resume", tags=["Phase 3 - Resume Processing"])


# ============================================================
# POST /resume/process/{candidate_id}
# Triggers the full resume processing pipeline:
# PDF extract → clean → parse skills/education/experience → save
# ============================================================
@router.post("/process/{candidate_id}", response_model=ResumeExtractResponse)
def process_resume(candidate_id: int, db: Session = Depends(get_db)):
    """
    Extract and parse a candidate's uploaded PDF resume.
    The CV must be already uploaded (Phase 2 /portal/upload-cv).
    Saves extracted skills, education, experience to SQLite.
    Also flags embedding_needs_update = True for Phase 4 sync.
    """
    resume_data = resume_svc.process_resume(db, candidate_id)

    return ResumeExtractResponse(
        candidate_profile_id     = resume_data.candidate_profile_id,
        raw_text                 = resume_data.raw_text,
        cleaned_text             = resume_data.cleaned_text,
        extracted_skills         = resume_data.extracted_skills,
        extracted_education      = resume_data.extracted_education,
        extracted_experience     = resume_data.extracted_experience,
        extracted_certifications = resume_data.extracted_certifications,
        is_processed             = resume_data.is_processed,
        message                  = "Resume extracted and processed successfully"
    )


# ============================================================
# GET /resume/{candidate_id}
# Returns the stored resume data for a candidate
# ============================================================
@router.get("/{candidate_id}", response_model=ResumeDataResponse)
def get_resume_data(candidate_id: int, db: Session = Depends(get_db)):
    """
    Fetch stored resume extraction data for a candidate.
    Returns all parsed fields: skills, education, experience, certifications.
    """
    return resume_svc.get_resume_data(db, candidate_id)