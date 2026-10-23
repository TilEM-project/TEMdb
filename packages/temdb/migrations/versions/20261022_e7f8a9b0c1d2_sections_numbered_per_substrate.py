"""sections numbered per substrate, unique per placement, with a cut_count

Sections sharing a placement (media_id, aperture_index, timestamp) are distinct cuts whose placement a batch update
copied from one onto the others; the highest-numbered section of each such group keeps it and the others are deleted.

Revision ID: e7f8a9b0c1d2
Revises: d5e6f7a8b9c0
Create Date: 2026-10-22 00:00:00.000000
"""

import logging
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | Sequence[str] | None = "d5e6f7a8b9c0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def stop_on_rows(query: sa.Select, problem: str) -> None:
    """Raise with up to 20 of the rows the query returns, so the migration stops instead of changing them."""
    rows = op.get_bind().execute(query.limit(20)).all()
    if rows:
        listed = "\n".join(str(tuple(row)) for row in rows)
        raise RuntimeError(f"{problem}; first rows:\n{listed}")


def sections_table() -> sa.TableClause:
    return sa.table(
        "sections",
        sa.column("section_id"),
        sa.column("section_number"),
        sa.column("cutting_session_id"),
        sa.column("media_id"),
        sa.column("aperture_index"),
        sa.column("timestamp"),
        sa.column("cut_count"),
    )


def upgrade() -> None:
    """Upgrade schema."""
    sections = sections_table()
    rois = sa.table("rois", sa.column("roi_id"), sa.column("section_id"))
    placement = (sections.c.media_id, sections.c.aperture_index, sections.c.timestamp)
    highest = sa.func.max(sections.c.section_number).over(partition_by=placement)
    ranked = sa.select(sections.c.section_id, sections.c.section_number, highest.label("highest")).subquery()
    copied = sa.select(ranked.c.section_id).where(ranked.c.section_number < ranked.c.highest)
    stop_on_rows(
        sa.select(rois.c.roi_id, rois.c.section_id).where(rois.c.section_id.in_(copied)).order_by(rois.c.section_id),
        "sections whose placement was copied from another would be deleted, but these have ROIs",
    )
    deleted = (
        op.get_bind()
        .execute(sections.delete().where(sections.c.section_id.in_(copied)).returning(sections.c.section_id))
        .scalars()
        .all()
    )
    if deleted:
        logging.getLogger("alembic.runtime.migration").info(
            "deleted %d sections whose placement was copied from another: %s", len(deleted), sorted(deleted)
        )
    number = (sections.c.media_id, sections.c.section_number)
    stop_on_rows(
        sa.select(*number, sa.func.string_agg(sections.c.section_id, sa.literal(", ")))
        .group_by(*number)
        .having(sa.func.count() > 1)
        .order_by(*number),
        "sections sharing a substrate and section_number cannot be numbered per substrate",
    )
    op.add_column("sections", sa.Column("cut_count", sa.Integer(), nullable=True))
    op.execute(sections.update().values(cut_count=sections.c.section_number))
    op.drop_constraint("uq_sections_session_number", "sections", type_="unique")
    op.create_unique_constraint("uq_sections_media_number", "sections", ["media_id", "section_number"])
    op.create_unique_constraint(
        "uq_sections_placement",
        "sections",
        ["media_id", "aperture_index", "timestamp"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    sections = sections_table()
    number = (sections.c.cutting_session_id, sections.c.section_number)
    stop_on_rows(
        sa.select(*number, sa.func.string_agg(sections.c.section_id, sa.literal(", ")))
        .group_by(*number)
        .having(sa.func.count() > 1)
        .order_by(*number),
        "sections sharing a cutting session and section_number cannot be numbered per session",
    )
    op.drop_constraint("uq_sections_placement", "sections", type_="unique")
    op.drop_constraint("uq_sections_media_number", "sections", type_="unique")
    op.create_unique_constraint("uq_sections_session_number", "sections", ["cutting_session_id", "section_number"])
    op.drop_column("sections", "cut_count")
