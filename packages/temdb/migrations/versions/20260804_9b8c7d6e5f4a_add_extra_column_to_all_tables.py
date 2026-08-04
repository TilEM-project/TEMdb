"""add extra column to all tables

Revision ID: 9b8c7d6e5f4a
Revises: a1d2f3e4b5c6
Create Date: 2026-08-04 13:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b8c7d6e5f4a"
down_revision: str | Sequence[str] | None = "a1d2f3e4b5c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    "microscopes",
    "specimens",
    "substrates",
    "blocks",
    "datasets",
    "lens_corrections",
    "cutting_sessions",
    "tiles",
    "sections",
    "rois",
    "acquisition_tasks",
    "acquisitions",
)


def upgrade() -> None:
    """Upgrade schema."""
    for table_name in TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "extra",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
        )

    for table_name in TABLES:
        op.alter_column(
            table_name,
            "extra",
            existing_type=postgresql.JSONB(astext_type=sa.Text()),
            server_default=None,
            existing_nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table_name in reversed(TABLES):
        op.drop_column(table_name, "extra")
