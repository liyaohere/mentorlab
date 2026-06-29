import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_participant
from app.models.notification import Notification, NotificationStatus
from app.models.participant import Participant
from app.services.notification_service import notification_service
from app.services.scheduler_service import (
    initiate_conversations_for_cohort,
    update_cohort_schedule,
    get_schedule,
    DEFAULT_SCHEDULE,
)

router = APIRouter(prefix="/api/v1", tags=["notifications"])


# --- Participant-facing endpoints ---


@router.post("/notifications/{notification_id}/delivered")
async def mark_delivered(
    notification_id: uuid.UUID,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif or notif.participant_id != participant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    notif.delivered_at = datetime.now(timezone.utc)
    notif.status = NotificationStatus.delivered
    await db.commit()
    return {"status": "ok"}


@router.post("/notifications/{notification_id}/opened")
async def mark_opened(
    notification_id: uuid.UUID,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notif = result.scalar_one_or_none()
    if not notif or notif.participant_id != participant.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    notif.opened_at = datetime.now(timezone.utc)
    notif.status = NotificationStatus.opened
    await db.commit()
    return {"status": "ok"}


# --- Admin endpoints for scheduler ---


class ScheduleConfig(BaseModel):
    cohort_id: str
    day_of_week: str = "mon"  # mon, tue, wed, thu, fri, sat, sun
    hour: int = 6  # UTC hour (6 UTC = 9 AM EAT)
    minute: int = 0
    timezone: str = "UTC"


@router.get("/admin/schedule/{cohort_id}")
async def get_cohort_schedule(cohort_id: str):
    schedule = get_schedule(cohort_id)
    return {"cohort_id": cohort_id, **schedule}


@router.put("/admin/schedule")
async def set_cohort_schedule(config: ScheduleConfig):
    """Set the weekly AI-initiated conversation schedule for a cohort."""
    update_cohort_schedule(
        cohort_id=config.cohort_id,
        day_of_week=config.day_of_week,
        hour=config.hour,
        minute=config.minute,
        tz=config.timezone,
    )
    return {"status": "ok", "schedule": config.model_dump()}


@router.post("/admin/trigger/{cohort_id}")
async def trigger_conversations(cohort_id: str):
    """Manually trigger AI-initiated conversations for a cohort (for testing)."""
    await initiate_conversations_for_cohort(cohort_id if cohort_id != "all" else None)
    return {"status": "triggered", "cohort_id": cohort_id}
