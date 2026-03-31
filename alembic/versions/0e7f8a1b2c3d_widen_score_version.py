"""widen score_version column

Revision ID: 0e7f8a1b2c3d
Revises: 4632c1f1966b
Create Date: 2026-03-31 11:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0e7f8a1b2c3d"
down_revision: Union[str, Sequence[str], None] = "4632c1f1966b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "subnet_scores",
        "score_version",
        existing_type=sa.String(length=16),
        type_=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "subnet_scores",
        "score_version",
        existing_type=sa.String(length=64),
        type_=sa.String(length=16),
        existing_nullable=False,
    )
