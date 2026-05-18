import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.participant import ArmType, InviteCode

# Use in-memory SQLite with shared cache for tests (single connection pool)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _get_test_db():
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def override_db():
    """Override the get_db dependency to use test database."""
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_invite_codes():
    """Create test invite codes via the same session pool."""
    async with TestSession() as session:
        codes = [
            InviteCode(code="TEST001A", arm=ArmType.c1, cohort_id="test"),
            InviteCode(code="TEST002B", arm=ArmType.c2, cohort_id="test"),
            InviteCode(code="TEST003C", arm=ArmType.c3, cohort_id="test"),
        ]
        for code in codes:
            session.add(code)
        await session.commit()
    return codes


@pytest.fixture
def mock_claude():
    """Mock Claude API to return deterministic responses."""
    async def fake_get_response(self, participant, conversation, messages):
        return "This is a test AI response.", {"input_tokens": 100, "output_tokens": 50}

    async def fake_get_greeting(self, participant, conversation):
        return "Welcome! I'm your mentor. How is your venture going this week?", {"input_tokens": 80, "output_tokens": 30}

    with patch("app.services.claude_service.ClaudeService.get_response", fake_get_response), \
         patch("app.services.claude_service.ClaudeService.get_greeting", fake_get_greeting):
        yield
