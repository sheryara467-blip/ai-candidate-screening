# ============================================================
# EXACT FILE LOCATION: backend/api/interview.py
# ============================================================
# PURPOSE: All interview system endpoints.
#
# Routes:
#   POST /interview/generate/{candidate_id}/{job_id}
#   GET  /interview/session/{candidate_id}/{job_id}
#   GET  /interview/session/id/{session_id}
#   POST /interview/start/{session_id}
#   POST /interview/submit-answer
#   POST /interview/evaluate/{session_id}
#   GET  /interview/results/{session_id}
#   GET  /interview/job/{job_id}/sessions
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from database.database import get_db
from schemas.interview_schemas import (
    InterviewSessionResponse,
    InterviewSessionSummary,
    SubmitAnswerRequest,
    InterviewAnswerResponse,
    EvaluationResponse,
    QuestionEvaluationResult,
)
import services.interview_service  as interview_svc
import services.evaluation_service as eval_svc

router = APIRouter(prefix="/interview", tags=["Phase 6/7/8 - Interview System"])


# ============================================================
# POST /interview/generate/{candidate_id}/{job_id}
# Manually trigger interview generation (also called automatically)
# ============================================================
@router.post("/generate/{candidate_id}/{job_id}", response_model=InterviewSessionResponse)
def generate_interview(
    candidate_id: int,
    job_id:       int,
    db: Session = Depends(get_db)
):
    """
    Generate AI interview questions for a candidate+job pair.
    Called automatically after matching, or manually by admin.
    Uses Groq LLM to create contextual, role-specific questions.
    """
    session = interview_svc.auto_generate_interview(db, candidate_id, job_id)
    return session


# ============================================================
# GET /interview/session/id/{session_id}
# Get session by its own ID (MUST come before /session/{id}/{id})
# ============================================================
@router.get("/session/id/{session_id}", response_model=InterviewSessionResponse)
def get_session_by_id(session_id: int, db: Session = Depends(get_db)):
    """Get full interview session including all questions."""
    return interview_svc.get_session_by_id(db, session_id)


# ============================================================
# GET /interview/session/{candidate_id}/{job_id}
# Candidate opens their interview session
# ============================================================
@router.get("/session/{candidate_id}/{job_id}", response_model=InterviewSessionResponse)
def get_session(
    candidate_id: int,
    job_id:       int,
    db: Session = Depends(get_db)
):
    """Get the interview session for a candidate+job pair."""
    return interview_svc.get_session_for_candidate(db, candidate_id, job_id)


# ============================================================
# POST /interview/start/{session_id}
# Mark session as IN_PROGRESS when candidate opens it
# ============================================================
@router.post("/start/{session_id}", response_model=InterviewSessionResponse)
def start_interview(session_id: int, db: Session = Depends(get_db)):
    """Mark interview as started. Records the start timestamp."""
    return interview_svc.start_session(db, session_id)


# ============================================================
# POST /interview/submit-answer
# Candidate submits a text answer to a question
# ============================================================
@router.post("/submit-answer", response_model=InterviewAnswerResponse)
def submit_answer(request: SubmitAnswerRequest, db: Session = Depends(get_db)):
    """
    Save a candidate's text answer.
    Marks the question as answered.
    If all questions are answered, session moves to COMPLETED.
    """
    answer = interview_svc.save_answer(
        db          = db,
        session_id  = request.session_id,
        question_id = request.question_id,
        answer_text = request.answer_text,
        answer_type = request.answer_type,
    )
    return answer


# ============================================================
# POST /interview/evaluate/{session_id}
# Trigger AI evaluation of all answers in a session
# ============================================================
@router.post("/evaluate/{session_id}", response_model=EvaluationResponse)
def evaluate_interview(session_id: int, db: Session = Depends(get_db)):
    """
    Run AI evaluation on all submitted answers.
    Uses Groq LLM to score and provide feedback per answer.
    Updates the CandidateMatch final_match_score with interview component.
    """
    session = eval_svc.evaluate_session(db, session_id)
    results = eval_svc.get_evaluation_results(db, session_id)

    return EvaluationResponse(
        session_id        = results["session_id"],
        candidate_name    = results["candidate_name"],
        job_title         = results["job_title"],
        interview_score   = results["interview_score"],
        recommendation    = results["recommendation"],
        strengths         = results["strengths"],
        weaknesses        = results["weaknesses"],
        overall_feedback  = results["overall_feedback"],
        question_analysis = [
            QuestionEvaluationResult(**q) for q in results["question_analysis"]
        ],
    )


# ============================================================
# GET /interview/results/{session_id}
# Admin views the full evaluated interview report
# ============================================================
@router.get("/results/{session_id}", response_model=EvaluationResponse)
def get_interview_results(session_id: int, db: Session = Depends(get_db)):
    """
    Get the full AI interview evaluation report for admin.
    Shows score, per-question feedback, strengths, weaknesses.
    """
    results = eval_svc.get_evaluation_results(db, session_id)
    return EvaluationResponse(
        session_id        = results["session_id"],
        candidate_name    = results["candidate_name"],
        job_title         = results["job_title"],
        interview_score   = results["interview_score"],
        recommendation    = results["recommendation"],
        strengths         = results["strengths"],
        weaknesses        = results["weaknesses"],
        overall_feedback  = results["overall_feedback"],
        question_analysis = [
            QuestionEvaluationResult(**q) for q in results["question_analysis"]
        ],
    )


# ============================================================
# GET /interview/job/{job_id}/sessions
# Admin views all interview sessions for a job
# ============================================================
@router.get("/job/{job_id}/sessions", response_model=List[InterviewSessionSummary])
def get_job_sessions(job_id: int, db: Session = Depends(get_db)):
    """Get all interview sessions for a specific job (admin view)."""
    return interview_svc.get_sessions_for_job(db, job_id)