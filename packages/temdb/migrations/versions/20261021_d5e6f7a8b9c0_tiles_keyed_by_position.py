"""tiles keyed by position, with a stage z

Revision ID: d5e6f7a8b9c0
Revises: b1c2d3e4f5a6
Create Date: 2026-10-21 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: str | Sequence[str] | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def stop_on_rows(query: sa.Select, problem: str) -> None:
    """Raise with up to 20 of the rows the query returns, so the migration stops instead of changing them."""
    rows = op.get_bind().execute(query.limit(20)).all()
    if rows:
        listed = "\n".join(str(tuple(row)) for row in rows)
        raise RuntimeError(f"{problem}; first rows:\n{listed}")


def upgrade() -> None:
    """Upgrade schema."""
    tiles = sa.table(
        "tiles",
        sa.column("dataset_id"),
        sa.column("run_id"),
        sa.column("raster_index"),
        sa.column("montage_row"),
        sa.column("montage_col"),
    )
    position = (tiles.c.dataset_id, tiles.c.run_id, tiles.c.montage_row, tiles.c.montage_col)
    stop_on_rows(
        sa.select(*position, tiles.c.raster_index).where(
            sa.or_(~tiles.c.montage_row.between(0, 32767), ~tiles.c.montage_col.between(0, 32767))
        ),
        "tiles with a row or column outside 0..32767 cannot be keyed by position",
    )
    stop_on_rows(
        sa.select(*position, sa.func.count()).group_by(*position).having(sa.func.count() > 1),
        "runs with two tiles at one position cannot be keyed by position",
    )
    op.drop_index(op.f("ix_tiles_tile_id"), table_name="tiles")
    op.drop_column("tiles", "tile_id")
    op.drop_column("tiles", "extra")
    op.drop_constraint(op.f("pk_tiles"), "tiles", type_="primary")
    for old, new in (("montage_row", "row"), ("montage_col", "col")):
        op.alter_column(
            "tiles",
            old,
            new_column_name=new,
            type_=sa.SmallInteger(),
            existing_type=sa.Integer(),
            existing_nullable=False,
        )
    op.add_column("tiles", sa.Column("retake", sa.SmallInteger(), server_default=sa.text("0"), nullable=False))
    op.add_column("tiles", sa.Column("stage_z_nm", sa.Float(), nullable=True))
    op.create_primary_key(op.f("pk_tiles"), "tiles", ["dataset_id", "run_id", "row", "col", "retake"])


def downgrade() -> None:
    """Downgrade schema."""
    tiles = sa.table(
        "tiles",
        sa.column("dataset_id"),
        sa.column("run_id"),
        sa.column("raster_index"),
        sa.column("row"),
        sa.column("col"),
        sa.column("retake"),
    )
    stop_on_rows(
        sa.select(tiles.c.dataset_id, tiles.c.run_id, tiles.c.row, tiles.c.col, tiles.c.retake).where(
            tiles.c.retake > 0
        ),
        "tiles with a retake cannot be keyed by raster_index",
    )
    key = (tiles.c.dataset_id, tiles.c.run_id, tiles.c.raster_index)
    stop_on_rows(
        sa.select(*key, sa.func.count()).group_by(*key).having(sa.func.count() > 1),
        "runs with two tiles at one raster_index cannot be keyed by raster_index",
    )
    op.drop_constraint(op.f("pk_tiles"), "tiles", type_="primary")
    op.drop_column("tiles", "stage_z_nm")
    op.drop_column("tiles", "retake")
    for old, new in (("row", "montage_row"), ("col", "montage_col")):
        op.alter_column(
            "tiles",
            old,
            new_column_name=new,
            type_=sa.Integer(),
            existing_type=sa.SmallInteger(),
            existing_nullable=False,
        )
    op.add_column(
        "tiles",
        sa.Column(
            "extra", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
    )
    op.alter_column("tiles", "extra", server_default=None)
    op.add_column("tiles", sa.Column("tile_id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False))
    op.create_index(op.f("ix_tiles_tile_id"), "tiles", ["tile_id"], unique=False)
    op.create_primary_key(op.f("pk_tiles"), "tiles", ["dataset_id", "run_id", "raster_index"])
