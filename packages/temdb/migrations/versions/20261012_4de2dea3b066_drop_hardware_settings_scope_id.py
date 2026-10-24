"""drop scope_id from acquisitions.hardware_settings

Revision ID: 4de2dea3b066
Revises: d4b8e2f1a7c9
Create Date: 2026-10-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4de2dea3b066"
down_revision: str | Sequence[str] | None = "d4b8e2f1a7c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop scope_id; stop if any scope_id is not its microscope's label, since the downgrade could not restore it."""
    mismatched = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT a.acquisition_id FROM acquisitions a JOIN microscopes m USING (microscope_id)"
                " WHERE a.hardware_settings ->> 'scope_id' <> m.label"
            )
        )
        .scalars()
        .all()
    )
    if mismatched:
        raise RuntimeError(f"scope_id is not the microscope label for acquisitions {mismatched}")
    op.execute("UPDATE acquisitions SET hardware_settings = hardware_settings - 'scope_id'")


def downgrade() -> None:
    """Restore scope_id as the microscope's label."""
    op.execute(
        "UPDATE acquisitions a SET hardware_settings = a.hardware_settings || jsonb_build_object('scope_id', m.label)"
        " FROM microscopes m WHERE m.microscope_id = a.microscope_id"
    )
