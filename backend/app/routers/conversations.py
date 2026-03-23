import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.conversation import Conversation, InitiatorType
from app.models.message import Message, MessageRole, SyncStatus
from app.models.participant import Participant
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.claude_service import claude_service

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _compute_week_number(participant: Participant) -> int:
    """Compute current week number based on enrollment date."""
    now = datetime.now(timezone.utc)
    created = participant.created_at
    # Handle both tz-aware and tz-naive datetimes (SQLite stores naive)
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days_since = (now - created).days
    return max(1, (days_since // 7) + 1)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.participant_id == participant.id)
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()

    response_items = []
    for conv in conversations:
        last_msg = None
        if conv.messages:
            last = conv.messages[-1]
            last_msg = MessageResponse.model_validate(last)
        response_items.append(
            ConversationResponse(
                id=conv.id,
                title=conv.title,
                week_number=conv.week_number,
                initiated_by=conv.initiated_by.value,
                created_at=conv.created_at,
                ended_at=conv.ended_at,
                last_message=last_msg,
            )
        )
    return ConversationListResponse(conversations=response_items)


@router.post("", response_model=ConversationDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    week_number = _compute_week_number(participant)

    # Summarize unsummarized past conversations and update participant memory
    result = await db.execute(
        select(Conversation)
        .where(Conversation.participant_id == participant.id, Conversation.summary.is_(None))
        .options(selectinload(Conversation.messages))
        .order_by(Conversation.created_at)
    )
    unsummarized = result.scalars().all()
    for conv in unsummarized:
        if len(conv.messages) >= 2:  # Only summarize conversations with actual exchanges
            try:
                summary, updated_memory = await claude_service.summarize_conversation(
                    participant, conv, conv.messages,
                )
                conv.summary = summary
                participant.memory_notes = updated_memory
            except Exception as e:
                logger.warning(f"Failed to summarize conversation {conv.id}: {e}")
    if unsummarized:
        await db.flush()

    conversation = Conversation(
        participant_id=participant.id,
        week_number=week_number,
        initiated_by=InitiatorType.participant,
    )
    db.add(conversation)
    await db.flush()

    # Generate AI greeting (now includes memory from past conversations)
    greeting_text, token_usage = await claude_service.get_greeting(participant, conversation)

    greeting_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=greeting_text,
        token_usage=token_usage,
        sync_status=SyncStatus.synced,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(greeting_msg)
    await db.commit()
    await db.refresh(conversation)
    await db.refresh(greeting_msg)

    return ConversationDetailResponse(
        conversation=ConversationResponse(
            id=conversation.id,
            week_number=conversation.week_number,
            initiated_by=conversation.initiated_by.value,
            created_at=conversation.created_at,
            ended_at=conversation.ended_at,
        ),
        messages=[MessageResponse.model_validate(greeting_msg)],
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    conversation = result.scalar_one_or_none()

    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.participant_id != participant.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    messages = [MessageResponse.model_validate(msg) for msg in conversation.messages]

    return ConversationDetailResponse(
        conversation=ConversationResponse(
            id=conversation.id,
            week_number=conversation.week_number,
            initiated_by=conversation.initiated_by.value,
            created_at=conversation.created_at,
            ended_at=conversation.ended_at,
        ),
        messages=messages,
    )
