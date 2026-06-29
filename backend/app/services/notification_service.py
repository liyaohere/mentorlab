import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification, NotificationStatus
from app.models.participant import Participant

logger = logging.getLogger(__name__)

# Firebase Admin SDK — lazy init
_firebase_initialized = False


def _init_firebase():
    global _firebase_initialized
    if _firebase_initialized:
        return True
    if not settings.FCM_CREDENTIALS_PATH:
        logger.warning("FCM_CREDENTIALS_PATH not set — push notifications disabled")
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.FCM_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return False


class NotificationService:
    async def send_push(
        self,
        participant: Participant,
        message_id: str,
        db: AsyncSession,
        title: str = "MentorLab",
        body: str = "Your mentor has a new message for you",
    ) -> Notification | None:
        """Send a push notification to a participant. Returns the Notification record."""
        # Create notification record regardless of whether push succeeds
        notification = Notification(
            participant_id=participant.id,
            message_id=message_id,
            sent_at=datetime.now(timezone.utc),
            status=NotificationStatus.sent,
        )
        db.add(notification)

        if not participant.fcm_token:
            logger.info(
                f"No FCM token for participant {participant.id} — skipping push"
            )
            notification.status = NotificationStatus.failed
            await db.flush()
            return notification

        if not _init_firebase():
            logger.info("Firebase not configured — notification recorded but not sent")
            notification.status = NotificationStatus.failed
            await db.flush()
            return notification

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    "type": "new_message",
                    "message_id": str(message_id),
                },
                token=participant.fcm_token,
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        click_action="OPEN_CONVERSATION",
                        channel_id="mentorlab_messages",
                    ),
                ),
            )

            response = messaging.send(message)
            logger.info(f"FCM sent to participant {participant.id}: {response}")
            notification.status = NotificationStatus.sent
        except Exception as e:
            logger.error(f"FCM send failed for participant {participant.id}: {e}")
            notification.status = NotificationStatus.failed

        await db.flush()
        return notification

    async def mark_delivered(self, notification_id: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notif = result.scalar_one_or_none()
        if notif:
            notif.delivered_at = datetime.now(timezone.utc)
            notif.status = NotificationStatus.delivered
            await db.flush()

    async def mark_opened(self, notification_id: str, db: AsyncSession) -> None:
        result = await db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        notif = result.scalar_one_or_none()
        if notif:
            notif.opened_at = datetime.now(timezone.utc)
            notif.status = NotificationStatus.opened
            await db.flush()


notification_service = NotificationService()
