# ============================================================
# EXACT FILE LOCATION: backend/schemas/interview_schemas.py
# ============================================================
# FIXED:
#   - QuestionEvaluationResult.semantic_score is now Optional
#     so evaluations without it don't throw a validation error
#   - model_config added to EmbeddingMetadata to suppress
#     the "model_name" namespace warning
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.interview_models import SessionStatus, AnswerType, QuestionCategory


# ============================================================
# Question schemas
# ============================================================

class InterviewQuestionResponse(BaseModel):
    id            : int
    session_id    : int
    question_text : str
    category      : QuestionCategory
    order_index   : int
    audio_path    : Optional[str]
    is_answered   : bool
    created_at    : datetime

    class Config:
        from_attributes = True


# ============================================================
# Answer schemas
# ============================================================

class SubmitAnswerRequest(BaseModel):
    """Payload when candidate submits a text answer."""
    session_id   : int       = Field(..., example=1)
    question_id  : int       = Field(..., example=1)
    answer_text  : str       = Field(..., min_length=1, example="FastAPI uses dependency injection...")
    answer_type  : AnswerType = Field(default=AnswerType.TEXT)


class InterviewAnswerResponse(BaseModel):
    id             : int
    question_id    : int
    session_id     : int
    answer_text    : Optional[str]
    answer_type    : AnswerType
    audio_path     : Optional[str]
    answer_score   : Optional[float]
    ai_feedback    : Optional[str]
    is_evaluated   : bool
    semantic_score : Optional[float]
    submitted_at   : datetime

    class Config:
        from_attributes = True


# ============================================================
# Session schemas
# ============================================================

class InterviewSessionResponse(BaseModel):
    """Full session with all questions and answers."""
    id                   : int
    candidate_profile_id : int
    job_id               : int
    status               : SessionStatus
    interview_score      : Optional[float]
    overall_feedback     : Optional[str]
    strengths            : Optional[str]
    weaknesses           : Optional[str]
    recommendation       : Optional[str]
    interview_mode       : str
    started_at           : Optional[datetime]
    completed_at         : Optional[datetime]
    created_at           : datetime
    questions            : List[InterviewQuestionResponse] = []

    class Config:
        from_attributes = True


class InterviewSessionSummary(BaseModel):
    """Lightweight session summary for listing."""
    id                   : int
    candidate_profile_id : int
    job_id               : int
    status               : SessionStatus
    interview_score      : Optional[float]
    recommendation       : Optional[str]
    interview_mode       : str
    created_at           : datetime

    class Config:
        from_attributes = True


# ============================================================
# Voice / TTS schemas
# ============================================================

class TTSRequest(BaseModel):
    """Request to convert question text to speech audio."""
    question_id : int = Field(..., example=1)
    text        : str = Field(..., example="Explain FastAPI dependency injection.")


class TTSResponse(BaseModel):
    question_id : int
    audio_url   : str
    message     : str


class TranscribeResponse(BaseModel):
    """Response after transcribing a voice answer."""
    question_id : int
    session_id  : int
    transcript  : str
    audio_path  : str
    message     : str


# ============================================================
# Evaluation schemas
# ============================================================

class QuestionEvaluationResult(BaseModel):
    question      : str
    answer        : str
    answer_score  : float
    feedback      : str
    # FIX 4: Made Optional with default 0.0 — evaluation service
    # does not always return semantic_score, causing 500 errors.
    semantic_score: Optional[float] = 0.0


class EvaluationResponse(BaseModel):
    """Full interview evaluation result — Phase 8 output."""
    session_id        : int
    candidate_name    : str
    job_title         : str
    interview_score   : float
    recommendation    : str
    strengths         : List[str]
    weaknesses        : List[str]
    overall_feedback  : str
    question_analysis : List[QuestionEvaluationResult]