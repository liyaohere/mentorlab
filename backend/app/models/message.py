import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class InputMethod(str, enum.Enum):
    text = "text"
    voice = "voice"


class SyncStatus(str, enum.Enum):
    synced = "synced"
    pending = "pending"
    failed = "failed"


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_client_id", "client_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    input_method: Mapped[InputMethod] = mapped_column(
        Enum(InputMethod), default=InputMethod.text
    )
    audio_file_url: Mapped[str | None] = mapped_column(Text)
    token_usage: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sync_status: Mapped[SyncStatus] = mapped_column(
        Enum(SyncStatus), default=SyncStatus.synced
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages", lazy="selectin"
    )
