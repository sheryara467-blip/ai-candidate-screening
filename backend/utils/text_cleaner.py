# ============================================================
# EXACT FILE LOCATION: backend/utils/text_cleaner.py
# ============================================================
# PURPOSE: Clean and normalize extracted resume text before
# passing it to the embedding model.
# Raw PDF text often contains noise: extra spaces, special
# characters, page numbers, headers/footers.
# This module removes that noise to improve embedding quality.
# ============================================================

import re
import string
import logging

logger = logging.getLogger(__name__)


# ============================================================
# Master clean function — runs all cleaning steps in order
# Input:  raw text string from PDF extraction
# Output: clean normalized text ready for embedding
# ============================================================
def clean_resume_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    text = raw_text

    # Step 1: Normalize unicode characters to ASCII equivalents
    text = text.encode("ascii", errors="ignore").decode("ascii")

    # Step 2: Remove email addresses (privacy + noise reduction)
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # Step 3: Remove phone numbers (various formats)
    text = re.sub(r"[\+\(]?[1-9][0-9\-\(\)\s]{8,}[0-9]", " ", text)

    # Step 4: Remove URLs and web addresses
    text = re.sub(r"http\S+|www\.\S+", " ", text)

    # Step 5: Remove special characters but keep letters, digits, spaces
    text = re.sub(r"[^a-zA-Z0-9\s\-\./,]", " ", text)

    # Step 6: Remove standalone single characters (e.g. "a b c d")
    text = re.sub(r"\b[a-zA-Z]\b", " ", text)

    # Step 7: Remove excessive whitespace and normalize to single spaces
    text = re.sub(r"\s+", " ", text)

    # Step 8: Strip leading and trailing whitespace
    text = text.strip()

    logger.debug(f"Cleaned text: {len(raw_text)} chars → {len(text)} chars")
    return text


# ============================================================
# Extract section blocks from resume text
# Looks for common section headers to segment the resume
# Returns a dict with keys: skills, education, experience, certs
# ============================================================
def extract_sections(text: str) -> dict:
    sections = {
        "skills":           "",
        "education":        "",
        "experience":       "",
        "certifications":   "",
        "summary":          "",
    }

    if not text:
        return sections

    # Section header patterns (case-insensitive)
    section_patterns = {
        "skills": [
            r"(skills?|technical skills?|core competencies|technologies|stack)",
        ],
        "education": [
            r"(education|academic|qualification|degree|university|college)",
        ],
        "experience": [
            r"(experience|work history|employment|career|professional background)",
        ],
        "certifications": [
            r"(certif|certification|license|credential)",
        ],
        "summary": [
            r"(summary|profile|objective|about me|overview)",
        ],
    }

    # Split text into lines for section detection
    lines = text.split("\n")
    current_section = None

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # Check if this line is a section header
        matched_section = None
        for section_name, patterns in section_patterns.items():
            for pattern in patterns:
                if re.search(pattern, line_stripped, re.IGNORECASE):
                    # Only treat short lines as headers (< 50 chars)
                    if len(line_stripped) < 50:
                        matched_section = section_name
                        break
            if matched_section:
                break

        if matched_section:
            current_section = matched_section
        elif current_section:
            # Append line to current section
            sections[current_section] += " " + line_stripped

    # Clean each section
    for key in sections:
        sections[key] = clean_resume_text(sections[key])

    return sections


# ============================================================
# Normalize a skill string for comparison
# Lowercase, strip whitespace, remove punctuation
# e.g. "Python 3.x" → "python 3x"
# ============================================================
def normalize_skill(skill: str) -> str:
    skill = skill.lower().strip()
    skill = re.sub(r"[^\w\s]", "", skill)
    skill = re.sub(r"\s+", " ", skill).strip()
    return skill


# ============================================================
# Parse comma-separated skills string into a clean list
# ============================================================
def parse_skills_list(skills_str: str) -> list:
    if not skills_str:
        return []
    return [
        s.strip()
        for s in skills_str.split(",")
        if s.strip()
    ]