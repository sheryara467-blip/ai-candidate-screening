# ============================================================
# EXACT FILE LOCATION: backend/api/voice.py
# ============================================================
# PURPOSE: Phase 7 — Voice system endpoints.
#
# Routes:
#   POST /voice/question-audio/{question_id}   → TTS
#   POST /voice/transcribe                     → Whisper STT
# ============================================================

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from database.database import get_db
from schemas.interview_schemas import TTSResponse, TranscribeResponse
from models.interview_models   import InterviewQuestion
import services.voice_service         as voice_svc
import services.transcription_service as transcription_svc
import services.interview_service     as interview_svc
from fastapi import HTTPException

router = APIRouter(prefix="/voice", tags=["Phase 7 - Voice System"])


# ============================================================
# POST /voice/question-audio/{question_id}
# Generate TTS audio for an interview question.
# Returns the URL of the audio file to play in the browser.
# ============================================================
@router.post("/question-audio/{question_id}", response_model=TTSResponse)
def generate_question_audio(question_id: int, db: Session = Depends(get_db)):
    """
    Convert an interview question's text to speech using gTTS.
    Saves the MP3 file and returns a playable URL.
    """
    # Load the question from DB
    question = db.query(InterviewQuestion).filter(
        InterviewQuestion.id == question_id
    ).first()

    if not question:
        raise HTTPException(status_code=404, detail=f"Question {question_id} not found")

    # Generate the audio file
    audio_path = voice_svc.generate_question_audio(question_id, question.question_text)

    # Save path back to question record
    question.audio_path = audio_path
    db.commit()

    # Build the public URL for the audio file
    audio_url = voice_svc.get_audio_url(audio_path)

    return TTSResponse(
        question_id = question_id,
        audio_url   = audio_url,
        message     = "Audio generated successfully"
    )


# ============================================================
# POST /voice/transcribe
# Transcribe a candidate's voice recording using Whisper.
# Saves the answer text to the interview answer record.
# ============================================================
@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_voice_answer(
    session_id  : int        = Form(...),
    question_id : int        = Form(...),
    file        : UploadFile = File(...),
    db          : Session    = Depends(get_db)
):
    """
    Accept a voice recording, transcribe it with Whisper,
    and save the transcript as the candidate's answer.
    """
    # Save the uploaded audio file to disk
    audio_path = await transcription_svc.save_audio_file(file, session_id, question_id)

    # Transcribe using Whisper
    transcript = transcription_svc.transcribe_audio(audio_path)

    if not transcript:
        raise HTTPException(
            status_code=422,
            detail="Could not transcribe audio. Please try again or use text input."
        )

    # Save the transcribed answer using interview service
    interview_svc.save_answer(
        db          = db,
        session_id  = session_id,
        question_id = question_id,
        answer_text = transcript,
        answer_type = "VOICE",
        audio_path  = audio_path,
    )

    return TranscribeResponse(
        question_id = question_id,
        session_id  = session_id,
        transcript  = transcript,
        audio_path  = audio_path,
        message     = "Voice answer transcribed and saved successfully"
    )