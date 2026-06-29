import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.conversation import Conversation
from app.models.message import InputMethod, Message, MessageRole, SyncStatus
from app.models.participant import Participant
from app.schemas.conversation import MessageResponse
from app.schemas.message import (
    SendMessageRequest,
    SendMessageResponse,
    SyncMessageItem,
    SyncMessagesRequest,
    SyncMessagesResponse,
    SyncResultItem,
)
from app.services.claude_service import claude_service

router = APIRouter(prefix="/api/v1/conversations", tags=["messages"])


async def _process_message(
    conversation: Conversation,
    participant: Participant,
    content: str,
    input_method: str,
    client_id: uuid.UUID,
    db: AsyncSession,
    created_at: datetime | None = None,
    audio_file_url: str | None = None,
) -> tuple[Message, Message]:
    """Save user message, get Claude response, save assistant message. Returns (user_msg, assistant_msg)."""
    # Idempotency check
    existing = await db.execute(select(Message).where(Message.client_id == client_id))
    existing_msg = existing.scalar_one_or_none()
    if existing_msg:
        # Find the AI response that follows
        ai_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .where(Message.role == MessageRole.assistant)
            .where(Message.created_at > existing_msg.created_at)
            .order_by(Message.created_at)
            .limit(1)
        )
        ai_msg = ai_result.scalar_one_or_none()
        if ai_msg:
            return existing_msg, ai_msg

    # Save user message
    now = datetime.now(timezone.utc)
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=content,
        input_method=InputMethod(input_method),
        client_id=client_id,
        audio_file_url=audio_file_url,
        sync_status=SyncStatus.synced,
        created_at=created_at or now,
        sent_at=now,
    )
    db.add(user_msg)
    await db.flush()

    # Load conversation history for Claude
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    all_messages = list(result.scalars().all())

    # Get Claude response
    response_text, token_usage = await claude_service.get_response(
        participant, conversation, all_messages
    )

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=response_text,
        token_usage=token_usage,
        sync_status=SyncStatus.synced,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(assistant_msg)
    await db.flush()

    # Generate conversation title after first user message
    user_messages = [m for m in all_messages if m.role == MessageRole.user]
    if len(user_messages) == 1 and not conversation.title:
        try:
            title_text, _ = await claude_service._call_ai(
                "Generate a short title (3-6 words, no quotes) for a mentoring conversation that starts with this message. Just output the title, nothing else.",
                [{"role": "user", "content": content}],
            )
            conversation.title = title_text.strip().strip('"').strip("'")[:200]
            await db.flush()
        except Exception:
            pass  # Title generation is non-critical

    return user_msg, assistant_msg


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: uuid.UUID,
    request: SendMessageRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    # Verify conversation ownership
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    if conversation.participant_id != participant.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    user_msg, assistant_msg = await _process_message(
        conversation=conversation,
        participant=participant,
        content=request.content,
        input_method=request.input_method,
        client_id=request.client_id,
        db=db,
        audio_file_url=request.audio_url,
    )

    await db.commit()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    return SendMessageResponse(
        user_message=MessageResponse.model_validate(user_msg),
        assistant_message=MessageResponse.model_validate(assistant_msg),
    )


@router.post("/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: uuid.UUID,
    request: SendMessageRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Stream AI response via Server-Sent Events."""
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.participant_id != participant.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Idempotency check
    existing = await db.execute(
        select(Message).where(Message.client_id == request.client_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Message already sent")

    # Save user message
    now = datetime.now(timezone.utc)
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=request.content,
        input_method=InputMethod(request.input_method),
        client_id=request.client_id,
        audio_file_url=request.audio_url,
        sync_status=SyncStatus.synced,
        created_at=now,
        sent_at=now,
    )
    db.add(user_msg)
    await db.flush()

    # Load history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    all_messages = list(result.scalars().all())

    async def generate():
        full_text = ""
        token_usage = {}
        try:
            async for chunk, usage in claude_service.stream_response(
                participant, conversation, all_messages
            ):
                if usage is not None:
                    full_text = chunk
                    token_usage = usage
                else:
                    yield f"data: {json.dumps({'t': chunk})}\n\n"
        except Exception as e:
            import logging

            logging.getLogger(__name__).error(f"Stream generate error: {e}")
            if not full_text:
                full_text = "Sorry, I encountered an error. Please try again."
                yield f"data: {json.dumps({'t': full_text})}\n\n"

        # Save assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.assistant,
            content=full_text,
            token_usage=token_usage,
            sync_status=SyncStatus.synced,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(assistant_msg)

        # Generate title after first user message
        user_msgs = [m for m in all_messages if m.role == MessageRole.user]
        title = conversation.title
        if len(user_msgs) == 1 and not title:
            try:
                title_text, _ = await claude_service._call_ai(
                    "Generate a short title (3-6 words, no quotes) for a mentoring conversation. Just output the title.",
                    [{"role": "user", "content": request.content}],
                )
                conversation.title = title_text.strip().strip('"').strip("'")[:200]
                title = conversation.title
            except Exception:
                pass

        await db.commit()
        await db.refresh(assistant_msg)
        yield f"data: {json.dumps({'done': True, 'id': str(assistant_msg.id), 'title': title})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# Sync endpoint (separate router to avoid path conflicts)
sync_router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@sync_router.post("/messages", response_model=SyncMessagesResponse)
async def sync_messages(
    request: SyncMessagesRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    results: list[SyncResultItem] = []

    for item in request.messages:
        # Verify conversation ownership
        conv_result = await db.execute(
            select(Conversation).where(Conversation.id == item.conversation_id)
        )
        conversation = conv_result.scalar_one_or_none()
        if conversation is None or conversation.participant_id != participant.id:
            results.append(
                SyncResultItem(
                    client_id=item.client_id,
                    status="error",
                    error="Conversation not found or access denied",
                )
            )
            continue

        try:
            user_msg, assistant_msg = await _process_message(
                conversation=conversation,
                participant=participant,
                content=item.content,
                input_method=item.input_method,
                client_id=item.client_id,
                db=db,
                created_at=item.created_at,
            )
            await db.flush()

            results.append(
                SyncResultItem(
                    client_id=item.client_id,
                    user_message=MessageResponse.model_validate(user_msg),
                    assistant_message=MessageResponse.model_validate(assistant_msg),
                    status="synced",
                )
            )
        except Exception as e:
            results.append(
                SyncResultItem(
                    client_id=item.client_id,
                    status="error",
                    error=str(e),
                )
            )

    await db.commit()
    return SyncMessagesResponse(results=results)
