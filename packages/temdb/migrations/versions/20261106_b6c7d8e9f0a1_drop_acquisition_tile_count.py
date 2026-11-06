"""Drop acquisitions.tile_count.

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b6c7d8e9f0a1"
down_revision: str | Sequence[str] | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("acquisitions", "tile_count")


def downgrade() -> None:
    op.add_column("acquisitions", sa.Column("tile_count", sa.Integer(), nullable=True))
