import uuid
from datetime import datetime

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    invite_code: str
    name: str
    phone_number: str = ""
    venture_name: str = ""
    venture_description: str = ""
    industry_vertical: str = ""


class ConsentRequest(BaseModel):
    study_consent: bool
    audio_consent: bool = False


class ParticipantResponse(BaseModel):
    id: uuid.UUID
    name: str
    phone_number: str | None
    arm: str
    venture_name: str | None
    venture_description: str | None
    industry_vertical: str | None
    language_preference: str | None
    status: str
    cohort_id: str | None
    consent_at: datetime | None
    audio_consent: bool

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    participant_id: uuid.UUID
    access_token: str
    token_type: str = "bearer"
    participant: ParticipantResponse
