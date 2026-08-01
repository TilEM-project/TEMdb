"""add sections.run_parameters and migrate legacy nested payload

Revision ID: a1d2f3e4b5c6
Revises: 44f75ed44d66
Create Date: 2026-08-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1d2f3e4b5c6"
down_revision: str | Sequence[str] | None = "44f75ed44d66"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("sections", sa.Column("run_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.execute(
        sa.text(
            """
            UPDATE sections
            SET run_parameters = section_metrics->'run_parameters'
            WHERE run_parameters IS NULL
              AND section_metrics IS NOT NULL
              AND section_metrics ? 'run_parameters'
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE sections
            SET section_metrics = section_metrics - 'run_parameters'
            WHERE section_metrics IS NOT NULL
              AND section_metrics ? 'run_parameters'
            """
        )
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            UPDATE sections
            SET section_metrics = jsonb_set(
                COALESCE(section_metrics, '{}'::jsonb),
                '{run_parameters}',
                run_parameters,
                true
            )
            WHERE run_parameters IS NOT NULL
            """
        )
    )

    op.drop_column("sections", "run_parameters")
