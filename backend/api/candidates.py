# ============================================================
# EXACT FILE LOCATION: backend/api/candidates.py
# ============================================================
# MERGED: keeps the full build_candidate_response() logic from
# the working older version + adds the shortlisted fix from
# the latest update.
#
# build_candidate_response() correctly bridges Phase 1 Candidate
# rows → Phase 2 Application/CandidateProfile → Phase 5 CandidateMatch
# so the admin page always shows scores when they exist.
# ============================================================

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from database.database import get_db
from schemas.candidate import CandidateResultResponse, DashboardStatsResponse
from models.application import Application, CandidateProfile
from models.ai_models import CandidateMatch, RecommendationLevel
from models.job import Job, JobStatus
from models.candidate import Candidate, ApplicationStatus

router = APIRouter(prefix="/api", tags=["Candidates & Dashboard"])


# ============================================================
# build_candidate_response
# ============================================================
# Bridges the three phases into one response dict:
#
#   Phase 1:  Candidate row           (admin table)
#       ↓  join by email + job_id
#   Phase 2:  Application + Profile   (portal tables)
#       ↓  join by candidate_profile_id
#   Phase 5:  CandidateMatch          (AI results table)
#
# Returns a plain dict that matches CandidateResultResponse schema.
# Falls back gracefully if Phase 2/5 data is not yet available.
# ============================================================
def build_candidate_response(candidate: Candidate, db: Session) -> dict:
    """Return admin candidate data with Phase 5 match results when available."""
    data = {
        "id":                   candidate.id,
        "candidate_profile_id": None,
        "job_id":               candidate.job_id,
        "name":                 candidate.name,
        "email":                candidate.email,
        "extracted_skills":     candidate.extracted_skills,
        "missing_skills":       candidate.missing_skills,
        "status":               candidate.status,
        "created_at":           candidate.created_at,
        "updated_at":           candidate.updated_at,
        "score":                None,
        "recommendation":       None,
    }

    # ── Step 1: find the Phase 2 Application for this candidate ──
    application = (
        db.query(Application)
        .join(CandidateProfile, CandidateProfile.id == Application.candidate_id)
        .filter(
            Application.job_id       == candidate.job_id,
            CandidateProfile.email   == candidate.email,
        )
        .first()
    )
    if not application:
        return data

    data["candidate_profile_id"] = application.candidate_id

    # ── Step 2: find the Phase 5 CandidateMatch ──────────────────
    match = (
        db.query(CandidateMatch)
        .filter(
            CandidateMatch.candidate_profile_id == application.candidate_id,
            CandidateMatch.job_id               == candidate.job_id,
        )
        .first()
    )
    if not match:
        return data

    # ── Step 3: inject match data into the response ───────────────
    data["extracted_skills"] = match.matched_skills
    data["missing_skills"]   = match.missing_skills

    # Score block — maps CandidateMatch fields → ScoreResponse shape
    data["score"] = {
        "id":                match.id,
        "candidate_id":      candidate.id,
        "cv_score":          match.cv_similarity_score,
        "skill_match_score": match.skill_match_score,
        "interview_score":   match.experience_score,
        "final_score":       match.final_match_score,
        "match_percentage":  match.skill_match_score,
        "created_at":        match.created_at,
    }

    # Recommendation block — maps CandidateMatch fields → RecommendationResponse shape
    data["recommendation"] = {
        "id":           match.id,
        "candidate_id": candidate.id,
        "level":        match.recommendation.value if match.recommendation else "NOT_RECOMMENDED",
        "summary":      match.ai_summary,
        "strengths":    match.strengths,
        "weaknesses":   match.weaknesses,
        "created_at":   match.created_at,
    }

    return data


# ============================================================
# GET /api/jobs/{job_id}/candidates
# Returns all candidates for a job with AI screening results.
# ============================================================
@router.get("/jobs/{job_id}/candidates", response_model=List[CandidateResultResponse])
def get_candidates_for_job(
    job_id : int,
    status : Optional[ApplicationStatus] = Query(None, description="Filter by application status"),
    db     : Session = Depends(get_db)
):
    """
    Get all candidates for a job with their screening results.
    Includes: match percentage, missing skills, AI recommendation, scores.
    """
    query = db.query(Candidate).filter(Candidate.job_id == job_id)

    if status:
        query = query.filter(Candidate.status == status)

    # Order by final score descending — best candidates first
    candidates = (
        query
        .outerjoin(Candidate.score)
        .order_by(Candidate.score.property.mapper.class_.final_score.desc().nullslast())
        .all()
    )

    return [build_candidate_response(c, db) for c in candidates]


# ============================================================
# GET /api/candidates/{candidate_id}
# Get full detail for one candidate.
# ============================================================
@router.get("/candidates/{candidate_id}", response_model=CandidateResultResponse)
def get_candidate_detail(candidate_id: int, db: Session = Depends(get_db)):
    """Get full screening result for one candidate."""
    from fastapi import HTTPException
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail=f"Candidate id={candidate_id} not found")
    return build_candidate_response(candidate, db)


# ============================================================
# GET /api/dashboard/stats
# Dashboard aggregated statistics.
# FIXED: shortlisted_candidates now counts from CandidateMatch
# (AI-recommended) not the old manual status column.
# ============================================================
@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Dashboard overview stats:
    - total/active/draft/closed jobs
    - total candidates
    - shortlisted = AI RECOMMENDED or HIGHLY_RECOMMENDED
    - jobs awaiting embedding sync
    """
    total_jobs  = db.query(Job).count()
    active_jobs = db.query(Job).filter(Job.status == JobStatus.OPEN).count()
    draft_jobs  = db.query(Job).filter(Job.status == JobStatus.DRAFT).count()
    closed_jobs = db.query(Job).filter(Job.status == JobStatus.CLOSED).count()

    total_candidates = db.query(Candidate).count()

    # Count AI-shortlisted from Phase 5 match results
    shortlisted_candidates = (
        db.query(CandidateMatch)
        .filter(
            CandidateMatch.recommendation.in_([
                RecommendationLevel.HIGHLY_RECOMMENDED,
                RecommendationLevel.RECOMMENDED,
            ])
        )
        .count()
    )

    pending_embedding_sync = (
        db.query(Job)
        .filter(Job.embedding_needs_update == True)  # noqa: E712
        .count()
    )

    return DashboardStatsResponse(
        total_jobs             = total_jobs,
        active_jobs            = active_jobs,
        draft_jobs             = draft_jobs,
        closed_jobs            = closed_jobs,
        total_candidates       = total_candidates,
        shortlisted_candidates = shortlisted_candidates,
        pending_embedding_sync = pending_embedding_sync,
    )


# ============================================================
# PATCH /api/candidates/{candidate_id}/status
# Admin manually shortlists or rejects a candidate.
# ============================================================
from fastapi import HTTPException
from pydantic import BaseModel

class StatusUpdateRequest(BaseModel):
    status: ApplicationStatus

@router.patch("/candidates/{candidate_id}/status")
def update_candidate_status(
    candidate_id : int,
    body         : StatusUpdateRequest,
    db           : Session = Depends(get_db)
):
    """
    Admin shortlists or rejects a candidate.
    Updates the Phase 1 Candidate.status column.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = body.status
    db.commit()
    return {"id": candidate_id, "status": body.status, "message": "Status updated"}