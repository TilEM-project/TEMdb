"""Add structured image storage while retaining legacy tile paths.

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9b0c1d2e3f4"
down_revision: str | Sequence[str] | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("blocks", sa.Column("default_storage", postgresql.JSONB(), nullable=True))
    op.add_column("datasets", sa.Column("default_storage", postgresql.JSONB(), nullable=True))
    op.add_column("tiles", sa.Column("image", postgresql.JSONB(), nullable=True))
    op.alter_column("tiles", "image_path", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column("tiles", "image_path", existing_type=sa.String(), nullable=False)
    op.drop_column("tiles", "image")
    op.drop_column("datasets", "default_storage")
    op.drop_column("blocks", "default_storage")
