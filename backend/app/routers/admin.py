import csv
import io
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.middleware.admin_auth import require_admin
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.notification import Notification
from app.models.participant import ArmType, InviteCode, Participant, ParticipantStatus
from app.models.survey import Survey
from app.utils.invite_codes import generate_invite_code

# All admin endpoints require the X-Admin-Key header
router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


# --- Participant Management ---


class ParticipantSummary(BaseModel):
    id: uuid.UUID
    name: str
    arm: str
    status: str
    venture_name: str | None
    industry_vertical: str | None
    cohort_id: str | None
    invite_code: str
    created_at: datetime
    consent_at: datetime | None
    message_count: int = 0
    conversation_count: int = 0

    model_config = {"from_attributes": True}


@router.get("/participants")
async def list_participants(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Participant).order_by(Participant.created_at.desc())
    if cohort_id:
        query = query.where(Participant.cohort_id == cohort_id)
    result = await db.execute(query)
    participants = result.scalars().all()

    summaries = []
    for p in participants:
        # Count conversations and messages
        conv_count = await db.execute(
            select(func.count()).where(Conversation.participant_id == p.id)
        )
        msg_count = await db.execute(
            select(func.count()).where(
                Message.conversation_id.in_(
                    select(Conversation.id).where(Conversation.participant_id == p.id)
                )
            )
        )
        summaries.append(
            {
                "id": p.id,
                "name": p.name,
                "arm": p.arm.value,
                "status": p.status.value,
                "venture_name": p.venture_name,
                "industry_vertical": p.industry_vertical,
                "cohort_id": p.cohort_id,
                "invite_code": p.invite_code,
                "created_at": p.created_at,
                "consent_at": p.consent_at,
                "conversation_count": conv_count.scalar() or 0,
                "message_count": msg_count.scalar() or 0,
            }
        )
    return {"participants": summaries}


