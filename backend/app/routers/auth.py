from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.participant import InviteCode, Participant, ParticipantStatus
import hashlib
import secrets

from app.schemas.auth import AuthResponse, ConsentRequest, LoginRequest, ParticipantResponse, RegisterRequest, RequestCodeRequest, VerifyCodeRequest


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if "$" not in stored:
        return False
    salt, h = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return secrets.compare_digest(check.hex(), h)

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
    # Check if phone number already registered
    if request.phone_number:
        result = await db.execute(
            select(Participant).where(Participant.phone_number == request.phone_number)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this phone number already exists. Please log in instead.",
            )

    # Look up invite code — if empty or already used, auto-assign an available one
    invite = None
    if request.invite_code:
        result = await db.execute(
            select(InviteCode).where(InviteCode.code == request.invite_code.upper())
        )
        invite = result.scalar_one_or_none()

    if invite is None:
        # No matching code found — auto-assign an unused invite code
        result = await db.execute(
            select(InviteCode).where(InviteCode.used == False).limit(1)
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No invite codes available. Please contact the research team.",
            )
    elif invite.used and not (invite.code.startswith("DEMO") or invite.code.startswith("TEST")):
        # Non-reusable code already used — auto-assign
        result = await db.execute(
            select(InviteCode).where(InviteCode.used == False).limit(1)
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No invite codes available. Please contact the research team.",
            )

    # For DEMO/TEST codes: make them reusable by appending a unique suffix
    participant_code = invite.code
    if invite.code.startswith("DEMO") or invite.code.startswith("TEST"):
        import secrets
        participant_code = f"{invite.code}_{secrets.token_hex(3)}"
        # Don't mark demo codes as used — they stay reusable
    else:
        # Mark non-demo code as used
        invite.used = True

    # Create new participant
    participant = Participant(
        invite_code=participant_code,
        arm=invite.arm,
        name=request.name,
        phone_number=request.phone_number,
        password_hash=hash_password(request.password) if request.password else None,
        venture_name=request.venture_name,
        venture_description=request.venture_description,
        industry_vertical=request.industry_vertical,
        cohort_id=invite.cohort_id,
        status=ParticipantStatus.enrolled,
    )
    db.add(participant)

    if not invite.code.startswith("DEMO") and not invite.code.startswith("TEST"):
        invite.used_by = participant.id

    await db.commit()
    await db.refresh(participant)

    token = create_access_token(participant)
    return AuthResponse(
        participant_id=participant.id,
        access_token=token,
        participant=ParticipantResponse.model_validate(participant),
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Log in with phone number + password."""
    result = await db.execute(
        select(Participant).where(Participant.phone_number == request.phone_number)
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No account found with this phone number")
    if not participant.password_hash or not verify_password(request.password, participant.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password")
    token = create_access_token(participant)
    return AuthResponse(
        participant_id=participant.id,
        access_token=token,
        participant=ParticipantResponse.model_validate(participant),
    )


@router.post("/request-code")
async def request_code(request: RequestCodeRequest, db: AsyncSession = Depends(get_db)):
    """Send a verification code to the user's phone (for password reset or passwordless login)."""
    import random
    result = await db.execute(
        select(Participant).where(Participant.phone_number == request.phone_number)
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found with this phone number")
    code = f"{random.randint(0, 999999):06d}"
    participant.otp_code = code
    participant.otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.commit()
    # TODO: Send code via SMS (Twilio/Africa's Talking) in production
    # For development, return the code in the response
    return {"message": f"Verification code sent to {request.phone_number}", "dev_code": code}


@router.post("/verify-code", response_model=AuthResponse)
async def verify_code(request: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    """Verify OTP code and log in (optionally set new password)."""
    result = await db.execute(
        select(Participant).where(Participant.phone_number == request.phone_number)
    )
    participant = result.scalar_one_or_none()
    if participant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found")
    if not participant.otp_code or participant.otp_code != request.code:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid code")
    if participant.otp_expires and participant.otp_expires < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Code expired")
    # Clear OTP
    participant.otp_code = None
    participant.otp_expires = None
    # Update password if provided
    if request.new_password:
        participant.password_hash = hash_password(request.new_password)
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
