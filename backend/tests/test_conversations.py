import pytest
from httpx import AsyncClient


async def _register_and_get_token(client: AsyncClient, code: str = "TEST001A") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "invite_code": code,
        "name": "Test User",
        "venture_name": "Test Venture",
        "venture_description": "A test venture",
        "industry_vertical": "Agriculture",
    })
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_create_conversation(client: AsyncClient, seed_invite_codes, mock_claude):
    token = await _register_and_get_token(client)

    response = await client.post(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["conversation"]["initiated_by"] == "participant"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["role"] == "assistant"


@pytest.mark.asyncio
async def test_list_conversations(client: AsyncClient, seed_invite_codes, mock_claude):
    token = await _register_and_get_token(client)

    # Create two conversations
    await client.post("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    await client.post("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})

    response = await client.get(
        "/api/v1/conversations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["conversations"]) == 2


@pytest.mark.asyncio
async def test_get_conversation_with_messages(client: AsyncClient, seed_invite_codes, mock_claude):
    token = await _register_and_get_token(client)

    # Create conversation
    r = await client.post("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    conv_id = r.json()["conversation"]["id"]

    # Get conversation
    response = await client.get(
        f"/api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["messages"]) == 1


@pytest.mark.asyncio
async def test_cannot_access_other_participant_conversation(client: AsyncClient, seed_invite_codes, mock_claude):
    token1 = await _register_and_get_token(client, "TEST001A")
    token2 = await _register_and_get_token(client, "TEST002B")

    # Create conversation as participant 1
    r = await client.post("/api/v1/conversations", headers={"Authorization": f"Bearer {token1}"})
    conv_id = r.json()["conversation"]["id"]

    # Try to access as participant 2
    response = await client.get(
        f"/api/v1/conversations/{conv_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert response.status_code == 403
