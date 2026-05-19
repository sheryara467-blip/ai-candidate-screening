# ============================================================
# EXACT FILE LOCATION: backend/models/ai_models.py
# ============================================================
# PURPOSE: SQLAlchemy ORM models for the AI pipeline.
# Creates 4 new tables in SQLite:
#
#   1. resume_data        — extracted text + parsed fields from CV
#   2. embedding_metadata — tracks Pinecone vector IDs + sync status
#   3. candidate_matches  — final AI match scores per candidate+job
#   4. skill_analysis     — detailed skill breakdown per match
#
# These tables extend Phase 1 + 2 without modifying them.
# ============================================================

from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, Boolean, Enum, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum


# ============================================================
# Enum: recommendation level based on final match score
# 80%+ = Highly Recommended, 60-79% = Recommended,
# 40-59% = Needs Improvement, <40% = Not Recommended
# ============================================================
class RecommendationLevel(str, enum.Enum):
    HIGHLY_RECOMMENDED = "HIGHLY_RECOMMENDED"
    RECOMMENDED        = "RECOMMENDED"
    NEEDS_IMPROVEMENT  = "NEEDS_IMPROVEMENT"
    NOT_RECOMMENDED    = "NOT_RECOMMENDED"


# ============================================================
# Enum: which type of record the embedding belongs to
# ============================================================
class EmbeddingType(str, enum.Enum):
    JOB       = "JOB"
    CANDIDATE = "CANDIDATE"


# ============================================================
# TABLE 1: resume_data
# Stores all extracted and parsed content from a candidate's CV.
# Linked to CandidateProfile by candidate_profile_id.
# ============================================================
class ResumeData(Base):
    __tablename__ = "resume_data"

    id                   = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Link to the candidate who uploaded this CV
    candidate_profile_id = Column(
        Integer,
        ForeignKey("candidate_profiles.id"),
        nullable=False,
        unique=True,     # one resume record per candidate profile
        index=True
    )

    # Raw text extracted directly from the PDF
    raw_text             = Column(Text, nullable=True)

    # Cleaned + normalized version of raw_text (used for embeddings)
    cleaned_text         = Column(Text, nullable=True)

    # Comma-separated skills extracted from CV text
    extracted_skills     = Column(Text, nullable=True)

    # Education section extracted from CV
    extracted_education  = Column(Text, nullable=True)

    # Experience section extracted from CV
    extracted_experience = Column(Text, nullable=True)

    # Certifications extracted from CV
    extracted_certifications = Column(Text, nullable=True)

    # Flag: has this resume been processed through the AI pipeline?
    is_processed         = Column(Boolean, default=False, nullable=False)

    # Flag: does the embedding need to be regenerated?
    embedding_needs_update = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship back to candidate profile
    candidate_profile = relationship("CandidateProfile")

    def __repr__(self):
        return f"<ResumeData id={self.id} candidate_profile_id={self.candidate_profile_id}>"


# ============================================================
# TABLE 2: embedding_metadata
# Tracks Pinecone vector IDs for both jobs and candidates.
# Tells us what is currently stored in Pinecone and when it was synced.
# ============================================================
class EmbeddingMetadata(Base):
    __tablename__ = "embedding_metadata"

    id            = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # The type of record this embedding belongs to (JOB or CANDIDATE)
    entity_type   = Column(Enum(EmbeddingType), nullable=False)

    # The ID of the entity in SQLite (job_id or candidate_profile_id)
    entity_id     = Column(Integer, nullable=False, index=True)

    # The vector ID stored in Pinecone (e.g. "job-5" or "candidate-12")
    vector_id     = Column(String(100), nullable=False, unique=True)

    # The dimension of the embedding (384 for all-MiniLM-L6-v2)
    dimension     = Column(Integer, default=384)

    # The model used to generate this embedding
    model_name    = Column(String(100), default="all-MiniLM-L6-v2")

    # Is this embedding currently in sync with the source data?
    is_synced     = Column(Boolean, default=True, nullable=False)

    # When was the vector last pushed to Pinecone?
    last_synced_at = Column(DateTime(timezone=True), nullable=True)

    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return (
            f"<EmbeddingMetadata id={self.id} "
            f"entity_type={self.entity_type} "
            f"entity_id={self.entity_id} "
            f"vector_id='{self.vector_id}'>"
        )


# ============================================================
# TABLE 3: candidate_matches
# Stores the final AI analysis result for one candidate vs one job.
# This is the core output of the Phase 5 matching engine.
#
# Final Score = (CV Similarity × 0.4)
#             + (Skill Match    × 0.4)
#             + (Experience     × 0.2)
# ============================================================
class CandidateMatch(Base):
    __tablename__ = "candidate_matches"

    id                   = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # The candidate being evaluated
    candidate_profile_id = Column(
        Integer,
        ForeignKey("candidate_profiles.id"),
        nullable=False,
        index=True
    )

    # The job being matched against
    job_id               = Column(
        Integer,
        ForeignKey("jobs.id"),
        nullable=False,
        index=True
    )

    # Individual scoring components (0.0 to 100.0)
    cv_similarity_score  = Column(Float, default=0.0)   # Cosine similarity of CV vs job
    skill_match_score    = Column(Float, default=0.0)   # % of required skills found in CV
    experience_score     = Column(Float, default=0.0)   # Experience level match

    # Weighted final score
    final_match_score    = Column(Float, default=0.0)

    # AI recommendation level based on final_match_score
    recommendation       = Column(Enum(RecommendationLevel), nullable=True)

    # JSON-style comma-separated lists
    matched_skills       = Column(Text, nullable=True)   # skills found in both CV and job
    missing_skills       = Column(Text, nullable=True)   # required skills absent from CV
    strengths            = Column(Text, nullable=True)   # candidate's strong points
    weaknesses           = Column(Text, nullable=True)   # candidate's weak points

    # Short AI-generated summary
    ai_summary           = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    candidate_profile    = relationship("CandidateProfile")
    job                  = relationship("Job")

    def __repr__(self):
        return (
            f"<CandidateMatch id={self.id} "
            f"candidate={self.candidate_profile_id} "
            f"job={self.job_id} "
            f"score={self.final_match_score:.1f}>"
        )


# ============================================================
# TABLE 4: skill_analysis
# Stores per-skill breakdown for a candidate match.
# One row per skill that was checked against the job requirements.
# ============================================================
class SkillAnalysis(Base):
    __tablename__ = "skill_analysis"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Link to the parent match record
    match_id    = Column(
        Integer,
        ForeignKey("candidate_matches.id"),
        nullable=False,
        index=True
    )

    # The skill being evaluated
    skill_name  = Column(String(200), nullable=False)

    # Was this skill found in the candidate's CV?
    is_matched  = Column(Boolean, default=False)

    # How closely does the candidate's skill match? (0.0 to 1.0)
    # 1.0 = exact match, 0.8 = semantically similar
    similarity  = Column(Float, default=0.0)

    # Is this skill required or just preferred for the job?
    is_required = Column(Boolean, default=True)

    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship back to the match
    match       = relationship("CandidateMatch")

    def __repr__(self):
        return (
            f"<SkillAnalysis id={self.id} "
            f"skill='{self.skill_name}' "
            f"matched={self.is_matched} "
            f"similarity={self.similarity:.2f}>"
        )