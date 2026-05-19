# ============================================================
# models/candidate.py
# SQLAlchemy ORM models for Candidate, Score, and Recommendation.
# These tables store all candidate screening results in SQLite.
# ============================================================

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.database import Base
import enum


# ============================================================
# Enum for application status values
# ============================================================
class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    INTERVIEW_PENDING = "INTERVIEW_PENDING"
    INTERVIEW_DONE = "INTERVIEW_DONE"


# ============================================================
# Recommendation level based on final score
# Scoring logic: 80%+ = Highly Recommended, 60-79% = Recommended,
# 40-59% = Needs Improvement, <40% = Not Recommended
# ============================================================
class RecommendationLevel(str, enum.Enum):
    HIGHLY_RECOMMENDED = "HIGHLY_RECOMMENDED"
    RECOMMENDED = "RECOMMENDED"
    NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


# ============================================================
# Candidate table: stores candidate profile and application data
# ============================================================
class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Which job this candidate applied for
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)

    # Candidate personal information
    name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, index=True)

    # Path to stored CV file (relative to uploads directory)
    cv_file_path = Column(String(500), nullable=True)

    # Extracted raw text from CV (used for embedding generation)
    cv_extracted_text = Column(Text, nullable=True)

    # Comma-separated list of skills extracted from CV
    extracted_skills = Column(Text, nullable=True)

    # Comma-separated skills that are required but missing from CV
    missing_skills = Column(Text, nullable=True)

    # AI match percentage — synced from CandidateMatch after screening
    match_percentage = Column(Float, nullable=True)

    # Pinecone vector ID for this candidate's CV embedding
    cv_vector_id = Column(String(100), nullable=True)

    # Current application lifecycle status
    status = Column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.PENDING,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    job = relationship("Job", back_populates="candidates")
    score = relationship("Score", back_populates="candidate", uselist=False)
    recommendation = relationship("Recommendation", back_populates="candidate", uselist=False)

    def __repr__(self):
        return f"<Candidate id={self.id} name='{self.name}' job_id={self.job_id}>"


# ============================================================
# Score table: stores all scoring components per candidate
# Final Score = (CV × 0.3) + (Skill Match × 0.4) + (Interview × 0.3)
# ============================================================
class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Link score to one candidate
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, unique=True)

    # Component scores (0.0 to 100.0)
    cv_score = Column(Float, default=0.0, nullable=False)
    skill_match_score = Column(Float, default=0.0, nullable=False)
    interview_score = Column(Float, default=0.0, nullable=False)

    # Computed final score: (cv × 0.3) + (skill × 0.4) + (interview × 0.3)
    final_score = Column(Float, default=0.0, nullable=False)

    # Skill match percentage (how many required skills candidate has)
    match_percentage = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Back-reference to candidate
    candidate = relationship("Candidate", back_populates="score")

    def __repr__(self):
        return f"<Score id={self.id} candidate_id={self.candidate_id} final={self.final_score:.1f}>"


# ============================================================
# Recommendation table: AI-generated recommendation per candidate
# ============================================================
class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Link recommendation to one candidate
    candidate_id = Column(Integer, ForeignKey("candidates.id"), nullable=False, unique=True)

    # Computed recommendation level based on final score
    level = Column(Enum(RecommendationLevel), nullable=False)

    # AI-generated text summary of the recommendation
    summary = Column(Text, nullable=True)

    # Structured strengths and weaknesses extracted by AI
    strengths = Column(Text, nullable=True)
    weaknesses = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Back-reference to candidate
    candidate = relationship("Candidate", back_populates="recommendation")

    def __repr__(self):
        return f"<Recommendation id={self.id} level='{self.level}'>"