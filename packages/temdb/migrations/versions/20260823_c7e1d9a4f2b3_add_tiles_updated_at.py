"""add tiles.updated_at

Revision ID: c7e1d9a4f2b3
Revises: a1d2f3e4b5c6
Create Date: 2026-08-23 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7e1d9a4f2b3"
down_revision: str | Sequence[str] | None = "a1d2f3e4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("tiles", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("tiles", "updated_at")
