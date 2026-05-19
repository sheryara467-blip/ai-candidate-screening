# ============================================================
# EXACT FILE LOCATION: backend/services/evaluation_service.py
# ============================================================
# PURPOSE: Phase 8 — AI evaluation of interview answers.
#
# Scoring formula:
#   Interview Score = average of all per-answer scores
#
# Final candidate score (updated after interview):
#   Final = (CV Score × 0.3) + (Skill Match × 0.4) + (Interview × 0.3)
#
# Workflow:
#   1. Load all answers for a completed session
#   2. For each answer: call Groq to evaluate + score
#   3. Compute average interview score
#   4. Call Groq for overall summary + recommendation
#   5. Save all results to DB
#   6. Update CandidateMatch final_match_score
# ============================================================

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from datetime import datetime, timezone
import logging

from models.interview_models import (
    InterviewSession, InterviewQuestion,
    InterviewAnswer, SessionStatus
)
from models.ai_models import CandidateMatch, RecommendationLevel
from services.llm_service import evaluate_answer, generate_interview_summary

logger = logging.getLogger(__name__)


# ============================================================
# EVALUATE FULL INTERVIEW SESSION
# Triggered after candidate completes all answers.
# ============================================================
def evaluate_session(db: Session, session_id: int) -> InterviewSession:

    # Load session with all questions and answers
    session = (
        db.query(InterviewSession)
        .options(
            joinedload(InterviewSession.questions).joinedload(InterviewQuestion.answer),
            joinedload(InterviewSession.candidate_profile),
            joinedload(InterviewSession.job)
        )
        .filter(InterviewSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    if session.status not in (SessionStatus.COMPLETED, SessionStatus.IN_PROGRESS):
        raise HTTPException(
            status_code=400,
            detail=f"Session status is '{session.status}' — must be COMPLETED to evaluate"
        )

    # Collect Q&A pairs for evaluation
    qa_pairs = []
    for question in session.questions:
        answer = question.answer
        if not answer or not answer.answer_text:
            # Skip unanswered questions
            continue
        qa_pairs.append({
            "question_id"  : question.id,
            "question"     : question.question_text,
            "answer"       : answer.answer_text,
            "answer_obj"   : answer,
        })

    if not qa_pairs:
        raise HTTPException(
            status_code=400,
            detail="No answers found to evaluate"
        )

    # Evaluate each answer using Groq LLM
    total_score     = 0.0
    question_results = []

    for pair in qa_pairs:
        logger.info(f"Evaluating answer for question {pair['question_id']}")

        eval_result = evaluate_answer(
            question        = pair["question"],
            answer          = pair["answer"],
            job_title       = session.job.title if session.job else "Unknown",
            expected_skills = session.job.required_skills if session.job else ""
        )

        score    = eval_result["score"]
        feedback = eval_result["feedback"]

        # Save evaluation to the answer record
        answer_obj             = pair["answer_obj"]
        answer_obj.answer_score = score
        answer_obj.ai_feedback  = feedback
        answer_obj.is_evaluated = True

        total_score += score
        question_results.append({
            "question" : pair["question"],
            "answer"   : pair["answer"],
            "score"    : score,
            "feedback" : feedback,
        })

    # Calculate average interview score
    avg_score = round(total_score / len(qa_pairs), 2)

    # Generate overall summary using Groq
    summary = generate_interview_summary(
        candidate_name   = session.candidate_profile.full_name if session.candidate_profile else "Candidate",
        job_title        = session.job.title if session.job else "Unknown",
        question_results = question_results,
        avg_score        = avg_score,
    )

    # Update session with evaluation results
    session.interview_score  = avg_score
    session.overall_feedback = summary.get("overall_feedback", "")
    session.strengths        = " | ".join(summary.get("strengths", []))
    session.weaknesses       = " | ".join(summary.get("weaknesses", []))
    session.recommendation   = summary.get("recommendation", "Average")
    session.status           = SessionStatus.EVALUATED

    db.commit()

    # Update the CandidateMatch final score to include interview score
    _update_final_match_score(db, session)

    db.refresh(session)

    logger.info(
        f"Session {session_id} evaluated: "
        f"score={avg_score:.1f} recommendation={session.recommendation}"
    )
    return session


# ============================================================
# UPDATE FINAL MATCH SCORE with interview component
#
# Final = (CV Similarity × 0.3)
#       + (Skill Match   × 0.4)
#       + (Interview     × 0.3)
#
# NOTE: weights updated from Phase 5 (CV was 0.4, now 0.3)
# because interview score is now included.
# ============================================================
def _update_final_match_score(db: Session, session: InterviewSession):
    match = (
        db.query(CandidateMatch)
        .filter(
            CandidateMatch.candidate_profile_id == session.candidate_profile_id,
            CandidateMatch.job_id               == session.job_id
        )
        .first()
    )

    if not match:
        logger.warning(
            f"No CandidateMatch found for "
            f"candidate={session.candidate_profile_id} job={session.job_id}"
        )
        return

    interview_score = session.interview_score or 0.0

    # Recalculate with interview component
    new_final = round(
        (match.cv_similarity_score * 0.3)
        + (match.skill_match_score  * 0.4)
        + (interview_score          * 0.3),
        2
    )

    match.final_match_score = new_final

    # Update recommendation based on new final score
    if new_final >= 80:
        match.recommendation = RecommendationLevel.HIGHLY_RECOMMENDED
    elif new_final >= 60:
        match.recommendation = RecommendationLevel.RECOMMENDED
    elif new_final >= 40:
        match.recommendation = RecommendationLevel.NEEDS_IMPROVEMENT
    else:
        match.recommendation = RecommendationLevel.NOT_RECOMMENDED

    db.commit()
    logger.info(
        f"Updated final match score: "
        f"candidate={session.candidate_profile_id} "
        f"new_score={new_final:.1f}"
    )


# ============================================================
# GET EVALUATION RESULTS — formatted for API response
# ============================================================
def get_evaluation_results(db: Session, session_id: int) -> dict:
    session = (
        db.query(InterviewSession)
        .options(
            joinedload(InterviewSession.questions).joinedload(InterviewQuestion.answer),
            joinedload(InterviewSession.candidate_profile),
            joinedload(InterviewSession.job)
        )
        .filter(InterviewSession.id == session_id)
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Build question analysis list
    question_analysis = []
    for q in session.questions:
        if q.answer:
            question_analysis.append({
                "question"    : q.question_text,
                "answer"      : q.answer.answer_text or "",
                "answer_score": q.answer.answer_score or 0.0,
                "feedback"    : q.answer.ai_feedback  or "",
                "semantic_score": q.answer.semantic_score or 0.0,
            })

    return {
        "session_id"       : session.id,
        "candidate_name"   : session.candidate_profile.full_name if session.candidate_profile else "—",
        "job_title"        : session.job.title if session.job else "—",
        "interview_score"  : session.interview_score or 0.0,
        "recommendation"   : session.recommendation  or "Pending",
        "strengths"        : [s.strip() for s in (session.strengths or "").split("|") if s.strip()],
        "weaknesses"       : [w.strip() for w in (session.weaknesses or "").split("|") if w.strip()],
        "overall_feedback" : session.overall_feedback or "",
        "question_analysis": question_analysis,
    }