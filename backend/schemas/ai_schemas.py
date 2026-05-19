# ============================================================
# EXACT FILE LOCATION: backend/schemas/ai_schemas.py
# ============================================================
# PURPOSE: Pydantic request/response shapes for the AI pipeline.
# These define what the Phase 3/4/5 APIs send and receive.
# Does NOT touch the database — only validates/formats data.
# ============================================================

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from models.ai_models import RecommendationLevel, EmbeddingType


# ============================================================
# PHASE 3 — Resume Processing Schemas
# ============================================================

class ResumeExtractRequest(BaseModel):
    """
    Request to extract and process a resume by candidate profile ID.
    The CV file must already be uploaded (resume_path saved in DB).
    """
    candidate_profile_id: int = Field(..., example=1)


class ResumeExtractResponse(BaseModel):
    """
    Response after extracting text from a PDF resume.
    Returns all parsed fields.
    """
    candidate_profile_id  : int
    raw_text              : Optional[str]
    cleaned_text          : Optional[str]
    extracted_skills      : Optional[str]
    extracted_education   : Optional[str]
    extracted_experience  : Optional[str]
    extracted_certifications: Optional[str]
    is_processed          : bool
    message               : str


class ResumeDataResponse(BaseModel):
    """Full resume data record returned from the database."""
    id                      : int
    candidate_profile_id    : int
    raw_text                : Optional[str]
    cleaned_text            : Optional[str]
    extracted_skills        : Optional[str]
    extracted_education     : Optional[str]
    extracted_experience    : Optional[str]
    extracted_certifications: Optional[str]
    is_processed            : bool
    embedding_needs_update  : bool
    created_at              : datetime
    updated_at              : datetime

    class Config:
        from_attributes = True


# ============================================================
# PHASE 4 — Embedding Schemas
# ============================================================

class EmbeddingGenerateRequest(BaseModel):
    """Request to generate/regenerate an embedding."""
    force: bool = Field(
        default=False,
        description="Force re-generation even if embedding already exists"
    )


class EmbeddingResponse(BaseModel):
    """Response after generating and storing an embedding in Pinecone."""
    entity_type   : str
    entity_id     : int
    vector_id     : str
    dimension     : int
    model_name    : str

    # FIX 5: suppress Pydantic "model_" namespace warning
    model_config = {"protected_namespaces": ()}
    is_synced     : bool
    message       : str


class EmbeddingStatusResponse(BaseModel):
    """Summary of all embedding sync statuses."""
    total_jobs             : int
    jobs_synced            : int
    jobs_pending           : int
    total_candidates       : int
    candidates_synced      : int
    candidates_pending     : int
    last_checked           : datetime


class EmbeddingSyncResponse(BaseModel):
    """Response after running the batch sync operation."""
    synced_jobs       : List[int]
    synced_candidates : List[int]
    failed            : List[dict]
    message           : str


# ============================================================
# PHASE 5 — Matching + Scoring Schemas
# ============================================================

class MatchRequest(BaseModel):
    """
    Request to run semantic matching between a candidate and a job.
    Both must already have embeddings in Pinecone.
    """
    candidate_profile_id : int = Field(..., example=1)
    job_id               : int = Field(..., example=1)
    force_recalculate    : bool = Field(
        default=False,
        description="Recalculate even if a match result already exists"
    )


class SkillAnalysisItem(BaseModel):
    """Single skill result within a match analysis."""
    skill_name  : str
    is_matched  : bool
    similarity  : float
    is_required : bool

    class Config:
        from_attributes = True


class MatchResultResponse(BaseModel):
    """
    Full structured AI analysis result for one candidate vs one job.
    This is the main output of the Phase 5 matching engine.
    """
    candidate_profile_id  : int
    candidate_name        : str
    job_id                : int
    job_title             : str

    # Scoring components
    cv_similarity_score   : float
    skill_match_score     : float
    experience_score      : float
    final_match_score     : float

    # AI outputs
    recommendation        : RecommendationLevel
    matched_skills        : List[str]
    missing_skills        : List[str]
    strengths             : List[str]
    weaknesses            : List[str]
    ai_summary            : Optional[str]

    # Per-skill breakdown
    skill_analysis        : List[SkillAnalysisItem] = []

    created_at            : datetime

    class Config:
        from_attributes = True


class BulkMatchRequest(BaseModel):
    """Request to run matching for ALL candidates of a specific job."""
    job_id : int = Field(..., example=1)
    force  : bool = Field(default=False)


class BulkMatchResponse(BaseModel):
    """Response after running bulk matching for a job."""
    job_id          : int
    total_candidates: int
    processed       : int
    failed          : int
    results         : List[MatchResultResponse]