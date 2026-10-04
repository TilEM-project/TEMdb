"""tiles (dataset_id, run_id) foreign key to acquisitions

Revision ID: d4b8e2f1a7c9
Revises: c7e1d9a4f2b3
Create Date: 2026-10-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8e2f1a7c9"
down_revision: str | Sequence[str] | None = "c7e1d9a4f2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint("uq_acquisitions_dataset_run", "acquisitions", ["dataset_id", "run_id"])
    op.create_foreign_key(
        "fk_tiles_dataset_id_acquisitions",
        "tiles",
        "acquisitions",
        ["dataset_id", "run_id"],
        ["dataset_id", "run_id"],
    )
    op.drop_index("ix_acquisitions_dataset_id_nn", table_name="acquisitions")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        "ix_acquisitions_dataset_id_nn",
        "acquisitions",
        ["dataset_id"],
        postgresql_where=sa.text("dataset_id IS NOT NULL"),
    )
    op.drop_constraint("fk_tiles_dataset_id_acquisitions", "tiles", type_="foreignkey")
    op.drop_constraint("uq_acquisitions_dataset_run", "acquisitions", type_="unique")
