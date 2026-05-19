# ============================================================
# EXACT FILE LOCATION: backend/api/matching.py
# ============================================================
# PURPOSE: Phase 5 API routes for semantic matching + scoring.
#
# Routes:
#   POST /matching/run              → match one candidate to one job
#   POST /matching/bulk/{job_id}    → match all candidates for a job
#   GET  /matching/result/{cid}/{jid} → get stored match result
#   GET  /matching/job/{job_id}     → get all match results for a job
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from schemas.ai_schemas import (
    MatchRequest,
    MatchResultResponse,
    BulkMatchRequest,
    BulkMatchResponse,
    SkillAnalysisItem,
)
from models.ai_models import SkillAnalysis
import services.matching_service as match_svc

router = APIRouter(prefix="/matching", tags=["Phase 5 - Semantic Matching"])


# ============================================================
# Helper: convert CandidateMatch ORM object to response schema
# ============================================================
def build_match_response(match) -> MatchResultResponse:
    # Parse comma-separated stored strings back to lists
    def to_list(s): return [x.strip() for x in s.split(",") if x.strip()] if s else []
    def pipe_to_list(s): return [x.strip() for x in s.split("|") if x.strip()] if s else []

    return MatchResultResponse(
        candidate_profile_id = match.candidate_profile_id,
        candidate_name       = match.candidate_profile.full_name if match.candidate_profile else "—",
        job_id               = match.job_id,
        job_title            = match.job.title if match.job else "—",
        cv_similarity_score  = match.cv_similarity_score,
        skill_match_score    = match.skill_match_score,
        experience_score     = match.experience_score,
        final_match_score    = match.final_match_score,
        recommendation       = match.recommendation,
        matched_skills       = to_list(match.matched_skills),
        missing_skills       = to_list(match.missing_skills),
        strengths            = pipe_to_list(match.strengths),
        weaknesses           = pipe_to_list(match.weaknesses),
        ai_summary           = match.ai_summary,
        skill_analysis       = [
            SkillAnalysisItem(
                skill_name  = sa.skill_name,
                is_matched  = sa.is_matched,
                similarity  = sa.similarity,
                is_required = sa.is_required,
            )
            for sa in (match.skill_analysis if hasattr(match, "skill_analysis") else [])
        ],
        created_at           = match.created_at,
    )


# ============================================================
# POST /matching/run
# Run semantic matching for one candidate against one job.
# Both must have embeddings generated (Phase 4).
# ============================================================
@router.post("/run", response_model=MatchResultResponse)
def run_match(request: MatchRequest, db: Session = Depends(get_db)):
    """
    Run the full AI matching pipeline for one candidate + job pair.
    Computes: cosine similarity, skill match %, experience score.
    Returns: final score, recommendation, strengths, weaknesses.

    Prerequisites:
      - Resume processed: POST /resume/process/{candidate_id}
      - Embeddings generated: POST /embeddings/candidate/{id}
                               POST /embeddings/job/{id}
    """
    match = match_svc.run_candidate_job_match(
        db,
        request.candidate_profile_id,
        request.job_id,
        force_recalculate=request.force_recalculate
    )
    return build_match_response(match)


# ============================================================
# POST /matching/bulk/{job_id}
# Run matching for ALL candidates who applied for a specific job.
# Admin triggers this from the job analysis dashboard.
# ============================================================
@router.post("/bulk/{job_id}", response_model=BulkMatchResponse)
def run_bulk_match(
    job_id: int,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """
    Run AI matching for every candidate who applied for this job.
    Returns ranked results sorted by final_match_score descending.
    """
    result = match_svc.run_bulk_job_matching(db, job_id, force=force)
    return BulkMatchResponse(
        job_id           = result["job_id"],
        total_candidates = result["total_candidates"],
        processed        = result["processed"],
        failed           = result["failed"],
        results          = [build_match_response(m) for m in result["results"]]
    )


# ============================================================
# GET /matching/result/{candidate_id}/{job_id}
# Fetch stored match result for a specific candidate + job pair
# ============================================================
@router.get("/result/{candidate_id}/{job_id}", response_model=MatchResultResponse)
def get_match_result(
    candidate_id: int,
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve the stored AI match result for a candidate + job pair.
    Used on the admin candidate analysis page.
    """
    match = match_svc.get_match_result(db, candidate_id, job_id)
    return build_match_response(match)


# ============================================================
# GET /matching/job/{job_id}
# Get all match results for a job, sorted best-first
# ============================================================
@router.get("/job/{job_id}", response_model=List[MatchResultResponse])
def get_job_matches(job_id: int, db: Session = Depends(get_db)):
    """
    Get all candidate match results for a job.
    Results are sorted by final_match_score descending (best candidates first).
    Used on the admin job analysis leaderboard.
    """
    matches = match_svc.get_job_match_results(db, job_id)
    return [build_match_response(m) for m in matches]