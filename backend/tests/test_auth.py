import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_with_valid_code(client: AsyncClient, seed_invite_codes, mock_claude):
    response = await client.post("/api/v1/auth/register", json={
        "invite_code": "TEST001A",
        "name": "John Okello",
        "phone_number": "+256700123456",
        "venture_name": "Okello Farms",
        "venture_description": "Organic vegetable farming",
        "industry_vertical": "Agriculture",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["participant"]["name"] == "John Okello"
    assert data["participant"]["arm"] == "control"


@pytest.mark.asyncio
async def test_register_with_invalid_code(client: AsyncClient, seed_invite_codes, mock_claude):
    response = await client.post("/api/v1/auth/register", json={
        "invite_code": "INVALID1",
        "name": "Test User",
    })
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_register_with_used_code_returns_existing(client: AsyncClient, seed_invite_codes, mock_claude):
    # First registration
    r1 = await client.post("/api/v1/auth/register", json={
        "invite_code": "TEST002B",
        "name": "Mary Acan",
        "venture_name": "Acan Tech",
    })
    assert r1.status_code == 200
    participant_id_1 = r1.json()["participant_id"]

    # Second registration with same code (phone loss recovery)
    r2 = await client.post("/api/v1/auth/register", json={
        "invite_code": "TEST002B",
        "name": "Mary Acan",
    })
    assert r2.status_code == 200
    participant_id_2 = r2.json()["participant_id"]
    assert participant_id_1 == participant_id_2


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, seed_invite_codes, mock_claude):
    # Register first
    r = await client.post("/api/v1/auth/register", json={
        "invite_code": "TEST001A",
        "name": "Test User",
    })
    token = r.json()["access_token"]

    # Get profile
    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["name"] == "Test User"


@pytest.mark.asyncio
async def test_consent(client: AsyncClient, seed_invite_codes, mock_claude):
    # Register
    r = await client.post("/api/v1/auth/register", json={
        "invite_code": "TEST001A",
        "name": "Test User",
    })
    token = r.json()["access_token"]

    # Record consent
    response = await client.post(
        "/api/v1/me/consent",
        json={"study_consent": True, "audio_consent": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["consent_at"] is not None
    assert data["audio_consent"] is True
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_unauthenticated_access(client: AsyncClient):
    response = await client.get("/api/v1/me")
    assert response.status_code == 401
