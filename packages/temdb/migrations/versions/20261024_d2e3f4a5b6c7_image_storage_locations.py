"""Add structured image storage while retaining legacy tile paths.

sections.optical_image becomes one FileObject: the "thumbnail" entry when it is an S3 URL without metadata. Every other
entry moves unchanged to extra["optical_images"].

Revision ID: d2e3f4a5b6c7
Revises: b0c1d2e3f4a5
"""

import json
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d2e3f4a5b6c7"
down_revision: str | Sequence[str] | None = "b0c1d2e3f4a5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def loaded(value) -> dict:
    return value if isinstance(value, dict) else json.loads(value or "{}")


def save_sections(bind, updates: list[dict]) -> None:
    if updates:
        bind.execute(
            sa.text(
                "UPDATE sections SET optical_image = CAST(:image AS jsonb), extra = CAST(:extra AS jsonb) "
                "WHERE id = :id"
            ),
            updates,
        )


def upgrade() -> None:
    op.add_column("blocks", sa.Column("default_storage", postgresql.JSONB(), nullable=True))
    op.add_column("datasets", sa.Column("default_storage", postgresql.JSONB(), nullable=True))
    op.add_column("tiles", sa.Column("image", postgresql.JSONB(), nullable=True))
    op.alter_column("tiles", "image_path", existing_type=sa.String(), nullable=True)

    bind = op.get_bind()
    s3_url = re.compile(r"^https://([a-z0-9.-]+)\.s3\.([a-z0-9-]+)\.amazonaws\.com/(.+)$")
    updates = []
    rows = bind.execute(
        sa.text("SELECT id, optical_image, extra FROM sections WHERE jsonb_typeof(optical_image) = 'object'")
    ).all()
    for row in rows:
        images = loaded(row.optical_image)
        thumbnail = images.get("thumbnail")
        path = thumbnail.get("image_path") if isinstance(thumbnail, dict) else None
        match = s3_url.match(path) if isinstance(path, str) and not thumbnail.get("metadata") else None
        image = None
        if match:
            bucket, region, key = match.groups()
            image = {"protocol": "s3", "server": f"https://s3.{region}.amazonaws.com", "bucket": bucket, "key": key}
            del images["thumbnail"]
        extra = loaded(row.extra)
        if images:
            extra["optical_images"] = images
        updates.append({"id": row.id, "image": json.dumps(image) if image else None, "extra": json.dumps(extra)})
    save_sections(bind, updates)


def downgrade() -> None:
    bind = op.get_bind()
    aws_server = re.compile(r"^https://s3\.([a-z0-9-]+)\.amazonaws\.com$")
    updates = []
    rows = bind.execute(
        sa.text(
            "SELECT id, optical_image, extra FROM sections "
            "WHERE jsonb_typeof(optical_image) = 'object' OR extra ? 'optical_images'"
        )
    ).all()
    for row in rows:
        extra = loaded(row.extra)
        images = extra.pop("optical_images", {})
        if row.optical_image is not None:
            file = loaded(row.optical_image)
            if match := aws_server.match(file["server"] or ""):
                path = f"https://{file['bucket']}.s3.{match.group(1)}.amazonaws.com/{file['key']}"
            else:
                path = f"{file['server']}/{file['bucket']}/{file['key']}"
            images["thumbnail"] = {"image_path": path, "metadata": {}}
        updates.append({"id": row.id, "image": json.dumps(images) if images else None, "extra": json.dumps(extra)})
    save_sections(bind, updates)

    op.alter_column("tiles", "image_path", existing_type=sa.String(), nullable=False)
    op.drop_column("tiles", "image")
    op.drop_column("datasets", "default_storage")
    op.drop_column("blocks", "default_storage")
