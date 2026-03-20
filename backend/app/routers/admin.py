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
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.notification import Notification
from app.models.participant import ArmType, InviteCode, Participant, ParticipantStatus
from app.models.survey import Survey
from app.utils.invite_codes import generate_invite_code

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# NOTE: In production, these endpoints should be protected by admin auth.
# For Phase 4 / pilot, we leave them open to simplify testing.
# Phase 5 should add proper admin JWT auth.


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
        summaries.append({
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
        })
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
            errors.append(f"Row {i}: invalid arm '{arm_str}' (use control/analytic/constructive)")
            continue

        code = generate_invite_code()
        invite = InviteCode(code=code, arm=arm, cohort_id=cohort or None)
        db.add(invite)
        created_codes.append({
            "name": name,
            "phone": phone,
            "arm": arm_str,
            "cohort": cohort,
            "industry_vertical": industry,
            "invite_code": code,
        })

    await db.commit()

    return {
        "created": len(created_codes),
        "errors": errors,
        "codes": created_codes,
    }


# --- Data Export ---

@router.get("/export/transcripts")
async def export_transcripts(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export all chat transcripts as CSV."""
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
    writer.writerow([
        "participant_id", "participant_name", "arm", "cohort",
        "conversation_id", "week_number", "initiated_by",
        "message_role", "message_content", "input_method", "timestamp",
    ])

    for msg, conv, participant in rows:
        writer.writerow([
            str(participant.id), participant.name, participant.arm.value,
            participant.cohort_id or "",
            str(conv.id), conv.week_number or "", conv.initiated_by.value,
            msg.role.value, msg.content, msg.input_method.value,
            msg.created_at.isoformat() if msg.created_at else "",
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transcripts.csv"},
    )


@router.get("/export/surveys")
async def export_surveys(
    cohort_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Export all survey responses as CSV."""
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
    writer.writerow([
        "participant_id", "participant_name", "arm", "cohort",
        "survey_type", "week_number", "completed_at", "responses_json",
    ])

    for survey, participant in rows:
        import json
        writer.writerow([
            str(participant.id), participant.name, participant.arm.value,
            participant.cohort_id or "",
            survey.type.value, survey.week_number or "",
            survey.completed_at.isoformat() if survey.completed_at else "",
            json.dumps(survey.responses),
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=surveys.csv"},
    )


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
    messages_by_arm = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in result.all()}

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
    input_methods = {row[0].value if hasattr(row[0], 'value') else row[0]: row[1] for row in result.all()}

    # Token usage (cost tracking)
    token_query = (
        select(func.sum(func.cast(Message.token_usage["input_tokens"].as_string(), func.text())))
    )
    # Simplified: just count total messages with token_usage
    total_msg_result = await db.execute(
        select(func.count(Message.id)).where(Message.role == "assistant")
    )
    total_ai_messages = total_msg_result.scalar() or 0

    return {
        "total_participants": total,
        "by_arm": by_arm,
        "by_status": by_status,
        "user_messages_by_arm": messages_by_arm,
        "input_methods": input_methods,
        "total_ai_messages": total_ai_messages,
        "estimated_ai_cost_usd": round(total_ai_messages * 0.01, 2),
    }


# --- Prompt Management ---

class PromptUpdate(BaseModel):
    arm: str  # control, analytic, constructive
    content: str


@router.get("/prompts/{arm}")
async def get_prompt(arm: str):
    """Get the current system prompt for an arm."""
    from pathlib import Path
    arm_files = {
        "control": "arm1_control.md",
        "analytic": "arm2_analytic.md",
        "constructive": "arm3_constructive.md",
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
        "control": "arm1_control.md",
        "analytic": "arm2_analytic.md",
        "constructive": "arm3_constructive.md",
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
