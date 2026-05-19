# ============================================================
# EXACT FILE LOCATION: backend/services/interview_service.py
# ============================================================
# PURPOSE: Phase 6 — Automatic interview question generation
# and session management.
#
# AUTOMATIC WORKFLOW:
#   After matching completes → auto_generate_interview() is called
#   → Creates InterviewSession
#   → Calls Groq to generate questions
#   → Saves questions to DB
#   → Candidate can then open the interview page
# ============================================================

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from datetime import datetime, timezone
import logging

from models.interview_models import (
    InterviewSession, InterviewQuestion,
    InterviewAnswer, SessionStatus, QuestionCategory
)
from models.application import CandidateProfile
from models.job import Job
from models.ai_models import CandidateMatch
from services.llm_service import generate_interview_questions

logger = logging.getLogger(__name__)


# ============================================================
# AUTO GENERATE INTERVIEW
# Called automatically after semantic matching completes.
# Creates session + questions if they don't exist yet.
# ============================================================
def auto_generate_interview(
    db: Session,
    candidate_profile_id: int,
    job_id: int
) -> InterviewSession:

    # Check if a session already exists for this candidate+job
    existing = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.candidate_profile_id == candidate_profile_id,
            InterviewSession.job_id               == job_id
        )
        .first()
    )
    if existing:
        logger.info(
            f"Interview session already exists for "
            f"candidate={candidate_profile_id} job={job_id}, skipping"
        )
        return existing

    # Load candidate profile
    profile = db.query(CandidateProfile).filter(
        CandidateProfile.id == candidate_profile_id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    # Load job
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Load match result to get missing skills context
    match_result = (
        db.query(CandidateMatch)
        .filter(
            CandidateMatch.candidate_profile_id == candidate_profile_id,
            CandidateMatch.job_id               == job_id
        )
        .first()
    )

    missing_skills    = match_result.missing_skills    if match_result else ""
    candidate_experience = ""

    # Try to get experience from resume data
    from models.ai_models import ResumeData
    resume = db.query(ResumeData).filter(
        ResumeData.candidate_profile_id == candidate_profile_id
    ).first()
    if resume:
        candidate_experience = resume.extracted_experience or ""

    # Create the interview session
    session = InterviewSession(
        candidate_profile_id = candidate_profile_id,
        job_id               = job_id,
        status               = SessionStatus.PENDING,
        interview_mode       = "TEXT"
    )
    db.add(session)
    db.flush()  # Get session.id

    logger.info(
        f"Generating interview questions for "
        f"candidate={candidate_profile_id} job={job_id}"
    )

    # Call Groq LLM to generate contextual questions
    try:
        raw_questions = generate_interview_questions(
            job_title            = job.title,
            job_description      = job.description,
            required_skills      = job.required_skills or "",
            missing_skills       = missing_skills or "",
            candidate_experience = candidate_experience,
            num_questions        = 5
        )
    except Exception as e:
        logger.error(f"LLM question generation failed: {e}")
        # Use fallback questions so the session is still usable
        raw_questions = _fallback_questions(job.title, job.required_skills or "")

    # Save each question to the database
    category_map = {
        "TECHNICAL":       QuestionCategory.TECHNICAL,
        "BEHAVIORAL":      QuestionCategory.BEHAVIORAL,
        "PROBLEM_SOLVING": QuestionCategory.PROBLEM_SOLVING,
    }

    for idx, q in enumerate(raw_questions, start=1):
        cat_str  = q.get("category", "TECHNICAL").upper()
        category = category_map.get(cat_str, QuestionCategory.TECHNICAL)

        question = InterviewQuestion(
            session_id    = session.id,
            question_text = q.get("question", "").strip(),
            category      = category,
            order_index   = idx,
        )
        db.add(question)

    # FIX 2: Wrapped in try/except so a commit failure is
    # caught, rolled back, and re-raised clearly instead of
    # silently corrupting the session state.
    try:
        db.commit()
        db.refresh(session)
    except Exception as e:
        db.rollback()
        logger.error(
            f"Interview session commit failed for "
            f"candidate={candidate_profile_id} job={job_id}: {e}"
        )
        raise

    logger.info(
        f"Interview session {session.id} created with "
        f"{len(raw_questions)} questions for candidate={candidate_profile_id}"
    )
    return session


# ============================================================
# GET SESSION FOR CANDIDATE
# Returns full session with questions and answers
# ============================================================
def get_session_for_candidate(
    db: Session,
    candidate_profile_id: int,
    job_id: int
) -> InterviewSession:
    session = (
        db.query(InterviewSession)
        .options(
            joinedload(InterviewSession.questions)
        )
        .filter(
            InterviewSession.candidate_profile_id == candidate_profile_id,
            InterviewSession.job_id               == job_id
        )
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=404,
            detail="No interview session found. Please ensure matching has been completed."
        )
    return session


# ============================================================
# GET SESSION BY ID
# ============================================================
def get_session_by_id(db: Session, session_id: int) -> InterviewSession:
    session = (
        db.query(InterviewSession)
        .options(
            joinedload(InterviewSession.questions),
            joinedload(InterviewSession.candidate_profile),
            joinedload(InterviewSession.job)
        )
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail=f"Interview session {session_id} not found")
    return session


# ============================================================
# START SESSION — mark as IN_PROGRESS
# ============================================================
def start_session(db: Session, session_id: int) -> InterviewSession:
    session = get_session_by_id(db, session_id)
    if session.status == SessionStatus.PENDING:
        session.status     = SessionStatus.IN_PROGRESS
        session.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(session)
    return session


# ============================================================
# SAVE ANSWER — store candidate's text answer
# ============================================================
def save_answer(
    db: Session,
    session_id: int,
    question_id: int,
    answer_text: str,
    answer_type: str = "TEXT",
    audio_path: str  = None
) -> InterviewAnswer:

    # Verify session and question exist
    session  = get_session_by_id(db, session_id)
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id         == question_id,
        InterviewQuestion.session_id == session_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=404,
            detail=f"Question {question_id} not found in session {session_id}"
        )

    # Check for existing answer — update if exists
    existing_answer = (
        db.query(InterviewAnswer)
        .filter(InterviewAnswer.question_id == question_id)
        .first()
    )

    if existing_answer:
        existing_answer.answer_text = answer_text
        existing_answer.answer_type = answer_type
        if audio_path:
            existing_answer.audio_path = audio_path
        answer = existing_answer
    else:
        answer = InterviewAnswer(
            question_id = question_id,
            session_id  = session_id,
            answer_text = answer_text,
            answer_type = answer_type,
            audio_path  = audio_path,
        )
        db.add(answer)

    # Mark question as answered
    question.is_answered = True
    db.commit()
    db.refresh(answer)

    # Check if all questions are answered → mark session complete
    all_questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.session_id == session_id
    ).all()

    if all(q.is_answered for q in all_questions):
        session.status       = SessionStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Session {session_id} completed — all questions answered")

    return answer


# ============================================================
# GET ALL SESSIONS FOR A JOB (admin view)
# ============================================================
def get_sessions_for_job(db: Session, job_id: int) -> list:
    return (
        db.query(InterviewSession)
        .options(joinedload(InterviewSession.candidate_profile))
        .filter(InterviewSession.job_id == job_id)
        .order_by(InterviewSession.created_at.desc())
        .all()
    )


# ============================================================
# Fallback questions if Groq API fails
# ============================================================
def _fallback_questions(job_title: str, required_skills: str) -> list:
    skills = [s.strip() for s in required_skills.split(",") if s.strip()]
    first_skill = skills[0] if skills else "your primary skill"
    return [
        {"question": f"Explain your experience with {first_skill}.", "category": "TECHNICAL"},
        {"question": f"What does a typical day look like for a {job_title}?", "category": "BEHAVIORAL"},
        {"question": "Describe a difficult technical problem you solved recently.", "category": "PROBLEM_SOLVING"},
        {"question": f"How do you stay updated with the latest trends in {job_title}?", "category": "BEHAVIORAL"},
        {"question": f"Walk us through how you would architect a solution using {first_skill}.", "category": "TECHNICAL"},
    ]