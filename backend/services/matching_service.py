# ============================================================
# EXACT FILE LOCATION: backend/services/matching_service.py
# ============================================================
# PURPOSE: Phase 5 — Semantic candidate-to-job matching engine.
#
# Scoring Formula:
#   Final Score = (CV Similarity × 0.4)
#               + (Skill Match   × 0.4)
#               + (Experience    × 0.2)
#
# Workflow:
#   1. Load candidate resume data + job data from SQLite
#   2. Retrieve embeddings from Pinecone
#   3. Compute cosine similarity between CV and job vectors
#   4. Calculate skill match % using extracted skills
#   5. Estimate experience match
#   6. Compute weighted final score
#   7. Determine recommendation level
#   8. Generate strengths, weaknesses, AI summary
#   9. Save CandidateMatch + SkillAnalysis to SQLite
# ============================================================

import re
import logging
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException

from models.job import Job
from models.application import CandidateProfile, Application
from models.ai_models import (
    ResumeData, CandidateMatch, SkillAnalysis, RecommendationLevel
)
from services.pinecone_service import pinecone_service
from utils.skill_extractor import (
    find_matched_skills,
    find_missing_skills,
    calculate_skill_match_percentage,
    extract_experience_from_text,
)
from utils.text_cleaner import parse_skills_list

logger = logging.getLogger(__name__)


# ============================================================
# Compute cosine similarity between two embedding vectors.
# Both vectors are 384-dim float lists from all-MiniLM-L6-v2.
# Returns a value between 0.0 (no similarity) and 1.0 (identical).
# ============================================================
def cosine_similarity(vec_a: list, vec_b: list) -> float:
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)

    dot_product = np.dot(a, b)
    norm_a      = np.linalg.norm(a)
    norm_b      = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


# ============================================================
# Estimate experience match score (0 to 100)
# Compares years mentioned in resume vs job requirement
# ============================================================
def estimate_experience_score(
    resume_experience: str,
    job_experience: str
) -> float:
    if not job_experience:
        return 80.0  # No requirement = neutral score

    # Extract years from both strings
    def extract_years(text: str) -> int:
        if not text:
            return 0
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else 0

    required_years  = extract_years(job_experience)
    candidate_years = extract_years(resume_experience)

    if required_years == 0:
        return 80.0

    if candidate_years >= required_years:
        return 100.0
    elif candidate_years == 0:
        return 30.0
    else:
        # Partial credit based on ratio
        ratio = candidate_years / required_years
        return round(ratio * 100, 2)


# ============================================================
# Determine recommendation level from final score
# ============================================================
def get_recommendation_level(score: float) -> RecommendationLevel:
    if score >= 80.0:
        return RecommendationLevel.HIGHLY_RECOMMENDED
    elif score >= 60.0:
        return RecommendationLevel.RECOMMENDED
    elif score >= 40.0:
        return RecommendationLevel.NEEDS_IMPROVEMENT
    else:
        return RecommendationLevel.NOT_RECOMMENDED


# ============================================================
# Generate human-readable strengths list from match data
# ============================================================
def generate_strengths(
    matched_skills: list,
    cv_similarity: float,
    experience_score: float
) -> list:
    strengths = []

    if len(matched_skills) > 0:
        strengths.append(
            f"Possesses {len(matched_skills)} of the required skills: "
            f"{', '.join(matched_skills[:5])}"
        )
    if cv_similarity >= 0.7:
        strengths.append("Strong alignment between CV profile and job requirements")
    if experience_score >= 80.0:
        strengths.append("Meets or exceeds the experience requirements")
    if len(matched_skills) >= 5:
        strengths.append("Broad technical skill coverage")

    return strengths if strengths else ["Candidate has some relevant background"]


# ============================================================
# Generate human-readable weaknesses list from match data
# ============================================================
def generate_weaknesses(
    missing_skills: list,
    cv_similarity: float,
    experience_score: float
) -> list:
    weaknesses = []

    if len(missing_skills) > 0:
        weaknesses.append(
            f"Missing {len(missing_skills)} required skill(s): "
            f"{', '.join(missing_skills[:5])}"
        )
    if cv_similarity < 0.4:
        weaknesses.append("CV profile has low semantic match with job description")
    if experience_score < 50.0:
        weaknesses.append("May not meet the required experience level")

    return weaknesses if weaknesses else ["No significant gaps identified"]


# ============================================================
# Generate a short AI summary from the match data
# ============================================================
def generate_ai_summary(
    candidate_name: str,
    job_title: str,
    final_score: float,
    recommendation: RecommendationLevel,
    matched_count: int,
    missing_count: int
) -> str:
    rec_text = recommendation.value.replace("_", " ").title()
    return (
        f"{candidate_name} achieved a match score of {final_score:.1f}% "
        f"for the {job_title} position. "
        f"They matched {matched_count} required skill(s) and are missing {missing_count}. "
        f"Overall assessment: {rec_text}."
    )


