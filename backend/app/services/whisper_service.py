import logging
from pathlib import Path
from tempfile import NamedTemporaryFile

import httpx
from fastapi import HTTPException, UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

WHISPER_API_URL = "https://api.openai.com/v1/audio/transcriptions"


class WhisperService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def transcribe(self, audio_file: UploadFile) -> str:
        """Transcribe audio file using OpenAI Whisper API. Returns transcript text."""
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=503, detail="Whisper API not configured")

        audio_bytes = await audio_file.read()

        # Determine file extension from content type
        ext_map = {
            "audio/mp4": "m4a",
            "audio/m4a": "m4a",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/opus": "ogg",
            "audio/webm": "webm",
            "audio/wav": "wav",
            "audio/x-wav": "wav",
        }
        # Strip codec parameters (e.g., "audio/webm;codecs=opus" -> "audio/webm")
        base_type = (audio_file.content_type or "").split(";")[0].strip()
        ext = ext_map.get(base_type, "webm")
        filename = f"audio.{ext}"

        try:
            response = await self.client.post(
                WHISPER_API_URL,
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                files={
                    "file": (
                        filename,
                        audio_bytes,
                        audio_file.content_type or "audio/m4a",
                    )
                },
                data={
                    "model": "whisper-1",
                    "language": "en",  # Hint: English, but handles code-switching
                    "response_format": "text",
                },
            )
            response.raise_for_status()
            transcript = response.text.strip()
            logger.info(
                f"Whisper transcription: {len(audio_bytes)} bytes -> {len(transcript)} chars"
            )
            return transcript

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Whisper API error: {e.response.status_code} {e.response.text}"
            )
            raise HTTPException(
                status_code=502,
                detail="Speech transcription service temporarily unavailable.",
            )
        except httpx.RequestError as e:
            logger.error(f"Whisper API connection error: {e}")
            raise HTTPException(
                status_code=502,
                detail="Could not reach speech transcription service.",
            )


whisper_service = WhisperService()
