"""add v2 interview fields to conversations and condition to participants

Revision ID: 1dd075efc544
Revises: b73391c6438f
Create Date: 2026-04-04 10:57:01.474251
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1dd075efc544"
down_revision: Union[str, None] = "b73391c6438f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types first
    conversationstatus = postgresql.ENUM(
        "intake",
        "baseline",
        "analyzing",
        "diagnosis",
        "response",
        "survey",
        "complete",
        "active",
        name="conversationstatus",
        create_type=False,
    )
    conversationstatus.create(op.get_bind(), checkfirst=True)

    conditiontype = postgresql.ENUM(
        "single",
        "integrated",
        "competing",
        name="conditiontype",
        create_type=False,
    )
    conditiontype.create(op.get_bind(), checkfirst=True)

    # Add columns — status and intake fields need server_default for existing rows
    op.add_column(
        "conversations",
        sa.Column(
            "status", conversationstatus, nullable=False, server_default="active"
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "intake_complete", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "intake_responses", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "intake_question_index", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "baseline_responses", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "orchestrator_output", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "conversations",
        sa.Column(
            "diagnosis_raw", postgresql.JSON(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "conversations", sa.Column("diagnosis_integrated", sa.Text(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("diagnosis_shown", sa.Text(), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("divergence_check", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("selection_choice", sa.Integer(), nullable=True)
    )
    op.add_column("conversations", sa.Column("response_text", sa.Text(), nullable=True))
    op.add_column(
        "conversations",
        sa.Column("response_created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("cognitive_load_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "conversations",
        sa.Column("perceived_confusion_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("trust_in_advice_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("confidence_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("ownership_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("reading_time_seconds", sa.Integer(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("writing_time_seconds", sa.Integer(), nullable=True)
    )
    op.add_column(
        "conversations", sa.Column("session_audio_url", sa.Text(), nullable=True)
    )
    op.add_column("participants", sa.Column("condition", conditiontype, nullable=True))


def downgrade() -> None:
    op.drop_column("participants", "condition")
    op.drop_column("conversations", "session_audio_url")
    op.drop_column("conversations", "writing_time_seconds")
    op.drop_column("conversations", "reading_time_seconds")
    op.drop_column("conversations", "ownership_score")
    op.drop_column("conversations", "confidence_score")
    op.drop_column("conversations", "trust_in_advice_score")
    op.drop_column("conversations", "perceived_confusion_score")
    op.drop_column("conversations", "cognitive_load_score")
    op.drop_column("conversations", "response_created_at")
    op.drop_column("conversations", "response_text")
    op.drop_column("conversations", "selection_choice")
    op.drop_column("conversations", "divergence_check")
    op.drop_column("conversations", "diagnosis_shown")
    op.drop_column("conversations", "diagnosis_integrated")
    op.drop_column("conversations", "diagnosis_raw")
    op.drop_column("conversations", "orchestrator_output")
    op.drop_column("conversations", "baseline_responses")
    op.drop_column("conversations", "intake_question_index")
    op.drop_column("conversations", "intake_responses")
    op.drop_column("conversations", "intake_complete")
    op.drop_column("conversations", "status")
    # Drop enum types
    postgresql.ENUM(name="conversationstatus").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="conditiontype").drop(op.get_bind(), checkfirst=True)
