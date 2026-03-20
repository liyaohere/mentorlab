from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.auth import me_router, router as auth_router
from app.routers.conversations import router as conversations_router
from app.routers.messages import router as messages_router, sync_router
from app.routers.admin import router as admin_router
from app.routers.notifications import router as notifications_router
from app.routers.surveys import router as surveys_router
from app.routers.voice import router as voice_router
from app.services.scheduler_service import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="MentorLab API",
    description="AI Mentor RCT Platform for entrepreneurial mentoring research",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(me_router)
app.include_router(conversations_router)
app.include_router(messages_router)
app.include_router(sync_router)
app.include_router(voice_router)
app.include_router(surveys_router)
app.include_router(notifications_router)
app.include_router(admin_router)


CURRENT_APP_VERSION = "1.0.0"
MINIMUM_APP_VERSION = "1.0.0"
APK_DOWNLOAD_URL = "https://mentorlab.app/download"


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/api/v1/version")
async def check_version(current: str = ""):
    """App calls this on launch to check if an update is available."""
    update_available = current < CURRENT_APP_VERSION if current else False
    force_update = current < MINIMUM_APP_VERSION if current else False
    return {
        "latest_version": CURRENT_APP_VERSION,
        "minimum_version": MINIMUM_APP_VERSION,
        "update_available": update_available,
        "force_update": force_update,
        "download_url": APK_DOWNLOAD_URL,
    }
