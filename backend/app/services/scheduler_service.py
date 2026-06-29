"""
Scheduler for AI-initiated conversations.

Uses APScheduler to fire weekly conversation initiations at configured times.
Each cohort can have its own schedule (day_of_week, hour, minute, timezone).
"""

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session as default_session_factory
from app.models.conversation import Conversation, InitiatorType
from app.models.message import Message, MessageRole, SyncStatus
from app.models.participant import Participant, ParticipantStatus
from app.services.claude_service import claude_service
from app.services.notification_service import notification_service

logger = logging.getLogger(__name__)

# Default schedule: Monday 9:00 AM EAT (UTC+3 = 06:00 UTC)
DEFAULT_SCHEDULE = {
    "day_of_week": "mon",
    "hour": 6,
    "minute": 0,
    "timezone": "UTC",
}

# In-memory schedule config (overridable via admin API)
_schedules: dict[str, dict] = {}


def get_schedule(cohort_id: str) -> dict:
    return _schedules.get(cohort_id, DEFAULT_SCHEDULE)


def set_schedule(cohort_id: str, schedule: dict) -> None:
    _schedules[cohort_id] = schedule
    logger.info(f"Schedule updated for cohort {cohort_id}: {schedule}")


def _compute_week_number(participant: Participant) -> int:
    now = datetime.now(timezone.utc)
    created = participant.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    days_since = (now - created).days
    return max(1, (days_since // 7) + 1)


# Overridable session factory (for tests)
_session_factory = None


def set_session_factory(factory):
    global _session_factory
    _session_factory = factory


def _get_session_factory():
    return _session_factory or default_session_factory


async def initiate_conversations_for_cohort(cohort_id: str | None = None):
    """
    Create AI-initiated conversations for all active participants in a cohort.
    Called by the scheduler at the configured time.
    """
    logger.info(f"Initiating conversations for cohort: {cohort_id or 'all'}")

    session_factory = _get_session_factory()
    async with session_factory() as db:
        # Get all active participants (optionally filtered by cohort)
        query = select(Participant).where(
            Participant.status == ParticipantStatus.active
        )
        if cohort_id:
            query = query.where(Participant.cohort_id == cohort_id)

        result = await db.execute(query)
        participants = list(result.scalars().all())

        if not participants:
            logger.info("No active participants found")
            return

        logger.info(f"Initiating conversations for {len(participants)} participants")

        success_count = 0
        error_count = 0

        for participant in participants:
            try:
                week_number = _compute_week_number(participant)

                # Create conversation
                conversation = Conversation(
                    participant_id=participant.id,
                    week_number=week_number,
                    initiated_by=InitiatorType.system,
                )
                db.add(conversation)
                await db.flush()

                # Generate AI opening message
                greeting_text, token_usage = await claude_service.get_greeting(
                    participant, conversation
                )

                greeting_msg = Message(
                    conversation_id=conversation.id,
                    role=MessageRole.assistant,
                    content=greeting_text,
                    token_usage=token_usage,
                    sync_status=SyncStatus.synced,
                    sent_at=datetime.now(timezone.utc),
                )
                db.add(greeting_msg)
                await db.flush()

                # Send push notification
                await notification_service.send_push(
                    participant=participant,
                    message_id=str(greeting_msg.id),
                    db=db,
                )

                success_count += 1
                logger.info(
                    f"Initiated week {week_number} conversation for "
                    f"participant {participant.id} ({participant.name})"
                )

            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to initiate conversation for participant "
                    f"{participant.id}: {e}"
                )

        await db.commit()
        logger.info(
            f"Conversation initiation complete: "
            f"{success_count} success, {error_count} errors"
        )


# --- Scheduler setup ---

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start the APScheduler with the default job. Called on app startup."""
    if scheduler.running:
        return

    # Add default job for all participants (no cohort filter)
    scheduler.add_job(
        initiate_conversations_for_cohort,
        trigger=CronTrigger(
            day_of_week=DEFAULT_SCHEDULE["day_of_week"],
            hour=DEFAULT_SCHEDULE["hour"],
            minute=DEFAULT_SCHEDULE["minute"],
            timezone=DEFAULT_SCHEDULE["timezone"],
        ),
        id="default_initiator",
        replace_existing=True,
        kwargs={"cohort_id": None},
    )

    scheduler.start()
    logger.info(
        f"Scheduler started. Default job: {DEFAULT_SCHEDULE['day_of_week']} "
        f"at {DEFAULT_SCHEDULE['hour']:02d}:{DEFAULT_SCHEDULE['minute']:02d} UTC"
    )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def update_cohort_schedule(
    cohort_id: str, day_of_week: str, hour: int, minute: int, tz: str = "UTC"
):
    """Add or update a cohort-specific schedule."""
    set_schedule(
        cohort_id,
        {
            "day_of_week": day_of_week,
            "hour": hour,
            "minute": minute,
            "timezone": tz,
        },
    )

    job_id = f"initiator_{cohort_id}"

    if scheduler.running:
        scheduler.add_job(
            initiate_conversations_for_cohort,
            trigger=CronTrigger(
                day_of_week=day_of_week,
                hour=hour,
                minute=minute,
                timezone=tz,
            ),
            id=job_id,
            replace_existing=True,
            kwargs={"cohort_id": cohort_id},
        )
        logger.info(
            f"Cohort schedule updated: {cohort_id} → {day_of_week} {hour:02d}:{minute:02d} {tz}"
        )
