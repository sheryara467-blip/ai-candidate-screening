# ============================================================
# EXACT FILE LOCATION: backend/utils/skill_extractor.py
# ============================================================
# PURPOSE: Extract skills, education, and experience from
# cleaned resume text using pattern matching and keyword lists.
#
# This is a rule-based extractor — Phase 6 can upgrade it to
# an NER (Named Entity Recognition) model if needed.
# ============================================================

import re
import logging
from utils.text_cleaner import normalize_skill, parse_skills_list

logger = logging.getLogger(__name__)


# ============================================================
# Technology and skill keyword dictionary
# Add more keywords here as needed
# ============================================================
TECH_SKILLS_KEYWORDS = [
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "php",
    "ruby", "swift", "kotlin", "go", "rust", "scala", "r", "matlab",
    "bash", "shell", "perl",

    # Web frameworks
    "react", "nextjs", "next.js", "vue", "angular", "django", "flask",
    "fastapi", "spring", "laravel", "express", "nodejs", "node.js",

    # Databases
    "sql", "mysql", "postgresql", "mongodb", "sqlite", "redis",
    "cassandra", "oracle", "dynamodb", "firebase",

    # Cloud + DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "jenkins",
    "terraform", "ansible", "ci/cd", "linux", "git", "github",

    # AI/ML
    "machine learning", "deep learning", "nlp", "tensorflow", "pytorch",
    "scikit-learn", "keras", "pandas", "numpy", "opencv",
    "transformers", "huggingface", "langchain", "pinecone",

    # General tech
    "rest api", "graphql", "microservices", "agile", "scrum",
    "html", "css", "tailwind", "bootstrap",
]

# Education level keywords
EDUCATION_KEYWORDS = [
    "bachelor", "master", "phd", "doctorate", "bsc", "msc", "mba",
    "diploma", "associate", "degree", "university", "college",
    "institute", "engineering", "computer science", "information technology",
]

# Experience level indicators
EXPERIENCE_PATTERNS = [
    r"(\d+)\+?\s*years?\s+(?:of\s+)?experience",
    r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:work|professional|industry)",
    r"experience\s+of\s+(\d+)\+?\s*years?",
]


# ============================================================
# Extract skills from resume text
# Matches against known tech keywords
# Also handles comma-separated skills lists found in the text
# ============================================================
def extract_skills_from_text(text: str) -> list:
    if not text:
        return []

    text_lower = text.lower()
    found_skills = set()

    # Match against known technology keywords
    for skill in TECH_SKILLS_KEYWORDS:
        # Use word boundary matching to avoid partial matches
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill.title() if len(skill) > 2 else skill.upper())

    logger.debug(f"Extracted {len(found_skills)} skills from text")
    return sorted(list(found_skills))


# ============================================================
# Extract education info from text
# Returns the most relevant education line found
# ============================================================
def extract_education_from_text(text: str) -> str:
    if not text:
        return ""

    lines = text.split(".")
    education_lines = []

    for line in lines:
        line_lower = line.lower()
        for keyword in EDUCATION_KEYWORDS:
            if keyword in line_lower:
                cleaned = line.strip()
                if cleaned and len(cleaned) > 10:
                    education_lines.append(cleaned)
                break

    # Return top 3 most relevant education lines
    return " | ".join(education_lines[:3]) if education_lines else ""


# ============================================================
# Extract years of experience from text
# Returns the highest number of years mentioned
# ============================================================
def extract_experience_from_text(text: str) -> str:
    if not text:
        return ""

    max_years = 0
    found_text = ""

    for pattern in EXPERIENCE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            years = int(match) if isinstance(match, str) else int(match[0])
            if years > max_years:
                max_years = years

    if max_years > 0:
        found_text = f"{max_years}+ years of experience"

    return found_text


# ============================================================
# Extract certifications from text
# Looks for certification keywords and acronyms
# ============================================================
def extract_certifications_from_text(text: str) -> str:
    if not text:
        return ""

    cert_patterns = [
        r"\b(AWS\s+Certified[^\.\,\n]*)",
        r"\b(Google\s+Certified[^\.\,\n]*)",
        r"\b(Microsoft\s+Certified[^\.\,\n]*)",
        r"\b(PMP[^\.\,\n]*)",
        r"\b(Scrum\s+Master[^\.\,\n]*)",
        r"\b(CISSP[^\.\,\n]*)",
        r"\b(CPA[^\.\,\n]*)",
        r"\b(Oracle\s+Certified[^\.\,\n]*)",
        r"\b([A-Z]{2,5}\s*certification[^\.\,\n]*)",
    ]

    found_certs = []
    for pattern in cert_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        found_certs.extend([m.strip() for m in matches if m.strip()])

    # Deduplicate and return
    unique_certs = list(dict.fromkeys(found_certs))
    return ", ".join(unique_certs[:5])  # limit to 5 certifications


# ============================================================
# Find missing skills: required skills not found in candidate text
# Compares job required_skills against candidate extracted_skills
# ============================================================
def find_missing_skills(required_skills_str: str, candidate_skills_str: str) -> list:
    required  = set(normalize_skill(s) for s in parse_skills_list(required_skills_str))
    candidate = set(normalize_skill(s) for s in parse_skills_list(candidate_skills_str))
    missing   = required - candidate
    return sorted(list(missing))


# ============================================================
# Find matched skills: skills present in BOTH job and candidate
# ============================================================
def find_matched_skills(required_skills_str: str, candidate_skills_str: str) -> list:
    required  = set(normalize_skill(s) for s in parse_skills_list(required_skills_str))
    candidate = set(normalize_skill(s) for s in parse_skills_list(candidate_skills_str))
    matched   = required & candidate
    return sorted(list(matched))


# ============================================================
# Calculate skill match percentage
# Returns 0.0 to 100.0
# ============================================================
def calculate_skill_match_percentage(
    required_skills_str: str,
    candidate_skills_str: str
) -> float:
    required = parse_skills_list(required_skills_str)
    if not required:
        return 0.0

    required_normalized  = set(normalize_skill(s) for s in required)
    candidate_normalized = set(normalize_skill(s) for s in parse_skills_list(candidate_skills_str))

    matched_count = len(required_normalized & candidate_normalized)
    return round((matched_count / len(required_normalized)) * 100, 2)