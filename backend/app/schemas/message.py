import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.conversation import MessageResponse


class SendMessageRequest(BaseModel):
    content: str
    input_method: str = "text"
    client_id: uuid.UUID
    audio_url: str | None = None


class SendMessageResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse


class SyncMessageItem(BaseModel):
    conversation_id: uuid.UUID
    content: str
    input_method: str = "text"
    client_id: uuid.UUID
    created_at: datetime | None = None


class SyncMessagesRequest(BaseModel):
    messages: list[SyncMessageItem]


class SyncResultItem(BaseModel):
    client_id: uuid.UUID
    user_message: MessageResponse | None = None
    assistant_message: MessageResponse | None = None
    status: str  # "synced" or "error"
    error: str | None = None


class SyncMessagesResponse(BaseModel):
    results: list[SyncResultItem]
