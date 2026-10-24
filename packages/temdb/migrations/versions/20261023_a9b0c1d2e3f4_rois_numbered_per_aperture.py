"""rois numbered per aperture: id {media_id}.A{aperture:04d}.R{n:03d}, or {media_id}.R{n:04d} on a section with no
aperture, identified by when they were drawn

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-10-23 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a9b0c1d2e3f4"
down_revision: str | Sequence[str] | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def drop_roi_id_foreign_keys() -> None:
    op.drop_constraint("fk_rois_parent_roi_id_rois", "rois", type_="foreignkey")
    op.drop_constraint("fk_acquisition_tasks_roi_id_rois", "acquisition_tasks", type_="foreignkey")
    op.drop_constraint("fk_acquisitions_roi_id_rois", "acquisitions", type_="foreignkey")


def create_roi_id_foreign_keys() -> None:
    op.create_foreign_key("fk_rois_parent_roi_id_rois", "rois", "rois", ["parent_roi_id"], ["roi_id"])
    op.create_foreign_key("fk_acquisition_tasks_roi_id_rois", "acquisition_tasks", "rois", ["roi_id"], ["roi_id"])
    op.create_foreign_key("fk_acquisitions_roi_id_rois", "acquisitions", "rois", ["roi_id"], ["roi_id"])


def rename_rois(renames: list[dict]) -> None:
    """Give ROIs new ids and point their sub-ROIs, tasks and acquisitions at them."""
    # Old ids contain '.ROI' and new ones do not, so a new id never matches another ROI's old one.
    bind = op.get_bind()
    for statement in (
        "UPDATE rois SET roi_id = :new, roi_number = :number WHERE id = :id",
        "UPDATE rois SET parent_roi_id = :new WHERE parent_roi_id = :old",
        "UPDATE acquisition_tasks SET roi_id = :new WHERE roi_id = :old",
        "UPDATE acquisitions SET roi_id = :new WHERE roi_id = :old",
    ):
        if renames:
            bind.execute(sa.text(statement), renames)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    op.add_column("rois", sa.Column("aperture_index", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE rois SET aperture_index = s.aperture_index FROM sections s WHERE s.section_id = rois.section_id"
        )
    )
    counts: dict[tuple, int] = {}
    renames = []
    rows = bind.execute(
        sa.text("SELECT id, roi_id, substrate_media_id, aperture_index FROM rois ORDER BY created_at, id")
    ).all()
    for row in rows:
        place = (row.substrate_media_id, row.aperture_index)
        counts[place] = counts.get(place, 0) + 1
        number = counts[place]
        if row.aperture_index is None:
            new = f"{row.substrate_media_id}.R{number:04d}"
        else:
            new = f"{row.substrate_media_id}.A{row.aperture_index:04d}.R{number:03d}"
        renames.append({"id": row.id, "old": row.roi_id, "new": new, "number": number})
    drop_roi_id_foreign_keys()
    rename_rois(renames)
    create_roi_id_foreign_keys()

    op.drop_constraint("fk_rois_specimen_id_blocks", "rois", type_="foreignkey")
    op.drop_index("ix_rois_specimen_block", table_name="rois")
    for column in ("specimen_id", "block_id", "hierarchy_level", "section_number"):
        op.drop_column("rois", column)
    op.create_unique_constraint(
        "uq_rois_drawn",
        "rois",
        ["substrate_media_id", "aperture_index", "created_at"],
        postgresql_nulls_not_distinct=True,
    )
    op.create_unique_constraint(
        "uq_rois_number",
        "rois",
        ["substrate_media_id", "aperture_index", "roi_number"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.drop_constraint("uq_rois_number", "rois", type_="unique")
    op.drop_constraint("uq_rois_drawn", "rois", type_="unique")
    op.add_column("rois", sa.Column("specimen_id", sa.String(), nullable=True))
    op.add_column("rois", sa.Column("block_id", sa.String(), nullable=True))
    op.add_column("rois", sa.Column("hierarchy_level", sa.Integer(), nullable=True))
    op.add_column("rois", sa.Column("section_number", sa.Integer(), nullable=True))
    bind.execute(
        sa.text(
            "UPDATE rois SET specimen_id = s.specimen_id, block_id = s.block_id, section_number = rois.aperture_index "
            "FROM sections s WHERE s.section_id = rois.section_id"
        )
    )
    rows = {
        row.roi_id: row
        for row in bind.execute(
            sa.text(
                "SELECT id, roi_id, roi_number, parent_roi_id, section_id, substrate_media_id, specimen_id, block_id "
                "FROM rois"
            )
        ).all()
    }
    old_ids: dict[str, tuple[str, int]] = {}

    def old_id(roi_id: str) -> tuple[str, int]:
        """An ROI's pre-4.0 id and hierarchy level."""
        if roi_id not in old_ids:
            row = rows[roi_id]
            if row.parent_roi_id:
                parent, level = old_id(row.parent_roi_id)
                old_ids[roi_id] = (f"{parent}.ROI{row.roi_number - 1:04d}", level + 1)
            else:
                old_ids[roi_id] = (
                    f"{row.specimen_id}.{row.block_id}.{row.section_id}.{row.substrate_media_id}"
                    f".ROI{row.roi_number - 1:03d}",
                    1,
                )
        return old_ids[roi_id]

    renames = [
        {"id": row.id, "old": roi_id, "new": old_id(roi_id)[0], "number": row.roi_number - 1}
        for roi_id, row in rows.items()
    ]
    drop_roi_id_foreign_keys()
    rename_rois(renames)
    if renames:
        bind.execute(
            sa.text("UPDATE rois SET hierarchy_level = :level WHERE roi_id = :roi_id"),
            [{"roi_id": new, "level": level} for new, level in old_ids.values()],
        )
    create_roi_id_foreign_keys()

    for column in ("specimen_id", "block_id", "hierarchy_level"):
        op.alter_column("rois", column, nullable=False)
    op.create_index("ix_rois_specimen_block", "rois", ["specimen_id", "block_id"], unique=False)
    op.create_foreign_key(
        "fk_rois_specimen_id_blocks", "rois", "blocks", ["specimen_id", "block_id"], ["specimen_id", "block_id"]
    )
    op.drop_column("rois", "aperture_index")