# ============================================================
# MAIN MATCHING FUNCTION
# Runs the complete matching pipeline for one candidate + job
# ============================================================
def run_candidate_job_match(
    db: Session,
    candidate_profile_id: int,
    job_id: int,
    force_recalculate: bool = False
) -> CandidateMatch:

    # Check if match result already exists
    existing_match = (
        db.query(CandidateMatch)
        .filter(
            CandidateMatch.candidate_profile_id == candidate_profile_id,
            CandidateMatch.job_id               == job_id
        )
        .first()
    )

    if existing_match and not force_recalculate:
        logger.info(
            f"Match already exists for candidate={candidate_profile_id} "
            f"job={job_id} — returning cached result"
        )
        return existing_match

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

    # Load resume data (must be processed first)
    resume_data = db.query(ResumeData).filter(
        ResumeData.candidate_profile_id == candidate_profile_id
    ).first()
    if not resume_data or not resume_data.is_processed:
        raise HTTPException(
            status_code=400,
            detail="Resume not processed. Run POST /resume/process first."
        )

    # ============================================================
    # SCORING COMPONENT 1: CV Semantic Similarity (weight: 40%)
    # Fetch both embeddings from Pinecone and compute cosine similarity
    # ============================================================
    candidate_vector_id = f"candidate-{candidate_profile_id}"
    job_vector_id       = f"job-{job_id}"

    cv_similarity_score = 0.0

    try:
        # Fetch candidate vector from Pinecone
        candidate_vector_data = pinecone_service.fetch_vector(candidate_vector_id)
        job_vector_data       = pinecone_service.fetch_vector(job_vector_id)

        if candidate_vector_data and job_vector_data:
            candidate_values = candidate_vector_data.get("values", [])
            job_values       = job_vector_data.get("values", [])

            if candidate_values and job_values:
                # Compute cosine similarity and scale to 0-100
                similarity           = cosine_similarity(candidate_values, job_values)
                cv_similarity_score  = round(similarity * 100, 2)
                logger.info(f"Cosine similarity: {cv_similarity_score:.2f}%")
        else:
            logger.warning(
                "Could not fetch vectors from Pinecone. "
                "Make sure embeddings are generated first."
            )
    except Exception as e:
        logger.error(f"Pinecone similarity computation failed: {e}")
        # Continue with 0 score rather than failing completely

    # ============================================================
    # SCORING COMPONENT 2: Skill Match (weight: 40%)
    # Compare required skills from job vs extracted skills from resume
    # ============================================================
    skill_match_score = calculate_skill_match_percentage(
        job.required_skills or "",
        resume_data.extracted_skills or ""
    )

    matched_skills = find_matched_skills(
        job.required_skills or "",
        resume_data.extracted_skills or ""
    )
    missing_skills = find_missing_skills(
        job.required_skills or "",
        resume_data.extracted_skills or ""
    )

    logger.info(
        f"Skill match: {skill_match_score:.1f}% | "
        f"matched={len(matched_skills)} missing={len(missing_skills)}"
    )

    # ============================================================
    # SCORING COMPONENT 3: Experience Match (weight: 20%)
    # Compare experience requirement with candidate's experience
    # ============================================================
    experience_score = estimate_experience_score(
        resume_data.extracted_experience or "",
        job.experience or ""
    )
    logger.info(f"Experience score: {experience_score:.1f}%")

    # ============================================================
    # FINAL WEIGHTED SCORE
    # Formula: (CV × 0.4) + (Skills × 0.4) + (Experience × 0.2)
    # ============================================================
    final_score = round(
        (cv_similarity_score * 0.4)
        + (skill_match_score * 0.4)
        + (experience_score  * 0.2),
        2
    )
    logger.info(f"Final match score: {final_score:.2f}%")

    # ============================================================
    # AI ANALYSIS: recommendation, strengths, weaknesses, summary
    # ============================================================
    recommendation = get_recommendation_level(final_score)
    strengths      = generate_strengths(matched_skills, cv_similarity_score / 100, experience_score)
    weaknesses     = generate_weaknesses(missing_skills, cv_similarity_score / 100, experience_score)
    ai_summary     = generate_ai_summary(
        profile.full_name,
        job.title,
        final_score,
        recommendation,
        len(matched_skills),
        len(missing_skills)
    )

    # Convert lists to comma-separated strings for storage
    matched_str   = ", ".join(matched_skills)
    missing_str   = ", ".join(missing_skills)
    strengths_str = " | ".join(strengths)
    weakness_str  = " | ".join(weaknesses)

    # ============================================================
    # Save match result to SQLite
    # ============================================================
    if existing_match:
        # Update existing record
        existing_match.cv_similarity_score = cv_similarity_score
        existing_match.skill_match_score   = skill_match_score
        existing_match.experience_score    = experience_score
        existing_match.final_match_score   = final_score
        existing_match.recommendation      = recommendation
        existing_match.matched_skills      = matched_str
        existing_match.missing_skills      = missing_str
        existing_match.strengths           = strengths_str
        existing_match.weaknesses          = weakness_str
        existing_match.ai_summary          = ai_summary
        match_record = existing_match
    else:
        match_record = CandidateMatch(
            candidate_profile_id = candidate_profile_id,
            job_id               = job_id,
            cv_similarity_score  = cv_similarity_score,
            skill_match_score    = skill_match_score,
            experience_score     = experience_score,
            final_match_score    = final_score,
            recommendation       = recommendation,
            matched_skills       = matched_str,
            missing_skills       = missing_str,
            strengths            = strengths_str,
            weaknesses           = weakness_str,
            ai_summary           = ai_summary,
        )
        db.add(match_record)

    db.flush()  # Get match_record.id before saving skill analysis

    # Save per-skill analysis rows
    if match_record.id:
        # Delete old skill analysis rows if recalculating
        db.query(SkillAnalysis).filter(
            SkillAnalysis.match_id == match_record.id
        ).delete()

    required_skills_list = parse_skills_list(job.required_skills or "")
    candidate_skills_set = set(
        s.lower().strip()
        for s in parse_skills_list(resume_data.extracted_skills or "")
    )

    for skill in required_skills_list:
        is_matched = skill.lower().strip() in candidate_skills_set
        skill_row  = SkillAnalysis(
            match_id    = match_record.id,
            skill_name  = skill,
            is_matched  = is_matched,
            similarity  = 1.0 if is_matched else 0.0,
            is_required = True
        )
        db.add(skill_row)

    db.commit()
    db.refresh(match_record)

    logger.info(
        f"Match saved: candidate={candidate_profile_id} "
        f"job={job_id} final_score={final_score:.1f}% "
        f"recommendation={recommendation}"
    )

    # ============================================================
    # AUTO-TRIGGER INTERVIEW GENERATION
    # After matching completes, automatically generate interview
    # questions for this candidate so they can start immediately.
    # Uses lazy import to avoid circular dependency.
    # ============================================================
    _auto_trigger_interview(db, candidate_profile_id, job_id)

    return match_record


