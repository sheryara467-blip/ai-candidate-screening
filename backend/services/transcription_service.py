# ============================================================
# EXACT FILE LOCATION: backend/services/transcription_service.py
# ============================================================
# PURPOSE: Phase 7 — Speech-to-text using OpenAI Whisper.
# Transcribes candidate voice recordings into text so they
# can be stored and evaluated like text answers.
#
# Workflow:
#   1. Receive audio file upload from frontend
#   2. Save audio to /audio/recordings/
#   3. Run Whisper model on the file
#   4. Return transcript text
# ============================================================

import os
import logging
from fastapi import HTTPException, UploadFile

from utils.audio_utils import get_recording_path, allowed_audio_file, ensure_audio_dirs

logger = logging.getLogger(__name__)

# Load Whisper model once at module level
# Use "base" for speed, "small" or "medium" for accuracy
_whisper_model = None

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            model_size   = os.getenv("WHISPER_MODEL", "base")
            _whisper_model = whisper.load_model(model_size)
            logger.info(f"Whisper model loaded: {model_size}")
        except ImportError:
            logger.error(
                "Whisper not installed. Run: pip install openai-whisper"
            )
            raise
    return _whisper_model


# ============================================================
# Save uploaded audio file to disk
# Returns the file path where the audio was saved
# ============================================================
async def save_audio_file(
    file: UploadFile,
    session_id: int,
    question_id: int
) -> str:
    ensure_audio_dirs()

    # Validate audio file type
    if not allowed_audio_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid audio format. Accepted: .webm, .mp3, .wav, .ogg, .m4a"
        )

    # Read file content
    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Audio file is empty")

    # Save to recordings directory
    save_path = get_recording_path(session_id, question_id)
    with open(save_path, "wb") as f:
        f.write(content)

    logger.info(f"Audio saved: {save_path} ({len(content)} bytes)")
    return save_path


# ============================================================
# Transcribe audio file using Whisper
# Returns the transcript text
# ============================================================
def transcribe_audio(audio_path: str) -> str:
    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found: {audio_path}"
        )

    try:
        model  = _get_whisper_model()

        # Run Whisper transcription
        # fp16=False ensures compatibility with CPU environments
        result = model.transcribe(audio_path, fp16=False)
        transcript = result.get("text", "").strip()

        logger.info(
            f"Transcribed {audio_path}: "
            f"{len(transcript)} characters"
        )
        return transcript

    except Exception as e:
        logger.error(f"Whisper transcription failed for {audio_path}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {str(e)}"
        )