from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.routers.auth import me_router, router as auth_router
from app.routers.conversations import router as conversations_router
from app.routers.messages import router as messages_router, sync_router
from app.routers.admin import router as admin_router
from app.routers.notifications import router as notifications_router
from app.routers.surveys import router as surveys_router
from app.routers.voice import router as voice_router
from app.routers.interview import router as interview_router
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
app.include_router(interview_router)


CURRENT_APP_VERSION = "1.0.0"
MINIMUM_APP_VERSION = "1.0.0"
APK_DOWNLOAD_URL = "https://mentorlab.app/download"


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/api/v1/admin/login")
async def admin_login(credentials: dict):
    """Validate admin credentials and return the API key for subsequent requests."""
    password = credentials.get("password", "")
    if not settings.ADMIN_API_KEY:
        return {"api_key": "", "message": "No admin key configured — open access"}
    if password == settings.ADMIN_API_KEY:
        return {"api_key": settings.ADMIN_API_KEY}
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Invalid password")


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


# --- Static files: Admin panel + Web app ---
STATIC_DIR = Path(__file__).parent.parent / "static"

if (STATIC_DIR / "admin").exists():
    @app.get("/admin")
    async def admin_index():
        return FileResponse(STATIC_DIR / "admin" / "index.html")
    app.mount("/admin", StaticFiles(directory=STATIC_DIR / "admin", html=True), name="admin")

if (STATIC_DIR / "app").exists():
    @app.get("/interview")
    async def interview_index():
        """V2 interview platform."""
        return FileResponse(
            STATIC_DIR / "app" / "interview.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    @app.get("/")
    async def app_index():
        return FileResponse(
            STATIC_DIR / "app" / "index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
    app.mount("/app", StaticFiles(directory=STATIC_DIR / "app", html=True), name="webapp")
