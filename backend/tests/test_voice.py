import io
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _get_token(client: AsyncClient) -> str:
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "invite_code": "TEST001A",
            "name": "Test User",
            "venture_name": "Test Venture",
        },
    )
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_transcribe_audio(client: AsyncClient, seed_invite_codes, mock_claude):
    token = await _get_token(client)

    # Mock Whisper service to return a deterministic transcript
    async def fake_transcribe(self, audio_file):
        return "This is a test transcription from voice input."

    with patch(
        "app.services.whisper_service.WhisperService.transcribe", fake_transcribe
    ):
        # Create a small fake audio file
        audio_data = (
            b"\x00" * 1024
        )  # 1KB of zeros (not real audio, but Whisper is mocked)
        response = await client.post(
            "/api/v1/voice/transcribe",
            files={"audio": ("test.m4a", io.BytesIO(audio_data), "audio/m4a")},
            data={"conversation_id": ""},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["transcript"] == "This is a test transcription from voice input."
    assert data["audio_url"] is None  # S3 not configured in tests


@pytest.mark.asyncio
async def test_transcribe_rejects_invalid_type(
    client: AsyncClient, seed_invite_codes, mock_claude
):
    token = await _get_token(client)

    response = await client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("test.txt", io.BytesIO(b"not audio"), "text/plain")},
        data={"conversation_id": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_transcribe_unauthenticated(client: AsyncClient):
    audio_data = b"\x00" * 100
    response = await client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("test.m4a", io.BytesIO(audio_data), "audio/m4a")},
    )
    assert response.status_code == 401
