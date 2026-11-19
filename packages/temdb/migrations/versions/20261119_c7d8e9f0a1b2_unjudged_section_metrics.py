"""
Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | Sequence[str] | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # prototome never judges these two metrics; their stored pass_status true came from the old default
    for metric in ("segmentation", "capture_overlap"):
        op.execute(
            f"UPDATE sections SET section_metrics = jsonb_set(section_metrics, '{{{metric},pass_status}}', 'null') "
            f"WHERE section_metrics -> '{metric}' -> 'pass_status' = 'true'"
        )


def downgrade() -> None:
    for metric in ("segmentation", "capture_overlap"):
        op.execute(
            f"UPDATE sections SET section_metrics = jsonb_set(section_metrics, '{{{metric},pass_status}}', 'true') "
            f"WHERE section_metrics -> '{metric}' -> 'pass_status' = 'null'"
        )
