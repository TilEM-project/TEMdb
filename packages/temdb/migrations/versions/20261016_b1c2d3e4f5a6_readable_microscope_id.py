"""readable microscope_id

Revision ID: b1c2d3e4f5a6
Revises: 6441fe7b2a3e
Create Date: 2026-10-16 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | Sequence[str] | None = "6441fe7b2a3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

referencing_tables = ("acquisitions", "lens_corrections")


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("ix_lens_corrections_microscope_mag", table_name="lens_corrections")
    for table in referencing_tables:
        op.drop_constraint(op.f(f"fk_{table}_microscope_id_microscopes"), table, type_="foreignkey")
        op.add_column(table, sa.Column("microscope_label", sa.String(), nullable=True))
        op.execute(
            f"UPDATE {table} t SET microscope_label = m.label FROM microscopes m WHERE m.microscope_id = t.microscope_id"
        )
        op.drop_column(table, "microscope_id")
        op.alter_column(table, "microscope_label", new_column_name="microscope_id", nullable=False)
    op.drop_constraint(op.f("pk_microscopes"), "microscopes", type_="primary")
    op.drop_column("microscopes", "microscope_id")
    op.alter_column("microscopes", "label", new_column_name="microscope_id")
    op.execute("ALTER TABLE microscopes RENAME CONSTRAINT uq_microscopes_label TO uq_microscopes_microscope_id")
    op.add_column("microscopes", sa.Column("id", sa.Integer(), sa.Identity(always=True), nullable=False))
    op.create_primary_key(op.f("pk_microscopes"), "microscopes", ["id"])
    for table in referencing_tables:
        op.create_foreign_key(
            op.f(f"fk_{table}_microscope_id_microscopes"), table, "microscopes", ["microscope_id"], ["microscope_id"]
        )
    op.create_index(
        "ix_lens_corrections_microscope_mag",
        "lens_corrections",
        ["microscope_id", "magnification", sa.literal_column("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_lens_corrections_microscope_mag", table_name="lens_corrections")
    for table in referencing_tables:
        op.drop_constraint(op.f(f"fk_{table}_microscope_id_microscopes"), table, type_="foreignkey")
    op.drop_constraint(op.f("pk_microscopes"), "microscopes", type_="primary")
    op.drop_column("microscopes", "id")
    op.execute("ALTER TABLE microscopes RENAME CONSTRAINT uq_microscopes_microscope_id TO uq_microscopes_label")
    op.alter_column("microscopes", "microscope_id", new_column_name="label")
    op.add_column(
        "microscopes",
        sa.Column("microscope_id", sa.UUID(), server_default=sa.text("uuidv7()"), nullable=False),
    )
    op.create_primary_key(op.f("pk_microscopes"), "microscopes", ["microscope_id"])
    for table in referencing_tables:
        op.add_column(table, sa.Column("microscope_uuid", postgresql.UUID(), nullable=True))
        op.execute(
            f"UPDATE {table} t SET microscope_uuid = m.microscope_id FROM microscopes m WHERE m.label = t.microscope_id"
        )
        op.drop_column(table, "microscope_id")
        op.alter_column(table, "microscope_uuid", new_column_name="microscope_id", nullable=False)
        op.create_foreign_key(
            op.f(f"fk_{table}_microscope_id_microscopes"), table, "microscopes", ["microscope_id"], ["microscope_id"]
        )
    op.create_index(
        "ix_lens_corrections_microscope_mag",
        "lens_corrections",
        ["microscope_id", "magnification", sa.literal_column("started_at DESC")],
        unique=False,
    )
