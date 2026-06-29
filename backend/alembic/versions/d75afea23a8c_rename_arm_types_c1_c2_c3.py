"""rename arm types c1 c2 c3

Revision ID: d75afea23a8c
Revises: 1dd075efc544
Create Date: 2026-04-06 10:21:13.127725
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d75afea23a8c"
down_revision: Union[str, None] = "1dd075efc544"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename PostgreSQL enum values: control→c1, analytic→c2, constructive→c3
    op.execute("ALTER TYPE armtype RENAME VALUE 'control' TO 'c1'")
    op.execute("ALTER TYPE armtype RENAME VALUE 'analytic' TO 'c2'")
    op.execute("ALTER TYPE armtype RENAME VALUE 'constructive' TO 'c3'")


def downgrade() -> None:
    op.execute("ALTER TYPE armtype RENAME VALUE 'c1' TO 'control'")
    op.execute("ALTER TYPE armtype RENAME VALUE 'c2' TO 'analytic'")
    op.execute("ALTER TYPE armtype RENAME VALUE 'c3' TO 'constructive'")
