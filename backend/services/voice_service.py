# ============================================================
# EXACT FILE LOCATION: backend/services/voice_service.py
# ============================================================
# PURPOSE: Phase 7 — Text-to-Speech for interview questions.
# Uses gTTS to convert question text → MP3 audio file.
# The audio file is saved to /audio/questions/ and served
# as a static file so the frontend can play it.
# ============================================================

import os
import logging
from fastapi import HTTPException
from gtts import gTTS

from utils.audio_utils import get_question_audio_path, ensure_audio_dirs

logger = logging.getLogger(__name__)


# ============================================================
# Convert question text to speech and save as MP3
# Returns the relative file path to serve as static
# ============================================================
def generate_question_audio(question_id: int, text: str) -> str:
    ensure_audio_dirs()

    # Build the output file path
    audio_path = get_question_audio_path(question_id)

    # Skip regeneration if file already exists
    if os.path.exists(audio_path):
        logger.info(f"Audio already exists for question {question_id}: {audio_path}")
        return audio_path

    try:
        # Generate TTS audio using gTTS
        # lang='en' — English, slow=False for natural speed
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(audio_path)
        logger.info(f"TTS audio generated: {audio_path} ({os.path.getsize(audio_path)} bytes)")
        return audio_path

    except Exception as e:
        logger.error(f"TTS generation failed for question {question_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate audio: {str(e)}"
        )


# ============================================================
# Get audio URL for a question
# Returns the URL path the frontend uses to play the audio
# ============================================================
def get_audio_url(audio_path: str) -> str:
    # Convert local path to URL served by FastAPI static mount
    # e.g. "audio/questions/question_1.mp3" → "/audio/question_1.mp3"
    filename = os.path.basename(audio_path)
    subdir   = "questions" if "questions" in audio_path else "recordings"
    return f"/audio/{subdir}/{filename}"