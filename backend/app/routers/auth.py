from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.participant import InviteCode, Participant, ParticipantStatus
from app.schemas.auth import AuthResponse, ConsentRequest, ParticipantResponse, RegisterRequest

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def create_access_token(participant: Participant) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRY_DAYS)
    payload = {
        "sub": str(participant.id),
        "arm": participant.arm.value,
        "cohort": participant.cohort_id or "",
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Look up invite code
    result = await db.execute(
        select(InviteCode).where(InviteCode.code == request.invite_code.upper())
    )
    invite = result.scalar_one_or_none()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")

    # If code already used, return existing participant with new token (phone loss recovery)
    if invite.used:
        result = await db.execute(
            select(Participant).where(Participant.invite_code == invite.code)
        )
        existing = result.scalar_one_or_none()
        if existing:
            token = create_access_token(existing)
            return AuthResponse(
                participant_id=existing.id,
                access_token=token,
                participant=ParticipantResponse.model_validate(existing),
            )

    # Create new participant
    participant = Participant(
        invite_code=invite.code,
        arm=invite.arm,
        name=request.name,
        phone_number=request.phone_number,
        venture_name=request.venture_name,
        venture_description=request.venture_description,
        industry_vertical=request.industry_vertical,
        cohort_id=invite.cohort_id,
        status=ParticipantStatus.enrolled,
    )
    db.add(participant)

    # Mark code as used
    invite.used = True
    invite.used_by = participant.id

    await db.commit()
    await db.refresh(participant)

    token = create_access_token(participant)
    return AuthResponse(
        participant_id=participant.id,
        access_token=token,
        participant=ParticipantResponse.model_validate(participant),
    )


@router.post("/refresh")
async def refresh_token(participant: Participant = Depends(get_current_participant)):
    token = create_access_token(participant)
    return {"access_token": token, "token_type": "bearer"}


# Profile endpoints (under /api/v1/me)
me_router = APIRouter(prefix="/api/v1/me", tags=["profile"])


@me_router.get("", response_model=ParticipantResponse)
async def get_profile(participant: Participant = Depends(get_current_participant)):
    return ParticipantResponse.model_validate(participant)


@me_router.patch("", response_model=ParticipantResponse)
async def update_profile(
    updates: dict,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    allowed_fields = {"name", "phone_number", "venture_name", "venture_description", "industry_vertical", "language_preference", "fcm_token", "app_version"}
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(participant, field, value)
    await db.commit()
    await db.refresh(participant)
    return ParticipantResponse.model_validate(participant)


@me_router.post("/consent", response_model=ParticipantResponse)
async def record_consent(
    request: ConsentRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if request.study_consent:
        participant.consent_at = now
        participant.status = ParticipantStatus.active
    if request.audio_consent:
        participant.audio_consent = True
        participant.audio_consent_at = now
    await db.commit()
    await db.refresh(participant)
    return ParticipantResponse.model_validate(participant)
