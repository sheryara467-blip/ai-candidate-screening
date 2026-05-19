# ============================================================
# EXACT FILE LOCATION: backend/services/resume_service.py
# ============================================================
# PURPOSE: Phase 3 — Resume extraction and processing pipeline.
#
# Workflow:
#   1. Get candidate profile + resume_path from SQLite
#   2. Extract raw text from PDF using pdfplumber
#   3. Clean the extracted text
#   4. Extract: skills, education, experience, certifications
#   5. Save all extracted data to resume_data table
#   6. Mark embedding_needs_update = True for Phase 4
# ============================================================

import os
import logging
import pdfplumber
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.application import CandidateProfile
from models.ai_models import ResumeData
from utils.text_cleaner import clean_resume_text, extract_sections
from utils.skill_extractor import (
    extract_skills_from_text,
    extract_education_from_text,
    extract_experience_from_text,
    extract_certifications_from_text,
)

logger = logging.getLogger(__name__)


# ============================================================
# Extract text from a PDF file using pdfplumber
# pdfplumber is more accurate than PyPDF2 for complex layouts
# ============================================================
def extract_text_from_pdf(file_path: str) -> str:
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"Resume file not found: {file_path}"
        )

    raw_text = ""

    try:
        # Open PDF and extract text from every page
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    raw_text += page_text + "\n"
                logger.debug(f"Extracted page {page_num + 1}: {len(page_text or '')} chars")

    except Exception as e:
        logger.error(f"PDF extraction failed for {file_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read PDF: {str(e)}"
        )

    logger.info(f"Extracted {len(raw_text)} characters from {file_path}")
    return raw_text


# ============================================================
# Full resume processing pipeline
# Steps: extract → clean → parse → save to DB
# Returns the ResumeData ORM object
# ============================================================
def process_resume(db: Session, candidate_profile_id: int) -> ResumeData:

    # Step 1: Get the candidate profile to find the resume path
    profile = (
        db.query(CandidateProfile)
        .filter(CandidateProfile.id == candidate_profile_id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate profile id={candidate_profile_id} not found"
        )
    if not profile.resume_path:
        raise HTTPException(
            status_code=400,
            detail="No resume uploaded for this candidate"
        )

    logger.info(
        f"Processing resume for candidate {candidate_profile_id}: "
        f"{profile.resume_path}"
    )

    # Step 2: Extract raw text from PDF
    raw_text = extract_text_from_pdf(profile.resume_path)

    # Step 3: Clean the extracted text
    cleaned_text = clean_resume_text(raw_text)

    # Step 4: Extract structured fields from cleaned text
    skills         = extract_skills_from_text(cleaned_text)
    education      = extract_education_from_text(cleaned_text)
    experience     = extract_experience_from_text(cleaned_text)
    certifications = extract_certifications_from_text(cleaned_text)

    # Convert skills list to comma-separated string for storage
    skills_str = ", ".join(skills)

    # Step 5: Find or create the ResumeData record for this candidate
    resume_data = (
        db.query(ResumeData)
        .filter(ResumeData.candidate_profile_id == candidate_profile_id)
        .first()
    )

    if resume_data:
        # Update existing record with fresh extraction
        resume_data.raw_text                 = raw_text
        resume_data.cleaned_text             = cleaned_text
        resume_data.extracted_skills         = skills_str
        resume_data.extracted_education      = education
        resume_data.extracted_experience     = experience
        resume_data.extracted_certifications = certifications
        resume_data.is_processed             = True
        resume_data.embedding_needs_update   = True  # Flag for Phase 4 sync
    else:
        # Create a new ResumeData record
        resume_data = ResumeData(
            candidate_profile_id    = candidate_profile_id,
            raw_text                = raw_text,
            cleaned_text            = cleaned_text,
            extracted_skills        = skills_str,
            extracted_education     = education,
            extracted_experience    = experience,
            extracted_certifications= certifications,
            is_processed            = True,
            embedding_needs_update  = True
        )
        db.add(resume_data)

    db.commit()
    db.refresh(resume_data)

    logger.info(
        f"Resume processed: candidate={candidate_profile_id} "
        f"skills={len(skills)} education='{education[:50] if education else ''}'"
    )
    return resume_data


# ============================================================
# Get resume data for a candidate (read-only)
# Used by the matching service to get extracted skills
# ============================================================
def get_resume_data(db: Session, candidate_profile_id: int) -> ResumeData:
    resume = (
        db.query(ResumeData)
        .filter(ResumeData.candidate_profile_id == candidate_profile_id)
        .first()
    )
    if not resume:
        raise HTTPException(
            status_code=404,
            detail=f"No processed resume found for candidate {candidate_profile_id}. "
                   "Please run POST /resume/process first."
        )
    return resume