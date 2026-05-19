# ============================================================
# EXACT FILE LOCATION: backend/utils/audio_utils.py
# ============================================================
# PURPOSE: Audio directory management and file helpers.
# ============================================================

import os
import uuid
import logging

logger = logging.getLogger(__name__)

AUDIO_DIR         = "audio"
RECORDINGS_DIR    = os.path.join(AUDIO_DIR, "recordings")   # candidate voice answers
QUESTIONS_DIR     = os.path.join(AUDIO_DIR, "questions")    # TTS question audio


def ensure_audio_dirs():
    """Create audio directories if they don't exist."""
    os.makedirs(RECORDINGS_DIR, exist_ok=True)
    os.makedirs(QUESTIONS_DIR,  exist_ok=True)
    logger.info("Audio directories ready")


def get_question_audio_path(question_id: int) -> str:
    """Return file path for a TTS question audio file."""
    ensure_audio_dirs()
    return os.path.join(QUESTIONS_DIR, f"question_{question_id}.mp3")


def get_recording_path(session_id: int, question_id: int) -> str:
    """Return file path for a candidate voice recording."""
    ensure_audio_dirs()
    unique = uuid.uuid4().hex[:8]
    return os.path.join(RECORDINGS_DIR, f"session_{session_id}_q{question_id}_{unique}.webm")


def allowed_audio_file(filename: str) -> bool:
    """Check if uploaded file is an accepted audio format."""
    allowed = {".webm", ".mp3", ".wav", ".ogg", ".m4a"}
    _, ext  = os.path.splitext(filename or "")
    return ext.lower() in allowed