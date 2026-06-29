"""
Text-to-Speech Service: Converts AI text output to speech audio.

Uses OpenAI TTS API (tts-1 model) for high-quality voice output.
Falls back to empty response if API is unavailable.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class TTSService:
    """Generate speech audio from text using OpenAI TTS API."""

    async def synthesize(self, text: str) -> bytes:
        """Convert text to speech audio (MP3 bytes).

        Args:
            text: The text to speak

        Returns:
            MP3 audio bytes
        """
        if not settings.OPENAI_API_KEY:
            logger.warning("No OpenAI API key configured for TTS")
            return b""

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/audio/speech",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={
                        "model": settings.OPENAI_TTS_MODEL,
                        "input": text,
                        "voice": settings.OPENAI_TTS_VOICE,
                        "speed": settings.OPENAI_TTS_SPEED,
                        "response_format": "mp3",
                    },
                )
                response.raise_for_status()
                return response.content
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"TTS API error: {e.response.status_code} {e.response.text}"
                )
                return b""
            except httpx.RequestError as e:
                logger.error(f"TTS connection error: {e}")
                return b""


tts_service = TTSService()
