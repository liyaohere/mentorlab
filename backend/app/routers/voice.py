import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.participant import Participant
from app.services.storage_service import storage_service
from app.services.whisper_service import whisper_service

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# Max audio file size: 25MB (Whisper API limit)
MAX_AUDIO_SIZE = 25 * 1024 * 1024

ALLOWED_AUDIO_TYPES = {
    "audio/mp4", "audio/m4a", "audio/mpeg", "audio/ogg",
    "audio/opus", "audio/webm", "audio/wav", "audio/x-wav",
    "audio/aac", "audio/x-m4a",
}


class TranscribeResponse(BaseModel):
    transcript: str
    audio_url: str | None = None


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    audio: UploadFile = File(...),
    conversation_id: str = Form(default=""),
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an audio file, transcribe it via Whisper, and optionally store in S3.
    Returns the transcript text for the client to review before sending as a message.
    """
    # Validate content type
    if audio.content_type and audio.content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. Use m4a, mp3, ogg, wav, or webm.",
        )

    # Check file size (read first chunk to estimate)
    contents = await audio.read()
    if len(contents) > MAX_AUDIO_SIZE:
        raise HTTPException(status_code=400, detail="Audio file too large (max 25MB)")
    await audio.seek(0)

    # 1. Upload to S3 (if configured) — do this first so audio.seek(0) resets for Whisper
    audio_url = None
    if conversation_id:
        audio_url = await storage_service.upload_audio(
            audio, str(participant.id), conversation_id,
        )

    # 2. Transcribe via Whisper
    transcript = await whisper_service.transcribe(audio)

    return TranscribeResponse(transcript=transcript, audio_url=audio_url)