@router.post("/participants/upload")
async def upload_participants(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload CSV with columns: name, phone, arm, cohort, industry_vertical.
    Generates invite codes and creates invite_code records.
    """
    content = await file.read()
    text = content.decode("utf-8-sig")  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))

    created_codes = []
    errors = []

    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        name = row.get("name", "").strip()
        arm_str = row.get("arm", "").strip().lower()
        cohort = row.get("cohort", "").strip()
        phone = row.get("phone", "").strip()
        industry = row.get("industry_vertical", "").strip()

        if not name:
            errors.append(f"Row {i}: missing name")
            continue

        try:
            arm = ArmType(arm_str)
        except ValueError:
            errors.append(f"Row {i}: invalid arm '{arm_str}' (use c1/c2/c3)")
            continue

        code = generate_invite_code()
        invite = InviteCode(code=code, arm=arm, cohort_id=cohort or None)
        db.add(invite)
        created_codes.append(
            {
                "name": name,
                "phone": phone,
                "arm": arm_str,
                "cohort": cohort,
                "industry_vertical": industry,
                "invite_code": code,
            }
        )

    await db.commit()

    return {
        "created": len(created_codes),
        "errors": errors,
        "codes": created_codes,
    }


# --- Data Export ---


async def _log_export(
    db: AsyncSession, export_type: str, cohort_id: str | None, row_count: int
):
    """Log every export to admin_events for download history."""
    from app.models.admin import AdminEvent

    event = AdminEvent(
        action=f"export_{export_type}",
        metadata_={
            "type": export_type,
            "cohort_id": cohort_id,
            "row_count": row_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.add(event)
    await db.commit()


@router.get("/export/transcripts")
async def export_transcripts(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export all chat transcripts as CSV.

    Each message includes conversation_number (sequential per participant,
    so you can tell which messages belong to the same chat session) and
    message_order (sequential within a conversation, starting from 1).
    """
    query = (
        select(Message, Conversation, Participant)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Participant, Conversation.participant_id == Participant.id)
        .order_by(Participant.id, Conversation.created_at, Message.created_at)
    )
    if cohort_id:
        query = query.where(Participant.cohort_id == cohort_id)

    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "participant_id",
            "participant_name",
            "arm",
            "cohort",
            "conversation_id",
            "conversation_number",
            "week_number",
            "initiated_by",
            "message_order",
            "message_role",
            "message_content",
            "input_method",
            "timestamp",
        ]
    )

    # Track conversation numbering per participant
    participant_conv_counter: dict[str, int] = {}  # participant_id -> next conv number
    current_conv_id: str | None = None
    current_conv_number: int = 0
    message_order: int = 0

    for msg, conv, participant in rows:
        pid = str(participant.id)
        cid = str(conv.id)

        # New conversation?
        if cid != current_conv_id:
            current_conv_id = cid
            message_order = 0
            if pid not in participant_conv_counter:
                participant_conv_counter[pid] = 1
            else:
                participant_conv_counter[pid] += 1
            current_conv_number = participant_conv_counter[pid]

        message_order += 1

        writer.writerow(
            [
                pid,
                participant.name,
                participant.arm.value,
                participant.cohort_id or "",
                cid,
                current_conv_number,
                conv.week_number or "",
                conv.initiated_by.value,
                message_order,
                msg.role.value,
                msg.content,
                msg.input_method.value,
                msg.created_at.isoformat() if msg.created_at else "",
            ]
        )

    # Log this download
    await _log_export(db, "transcripts", cohort_id, len(rows))

    # Timestamped filename
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"mentorlab_transcripts_{ts}.csv"

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/surveys")
async def export_surveys(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export all survey responses as CSV."""
    import json

    query = (
        select(Survey, Participant)
        .join(Participant, Survey.participant_id == Participant.id)
        .order_by(Participant.id, Survey.completed_at)
    )
    if cohort_id:
        query = query.where(Participant.cohort_id == cohort_id)

    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "participant_id",
            "participant_name",
            "arm",
            "cohort",
            "survey_type",
            "week_number",
            "completed_at",
            "responses_json",
        ]
    )

    for survey, participant in rows:
        writer.writerow(
            [
                str(participant.id),
                participant.name,
                participant.arm.value,
                participant.cohort_id or "",
                survey.type.value,
                survey.week_number or "",
                survey.completed_at.isoformat() if survey.completed_at else "",
                json.dumps(survey.responses),
            ]
        )

    # Log this download
    await _log_export(db, "surveys", cohort_id, len(rows))

    # Timestamped filename
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"mentorlab_surveys_{ts}.csv"

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/history")
async def get_export_history(db: AsyncSession = Depends(get_db)):
    """Get the history of all data exports (who downloaded what, when)."""
    from app.models.admin import AdminEvent

    result = await db.execute(
        select(AdminEvent)
        .where(AdminEvent.action.like("export_%"))
        .order_by(AdminEvent.created_at.desc())
        .limit(50)
    )
    events = result.scalars().all()
    return {
        "exports": [
            {
                "id": str(e.id),
                "type": e.metadata_.get("type", "") if e.metadata_ else "",
                "cohort_id": e.metadata_.get("cohort_id") if e.metadata_ else None,
                "row_count": e.metadata_.get("row_count", 0) if e.metadata_ else 0,
                "downloaded_at": e.metadata_.get("timestamp", "")
                if e.metadata_
                else "",
            }
            for e in events
        ]
    }


# --- Engagement Dashboard ---


@router.get("/dashboard")
async def get_dashboard(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Engagement statistics for the admin dashboard."""
    # Base filter
    p_query = select(Participant)
    if cohort_id:
        p_query = p_query.where(Participant.cohort_id == cohort_id)
    result = await db.execute(p_query)
    participants = list(result.scalars().all())

    total = len(participants)
    by_arm = {}
    by_status = {}
    for p in participants:
        arm = p.arm.value
        st = p.status.value
        by_arm[arm] = by_arm.get(arm, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1

    # Message counts by arm
    msg_query = (
        select(Participant.arm, func.count(Message.id))
        .join(Conversation, Conversation.participant_id == Participant.id)
        .join(Message, Message.conversation_id == Conversation.id)
        .where(Message.role == "user")
        .group_by(Participant.arm)
    )
    if cohort_id:
        msg_query = msg_query.where(Participant.cohort_id == cohort_id)
    result = await db.execute(msg_query)
    messages_by_arm = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1]
        for row in result.all()
    }

    # Voice vs text
    voice_query = (
        select(Message.input_method, func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(Participant, Conversation.participant_id == Participant.id)
        .where(Message.role == "user")
        .group_by(Message.input_method)
    )
    if cohort_id:
        voice_query = voice_query.where(Participant.cohort_id == cohort_id)
    result = await db.execute(voice_query)
    input_methods = {
        row[0].value if hasattr(row[0], "value") else row[0]: row[1]
        for row in result.all()
    }

    # Total AI messages (for cost estimate)
    total_msg_result = await db.execute(
        select(func.count(Message.id)).where(Message.role == "assistant")
    )
    total_ai_messages = total_msg_result.scalar() or 0

    # Total user messages
    total_user_result = await db.execute(
        select(func.count(Message.id)).where(Message.role == "user")
    )
    total_user_messages = total_user_result.scalar() or 0

    # Total conversations
    conv_count_result = await db.execute(select(func.count(Conversation.id)))
    total_conversations = conv_count_result.scalar() or 0

    # Avg messages per conversation
    avg_msgs = round(total_user_messages / max(total_conversations, 1), 1)

    # Messages today
    from datetime import datetime, timedelta, timezone as tz

    today_start = datetime.now(tz.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    msgs_today_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.role == "user", Message.created_at >= today_start
        )
    )
    messages_today = msgs_today_result.scalar() or 0

    # Messages this week
    week_start = today_start - timedelta(days=today_start.weekday())
    msgs_week_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.role == "user", Message.created_at >= week_start
        )
    )
    messages_this_week = msgs_week_result.scalar() or 0

    # Recent conversations (last 10)
    recent_result = await db.execute(
        select(
            Conversation.id,
            Conversation.title,
            Conversation.created_at,
            Conversation.week_number,
            Participant.name,
            Participant.arm,
        )
        .join(Participant, Conversation.participant_id == Participant.id)
        .order_by(Conversation.created_at.desc())
        .limit(10)
    )
    recent_conversations = [
        {
            "id": str(r[0]),
            "title": r[1] or "New conversation",
            "created_at": r[2].isoformat(),
            "week": r[3],
            "participant": r[4],
            "arm": r[5].value,
        }
        for r in recent_result.all()
    ]

    # Conversations per arm
    conv_by_arm_result = await db.execute(
        select(Participant.arm, func.count(Conversation.id))
        .join(Conversation, Conversation.participant_id == Participant.id)
        .group_by(Participant.arm)
    )
    conversations_by_arm = {r[0].value: r[1] for r in conv_by_arm_result.all()}

    # Participants with memory (cross-conversation memory active)
    memory_result = await db.execute(
        select(func.count(Participant.id)).where(Participant.memory_notes.isnot(None))
    )
    participants_with_memory = memory_result.scalar() or 0

    return {
        "total_participants": total,
        "by_arm": by_arm,
        "by_status": by_status,
        "user_messages_by_arm": messages_by_arm,
        "input_methods": input_methods,
        "total_ai_messages": total_ai_messages,
        "total_user_messages": total_user_messages,
        "total_conversations": total_conversations,
        "avg_messages_per_conversation": avg_msgs,
        "messages_today": messages_today,
        "messages_this_week": messages_this_week,
        "conversations_by_arm": conversations_by_arm,
        "participants_with_memory": participants_with_memory,
        "recent_conversations": recent_conversations,
        "estimated_ai_cost_usd": round(total_ai_messages * 0.01, 2),
    }


