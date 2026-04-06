import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InitiatorType(str, enum.Enum):
    system = "system"
    participant = "participant"


class ConversationStatus(str, enum.Enum):
    """Tracks the phase of a v2 interview conversation."""
    intake = "intake"          # Factual questions being asked
    baseline = "baseline"      # Brief diagnostic questions at end of intake
    analyzing = "analyzing"    # AI diagnosis generation in progress
    diagnosis = "diagnosis"    # Diagnosis shown, awaiting entrepreneur response
    response = "response"      # Neutral prompt answered, awaiting survey
    survey = "survey"          # Process measures being collected
    complete = "complete"      # All phases done
    active = "active"          # Legacy: ongoing v1 conversation


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_participant", "participant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    week_number: Mapped[int | None] = mapped_column(Integer)
    initiated_by: Mapped[InitiatorType] = mapped_column(Enum(InitiatorType), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    summary: Mapped[str | None] = mapped_column(Text)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- V2 fields: interview phases ---
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus), default=ConversationStatus.active
    )

    # Intake phase
    intake_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    intake_responses: Mapped[dict | None] = mapped_column(JSON)
    intake_question_index: Mapped[int] = mapped_column(Integer, default=0)

    # Baseline (embedded at end of intake)
    baseline_responses: Mapped[dict | None] = mapped_column(JSON)

    # Diagnosis phase
    orchestrator_output: Mapped[dict | None] = mapped_column(JSON)    # 3 causal directions
    diagnosis_raw: Mapped[list | None] = mapped_column(JSON)          # All agent outputs (always stored)
    diagnosis_integrated: Mapped[str | None] = mapped_column(Text)    # C2 only: integrator output
    diagnosis_shown: Mapped[str | None] = mapped_column(Text)         # What entrepreneur actually saw
    divergence_check: Mapped[str | None] = mapped_column(String(10))  # PASS or FAIL

    # C3 selection (data collection, not treatment)
    selection_choice: Mapped[int | None] = mapped_column(Integer)     # 0, 1, or 2

    # Neutral response prompt (PRIMARY DV)
    response_text: Mapped[str | None] = mapped_column(Text)
    response_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Process measures (Likert 1-7)
    cognitive_load_score: Mapped[float | None] = mapped_column(Float)
    perceived_confusion_score: Mapped[float | None] = mapped_column(Float)
    trust_in_advice_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    ownership_score: Mapped[float | None] = mapped_column(Float)

    # Time tracking (seconds)
    reading_time_seconds: Mapped[int | None] = mapped_column(Integer)
    writing_time_seconds: Mapped[int | None] = mapped_column(Integer)

    # Audio recording
    session_audio_url: Mapped[str | None] = mapped_column(Text)

    participant: Mapped["Participant"] = relationship(back_populates="conversations", lazy="selectin")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation", lazy="selectin", order_by="Message.created_at")
