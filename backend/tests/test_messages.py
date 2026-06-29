import uuid

import pytest
from httpx import AsyncClient


async def _setup_conversation(
    client: AsyncClient, code: str = "TEST001A"
) -> tuple[str, str]:
    """Register, create conversation, return (token, conversation_id)."""
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "invite_code": code,
            "name": "Test User",
            "venture_name": "Test Venture",
            "venture_description": "A test venture",
            "industry_vertical": "Agriculture",
        },
    )
    token = r.json()["access_token"]

    r2 = await client.post(
        "/api/v1/conversations", headers={"Authorization": f"Bearer {token}"}
    )
    conv_id = r2.json()["conversation"]["id"]
    return token, conv_id


@pytest.mark.asyncio
async def test_send_message(client: AsyncClient, seed_invite_codes, mock_claude):
    token, conv_id = await _setup_conversation(client)

    client_id = str(uuid.uuid4())
    response = await client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={
            "content": "I've been working on expanding my farm.",
            "input_method": "text",
            "client_id": client_id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_message"]["content"] == "I've been working on expanding my farm."
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    assert data["assistant_message"]["content"] == "This is a test AI response."


@pytest.mark.asyncio
async def test_message_idempotency(client: AsyncClient, seed_invite_codes, mock_claude):
    token, conv_id = await _setup_conversation(client)

    client_id = str(uuid.uuid4())
    payload = {
        "content": "Hello mentor!",
        "input_method": "text",
        "client_id": client_id,
    }
    headers = {"Authorization": f"Bearer {token}"}

    # Send twice with same client_id
    r1 = await client.post(
        f"/api/v1/conversations/{conv_id}/messages", json=payload, headers=headers
    )
    r2 = await client.post(
        f"/api/v1/conversations/{conv_id}/messages", json=payload, headers=headers
    )

    assert r1.status_code == 201
    assert r2.status_code == 201
    # Should return the same messages
    assert r1.json()["user_message"]["id"] == r2.json()["user_message"]["id"]


@pytest.mark.asyncio
async def test_sync_messages(client: AsyncClient, seed_invite_codes, mock_claude):
    token, conv_id = await _setup_conversation(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Sync a batch of offline messages
    messages = [
        {
            "conversation_id": conv_id,
            "content": f"Offline message {i}",
            "input_method": "text",
            "client_id": str(uuid.uuid4()),
        }
        for i in range(3)
    ]

    response = await client.post(
        "/api/v1/sync/messages",
        json={"messages": messages},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3
    for result in data["results"]:
        assert result["status"] == "synced"
        assert result["user_message"] is not None
        assert result["assistant_message"] is not None


@pytest.mark.asyncio
async def test_sync_idempotent(client: AsyncClient, seed_invite_codes, mock_claude):
    token, conv_id = await _setup_conversation(client)
    headers = {"Authorization": f"Bearer {token}"}

    client_id = str(uuid.uuid4())
    messages = [
        {
            "conversation_id": conv_id,
            "content": "Same message",
            "input_method": "text",
            "client_id": client_id,
        }
    ]

    # Sync twice
    r1 = await client.post(
        "/api/v1/sync/messages", json={"messages": messages}, headers=headers
    )
    r2 = await client.post(
        "/api/v1/sync/messages", json={"messages": messages}, headers=headers
    )

    assert (
        r1.json()["results"][0]["user_message"]["id"]
        == r2.json()["results"][0]["user_message"]["id"]
    )