# ============================================================
# Run matching for ALL candidates who applied to a job
# ============================================================
def run_bulk_job_matching(db: Session, job_id: int, force: bool = False) -> dict:

    # Get all applications for this job
    applications = (
        db.query(Application)
        .filter(Application.job_id == job_id)
        .all()
    )

    if not applications:
        return {
            "job_id":           job_id,
            "total_candidates": 0,
            "processed":        0,
            "failed":           0,
            "results":          []
        }

    results = []
    failed  = 0

    for app in applications:
        try:
            match = run_candidate_job_match(
                db,
                app.candidate_id,
                job_id,
                force_recalculate=force
            )
            results.append(match)
        except Exception as e:
            logger.error(
                f"Match failed for candidate={app.candidate_id} "
                f"job={job_id}: {e}"
            )
            failed += 1

    return {
        "job_id":           job_id,
        "total_candidates": len(applications),
        "processed":        len(results),
        "failed":           failed,
        "results":          results
    }


# ============================================================
# Get existing match result for one candidate + job (read-only)
# ============================================================
def get_match_result(
    db: Session,
    candidate_profile_id: int,
    job_id: int
) -> CandidateMatch:
    match = (
        db.query(CandidateMatch)
        .options(
            joinedload(CandidateMatch.candidate_profile),
            joinedload(CandidateMatch.job)
        )
        .filter(
            CandidateMatch.candidate_profile_id == candidate_profile_id,
            CandidateMatch.job_id               == job_id
        )
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=404,
            detail="No match result found. Run POST /matching/run first."
        )
    return match


# ============================================================
# Get all match results for a job, sorted by score (best first)
# ============================================================
def get_job_match_results(db: Session, job_id: int) -> list:
    return (
        db.query(CandidateMatch)
        .options(
            joinedload(CandidateMatch.candidate_profile),
            joinedload(CandidateMatch.job)
        )
        .filter(CandidateMatch.job_id == job_id)
        .order_by(CandidateMatch.final_match_score.desc())
        .all()
    )


# ============================================================
# AUTO-TRIGGER INTERVIEW AFTER MATCHING
# Called at the end of run_candidate_job_match() so questions
# are generated automatically without any admin action.
# ============================================================
def _auto_trigger_interview(db, candidate_profile_id: int, job_id: int):
    """
    Automatically generate interview questions after matching.
    Imported lazily to avoid circular imports.
    """
    try:
        from services.interview_service import auto_generate_interview
        auto_generate_interview(db, candidate_profile_id, job_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"Auto interview generation failed for "
            f"candidate={candidate_profile_id} job={job_id}: {e}"
        )