# --- Prompt Management ---


class PromptUpdate(BaseModel):
    arm: str  # c1, c2, c3
    content: str


@router.get("/prompts/{arm}")
async def get_prompt(arm: str):
    """Get the current system prompt for an arm."""
    from pathlib import Path

    arm_files = {
        "c1": "c1_single.md",
        "c2": "c2_integrated.md",
        "c3": "c3_competing.md",
    }
    filename = arm_files.get(arm)
    if not filename:
        raise HTTPException(status_code=404, detail=f"Unknown arm: {arm}")

    prompt_path = Path(__file__).parent.parent / "prompts" / filename
    return {"arm": arm, "content": prompt_path.read_text()}


@router.put("/prompts")
async def update_prompt(update: PromptUpdate):
    """Update the system prompt for an arm. Logs the change."""
    from pathlib import Path

    arm_files = {
        "c1": "c1_single.md",
        "c2": "c2_integrated.md",
        "c3": "c3_competing.md",
    }
    filename = arm_files.get(update.arm)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unknown arm: {update.arm}")

    prompt_path = Path(__file__).parent.parent / "prompts" / filename

    # Read old content for diff
    old_content = prompt_path.read_text()
    prompt_path.write_text(update.content)

    # Clear prompt cache so changes take effect
    from app.services.claude_service import claude_service

    claude_service._prompt_cache.clear()

    return {
        "arm": update.arm,
        "status": "updated",
        "old_length": len(old_content),
        "new_length": len(update.content),
    }
