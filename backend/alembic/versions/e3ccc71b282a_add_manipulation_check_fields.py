"""add manipulation check fields

Revision ID: e3ccc71b282a
Revises: d75afea23a8c
Create Date: 2026-04-06 10:36:40.989525
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e3ccc71b282a"
down_revision: Union[str, None] = "d75afea23a8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("perceived_disagreement_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "conversations", sa.Column("perceived_breadth_score", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("conversations", "perceived_breadth_score")
    op.drop_column("conversations", "perceived_disagreement_score")
