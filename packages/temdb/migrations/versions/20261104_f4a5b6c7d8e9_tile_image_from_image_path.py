"""Move tiles.image_path into tiles.image, so existing tiles keep their images, and drop image_path.

Paths look like s3u://:@host:8000@bucket/key, with a trailing newline on production rows.

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a5b6c7d8e9"
down_revision: str | Sequence[str] | None = "e3f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def s3u_parts() -> str:
    return r"regexp_match(btrim(image_path, E' \r\n'), '^s3u://[^@]*@([^@/]+)@([^/]+)/(.+)$')"


def upgrade() -> None:
    bind = op.get_bind()
    parts = s3u_parts()
    pending = "image IS NULL AND image_path IS NOT NULL"
    unreadable = bind.execute(sa.text(f"SELECT image_path FROM tiles WHERE {pending} AND {parts} IS NULL LIMIT 5"))
    examples = [repr(path) for path in unreadable.scalars()]
    if examples:
        raise RuntimeError(f"Tiles have an image_path this migration cannot convert: {', '.join(examples)}")
    bind.execute(
        sa.text(
            f"""
            UPDATE tiles SET image = jsonb_build_object(
                'protocol', 's3',
                'server', 'http://' || ({parts})[1],
                'bucket', ({parts})[2],
                'key', ({parts})[3]
            )
            WHERE {pending}
            """
        )
    )
    op.drop_column("tiles", "image_path")


def downgrade() -> None:
    op.add_column("tiles", sa.Column("image_path", sa.String(), nullable=True))
    # shortcut: only images on an http server came from an s3u path, so others keep a NULL image_path.
    op.execute(
        sa.text(
            """
            UPDATE tiles
            SET image_path = 's3u://:@' || substr(image->>'server', 8) || '@' || (image->>'bucket') || '/' || (image->>'key')
            WHERE image->>'server' LIKE 'http://%'
            """
        )
    )
