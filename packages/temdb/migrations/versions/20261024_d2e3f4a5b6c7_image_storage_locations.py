"""Add structured image storage while retaining legacy tile paths.

Revision ID: d2e3f4a5b6c7
Revises: b0c1d2e3f4a5
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "b0c1d2e3f4a5"
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
