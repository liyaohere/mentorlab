import uuid
from unittest.mock import patch, AsyncMock

import pytest
from httpx import AsyncClient

from app.services.scheduler_service import set_session_factory


async def _register_and_consent(client: AsyncClient, code: str) -> str:
    """Register + consent → returns token."""
    r = await client.post("/api/v1/auth/register", json={
        "invite_code": code,
        "name": "Test User",
        "venture_name": "Test Venture",
        "industry_vertical": "Agriculture",
    })
    token = r.json()["access_token"]
    await client.post(
        "/api/v1/me/consent",
        json={"study_consent": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    return token


@pytest.mark.asyncio
async def test_admin_trigger_creates_conversations(client: AsyncClient, seed_invite_codes, mock_claude):
    """Test that manually triggering the scheduler creates system-initiated conversations."""
    # Register and consent all 3 test participants
    token1 = await _register_and_consent(client, "TEST001A")
    token2 = await _register_and_consent(client, "TEST002B")
    token3 = await _register_and_consent(client, "TEST003C")

    # Point scheduler at test DB
    from tests.conftest import TestSession
    set_session_factory(TestSession)

    # Trigger conversations for all
    with patch("app.services.notification_service.NotificationService.send_push", new_callable=AsyncMock) as mock_push:
        mock_push.return_value = None
        response = await client.post("/api/v1/admin/trigger/all")

    assert response.status_code == 200
    assert response.json()["status"] == "triggered"

    # Verify each participant now has a system-initiated conversation
    for token in [token1, token2, token3]:
        r = await client.get(
            "/api/v1/conversations",
            headers={"Authorization": f"Bearer {token}"},
        )
        convs = r.json()["conversations"]
        system_convs = [c for c in convs if c["initiated_by"] == "system"]
        assert len(system_convs) == 1
        assert system_convs[0]["week_number"] == 1


@pytest.mark.asyncio
async def test_admin_schedule_crud(client: AsyncClient):
    """Test getting and setting cohort schedules."""
    # Get default schedule
    r = await client.get("/api/v1/admin/schedule/pilot_2026")
    assert r.status_code == 200
    assert r.json()["day_of_week"] == "mon"

    # Update schedule
    r = await client.put("/api/v1/admin/schedule", json={
        "cohort_id": "pilot_2026",
        "day_of_week": "wed",
        "hour": 7,
        "minute": 30,
        "timezone": "UTC",
    })
    assert r.status_code == 200

    # Verify update
    r = await client.get("/api/v1/admin/schedule/pilot_2026")
    assert r.json()["day_of_week"] == "wed"
    assert r.json()["hour"] == 7
    assert r.json()["minute"] == 30


@pytest.mark.asyncio
async def test_notification_tracking(client: AsyncClient, seed_invite_codes, mock_claude):
    """Test marking notifications as delivered and opened."""
    token = await _register_and_consent(client, "TEST001A")

    # Create a conversation (generates a greeting message)
    r = await client.post("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    conv = r.json()

    # The notification tracking endpoints expect a valid notification ID.
    # Since we didn't go through the scheduler, test with a non-existent ID → 404
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/notifications/{fake_id}/delivered",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404

    r = await client.post(
        f"/api/v1/notifications/{fake_id}/opened",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
