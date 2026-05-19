# ============================================================
# EXACT FILE LOCATION: backend/schemas/candidate.py
# ============================================================
# Pydantic response schemas for Candidate, Score, Recommendation.
# Used by the admin dashboard to display candidate screening results.
#
# UPDATED vs older version:
#   - RecommendationResponse.level changed from RecommendationLevel
#     enum to plain str so it also accepts values injected as plain
#     strings from build_candidate_response() in candidates.py
#   - Added match_percentage to CandidateResultResponse directly
#     so the candidates page can show it without nesting into score
#   - DashboardStatsResponse keeps draft_jobs + closed_jobs
# ============================================================

from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from models.candidate import ApplicationStatus, RecommendationLevel


# ============================================================
# Score response schema
# ============================================================
class ScoreResponse(BaseModel):
    """Breakdown of candidate scoring components."""
    id                : int
    candidate_id      : int
    cv_score          : float
    skill_match_score : float
    interview_score   : float
    final_score       : float
    match_percentage  : float
    created_at        : datetime

    class Config:
        from_attributes = True


# ============================================================
# Recommendation response schema
# ============================================================
class RecommendationResponse(BaseModel):
    """AI-generated hiring recommendation."""
    id           : int
    candidate_id : int
    # Using str instead of RecommendationLevel enum so plain string
    # values injected by build_candidate_response() are accepted too
    level        : str
    summary      : Optional[str]
    strengths    : Optional[str]
    weaknesses   : Optional[str]
    created_at   : datetime

    class Config:
        from_attributes = True


# ============================================================
# Full candidate response with scores and recommendation
# Used in admin "View Candidates" page
# ============================================================
class CandidateResultResponse(BaseModel):
    """Complete candidate data including scores and AI recommendation."""
    id                   : int
    candidate_profile_id : Optional[int] = None
    job_id               : int
    name                 : str
    email                : str
    extracted_skills     : Optional[str]
    missing_skills       : Optional[str]
    # Direct field so frontend can read it without nesting into score
    match_percentage     : Optional[float] = None
    status               : ApplicationStatus
    created_at           : datetime
    updated_at           : datetime

    # Nested score and recommendation data
    score          : Optional[ScoreResponse]          = None
    recommendation : Optional[RecommendationResponse] = None

    class Config:
        from_attributes = True


# ============================================================
# Summary response for dashboard stats
# ============================================================
class DashboardStatsResponse(BaseModel):
    """Stats displayed on the admin dashboard overview page."""
    total_jobs             : int
    active_jobs            : int   # Jobs with status = OPEN
    draft_jobs             : int
    closed_jobs            : int
    total_candidates       : int
    shortlisted_candidates : int
    pending_embedding_sync : int   # Jobs with embedding_needs_update = True