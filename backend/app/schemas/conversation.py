import uuid
from datetime import datetime

from pydantic import BaseModel


class MessageResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID | None
    conversation_id: uuid.UUID
    role: str
    content: str
    input_method: str
    created_at: datetime
    sync_status: str

    model_config = {"from_attributes": True}


class ConversationResponse(BaseModel):
    id: uuid.UUID
    week_number: int | None
    initiated_by: str
    created_at: datetime
    ended_at: datetime | None
    last_message: MessageResponse | None = None

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
