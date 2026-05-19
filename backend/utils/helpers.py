# ============================================================
# utils/helpers.py
# Shared utility functions used across services.
# ============================================================

from models.candidate import RecommendationLevel


# ============================================================
# Determine recommendation level from final score
# Scoring thresholds from project strategy document:
#   80%+    → Highly Recommended
#   60–79%  → Recommended
#   40–59%  → Needs Improvement
#   Below 40% → Not Recommended
# ============================================================
def get_recommendation_level(final_score: float) -> RecommendationLevel:
    if final_score >= 80.0:
        return RecommendationLevel.HIGHLY_RECOMMENDED
    elif final_score >= 60.0:
        return RecommendationLevel.RECOMMENDED
    elif final_score >= 40.0:
        return RecommendationLevel.NEEDS_IMPROVEMENT
    else:
        return RecommendationLevel.NOT_RECOMMENDED


# ============================================================
# Calculate final composite score from component scores
# Formula: (CV × 0.3) + (Skill Match × 0.4) + (Interview × 0.3)
# ============================================================
def calculate_final_score(cv_score: float, skill_score: float, interview_score: float) -> float:
    return round(
        (cv_score * 0.3) + (skill_score * 0.4) + (interview_score * 0.3),
        2
    )


# ============================================================
# Parse skills from comma-separated string
# Returns a cleaned list of skill strings
# ============================================================
def parse_skills(skills_str: str) -> list[str]:
    if not skills_str:
        return []
    return [s.strip() for s in skills_str.split(",") if s.strip()]


# ============================================================
# Find missing skills: required skills not found in candidate skills
# Both inputs are comma-separated strings
# ============================================================
def find_missing_skills(required_skills_str: str, candidate_skills_str: str) -> list[str]:
    required = set(s.lower() for s in parse_skills(required_skills_str))
    candidate = set(s.lower() for s in parse_skills(candidate_skills_str))
    missing = required - candidate
    return sorted(list(missing))


# ============================================================
# Calculate skill match percentage
# Returns 0-100 float representing coverage
# ============================================================
def calculate_skill_match_percentage(required_skills_str: str, candidate_skills_str: str) -> float:
    required = parse_skills(required_skills_str)
    if not required:
        return 0.0
    candidate = set(s.lower() for s in parse_skills(candidate_skills_str))
    matched = sum(1 for skill in required if skill.lower() in candidate)
    return round((matched / len(required)) * 100, 2)