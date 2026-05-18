import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ArmType(str, enum.Enum):
    """Experiment arms — maps 1:1 to ConditionType (c1→single, c2→integrated, c3→competing)."""
    c1 = "c1"
    c2 = "c2"
    c3 = "c3"


class ConditionType(str, enum.Enum):
    """V2 experiment conditions."""
    single = "single"          # C1: Orchestrator + Agent A only
    integrated = "integrated"  # C2: All 3 agents + integrator → 1 recommendation
    competing = "competing"    # C3: All 3 agents → 3 competing diagnoses shown


class ParticipantStatus(str, enum.Enum):
    enrolled = "enrolled"
    active = "active"
    completed = "completed"
    dropped = "dropped"


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)
    arm: Mapped[ArmType] = mapped_column(Enum(ArmType), nullable=False)
    cohort_id: Mapped[str | None] = mapped_column(String(50))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        Index("idx_participants_status", "status"),
        Index("idx_participants_arm", "arm"),
        Index("idx_participants_cohort", "cohort_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invite_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    arm: Mapped[ArmType] = mapped_column(Enum(ArmType), nullable=False)
    condition: Mapped[ConditionType | None] = mapped_column(Enum(ConditionType), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone_number: Mapped[str | None] = mapped_column(String(20))
    venture_name: Mapped[str | None] = mapped_column(String(300))
    venture_description: Mapped[str | None] = mapped_column(Text)
    industry_vertical: Mapped[str | None] = mapped_column(String(100))
    baseline_data: Mapped[dict | None] = mapped_column(JSON, default=dict)
    fcm_token: Mapped[str | None] = mapped_column(Text)
    cohort_id: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[ParticipantStatus] = mapped_column(Enum(ParticipantStatus), default=ParticipantStatus.enrolled)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    audio_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    audio_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    password_hash: Mapped[str | None] = mapped_column(String(128))
    otp_code: Mapped[str | None] = mapped_column(String(6))
    otp_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    memory_notes: Mapped[str | None] = mapped_column(Text)
    language_preference: Mapped[str | None] = mapped_column(String(20), default="english")
    app_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="participant", lazy="selectin")
