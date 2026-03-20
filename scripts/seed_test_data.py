"""
Seed script: creates test invite codes (one per arm) for development.
Run: python -m scripts.seed_test_data (from the backend/ directory)
Or:  cd backend && python ../scripts/seed_test_data.py
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import text
from app.config import settings
from app.database import async_session, engine, Base
from app.models import *  # noqa
from app.models.participant import ArmType, InviteCode
from app.utils.invite_codes import generate_invite_code


async def seed():
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Check if codes already exist
        result = await session.execute(text("SELECT COUNT(*) FROM invite_codes"))
        count = result.scalar()
        if count > 0:
            print(f"Database already has {count} invite codes. Skipping seed.")
            return

        # Create 3 test invite codes (one per arm) + 6 more for testing
        test_codes = [
            ("TEST001A", ArmType.control, "pilot_test"),
            ("TEST002B", ArmType.analytic, "pilot_test"),
            ("TEST003C", ArmType.constructive, "pilot_test"),
            # Extra codes for bulk testing
            (generate_invite_code(), ArmType.control, "pilot_test"),
            (generate_invite_code(), ArmType.analytic, "pilot_test"),
            (generate_invite_code(), ArmType.constructive, "pilot_test"),
            (generate_invite_code(), ArmType.control, "pilot_test"),
            (generate_invite_code(), ArmType.analytic, "pilot_test"),
            (generate_invite_code(), ArmType.constructive, "pilot_test"),
        ]

        for code, arm, cohort in test_codes:
            invite = InviteCode(code=code, arm=arm, cohort_id=cohort)
            session.add(invite)

        await session.commit()
        print("Seeded test data:")
        print("  Invite codes:")
        for code, arm, cohort in test_codes:
            print(f"    {code} → {arm.value} (cohort: {cohort})")


if __name__ == "__main__":
    asyncio.run(seed())
