import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SurveyType(str, enum.Enum):
    baseline = "baseline"
    weekly_pulse = "weekly_pulse"
    midpoint = "midpoint"
    endline = "endline"


class Survey(Base):
    __tablename__ = "surveys"
    __table_args__ = (
        Index("idx_surveys_participant", "participant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    week_number: Mapped[int | None] = mapped_column(Integer)
    type: Mapped[SurveyType] = mapped_column(Enum(SurveyType), nullable=False)
    responses: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
