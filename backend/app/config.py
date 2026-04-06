import json
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mentorlab"

    # JWT
    JWT_SECRET_KEY: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_DAYS: int = 90

    # AI Provider: "anthropic" or "openai"
    AI_PROVIDER: str = "anthropic"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-opus-4-20250514"
    CLAUDE_MAX_TOKENS: int = 500

    # OpenAI (used for Whisper + optionally as AI provider)
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o"

    # V2 Diagnosis Pipeline
    DIAGNOSIS_MODEL: str = "claude-opus-4-20250514"
    DIAGNOSIS_MAX_TOKENS: int = 300
    OPENAI_TTS_MODEL: str = "tts-1-hd"
    OPENAI_TTS_VOICE: str = "onyx"
    OPENAI_TTS_SPEED: float = 0.95

    # S3-compatible storage
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET_NAME: str = "mentorlab-audio"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""

    # Admin panel authentication
    ADMIN_API_KEY: str = ""  # Set this to protect admin endpoints

    # FCM (Phase 3)
    FCM_CREDENTIALS_PATH: str = ""

    # CORS
    CORS_ORIGINS: str = '["http://localhost:8081","http://localhost:19006","http://localhost:5173"]'

    @property
    def cors_origins_list(self) -> list[str]:
        return json.loads(self.CORS_ORIGINS)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
