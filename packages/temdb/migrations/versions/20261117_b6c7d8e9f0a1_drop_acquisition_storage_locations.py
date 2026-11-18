"""
Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b6c7d8e9f0a1"
down_revision: str | Sequence[str] | None = "a5b6c7d8e9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE acquisitions SET extra = extra || jsonb_build_object('storage_locations', storage_locations) "
        "WHERE storage_locations IS NOT NULL AND storage_locations <> '[]'::jsonb"
    )
    op.drop_column("acquisitions", "storage_locations")


def downgrade() -> None:
    op.add_column("acquisitions", sa.Column("storage_locations", postgresql.JSONB(), nullable=True))
    op.execute(
        "UPDATE acquisitions SET storage_locations = extra -> 'storage_locations', extra = extra - 'storage_locations' "
        "WHERE extra ? 'storage_locations'"
    )
