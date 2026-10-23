"""sections drop barcode: a slot's barcode is its position on the substrate

Each stored barcode moves to extra["barcode"] unchanged, so values that are not media_id + aperture index are kept.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-10-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a9b0c1d2e3"
down_revision: str | Sequence[str] | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "UPDATE sections SET extra = coalesce(extra, '{}'::jsonb) || jsonb_build_object('barcode', barcode) "
        "WHERE barcode IS NOT NULL"
    )
    op.drop_index("ix_sections_barcode_nn", table_name="sections")
    op.drop_column("sections", "barcode")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("sections", sa.Column("barcode", sa.String(), nullable=True))
    op.create_index("ix_sections_barcode_nn", "sections", ["barcode"], postgresql_where=sa.text("barcode IS NOT NULL"))
    op.execute("UPDATE sections SET barcode = extra ->> 'barcode', extra = extra - 'barcode' WHERE extra ? 'barcode'")
