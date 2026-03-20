import logging
import uuid
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None and settings.S3_ENDPOINT_URL:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT_URL,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            )
        return self._client

    async def upload_audio(
        self,
        audio_file: UploadFile,
        participant_id: str,
        conversation_id: str,
    ) -> str | None:
        """Upload audio to S3-compatible storage. Returns the object URL, or None if storage not configured."""
        if not self.client:
            logger.warning("S3 storage not configured — skipping audio upload")
            return None

        audio_bytes = await audio_file.read()
        # Reset file position so it can be read again (for Whisper)
        await audio_file.seek(0)

        # Build key: participant_id/conversation_id/timestamp_uuid.ext
        ext_map = {
            "audio/mp4": "m4a",
            "audio/m4a": "m4a",
            "audio/mpeg": "mp3",
            "audio/ogg": "ogg",
            "audio/opus": "ogg",
            "audio/webm": "webm",
            "audio/wav": "wav",
        }
        ext = ext_map.get(audio_file.content_type, "m4a")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        key = f"audio/{participant_id}/{conversation_id}/{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"

        try:
            self.client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=key,
                Body=audio_bytes,
                ContentType=audio_file.content_type or "audio/m4a",
            )
            url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{key}"
            logger.info(f"Audio uploaded: {key} ({len(audio_bytes)} bytes)")
            return url
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            # Don't fail the request — audio storage is secondary to transcription
            return None


storage_service = StorageService()
