"""Turn sections.optical_image into sections.optical_images, a set of named images.

The stored image is the dropoff thumbnail, so it becomes post_dropoff_image. extra["optical_images"]["autotome_qc_snapshot"]
becomes qc_image when it is an S3 URL. Other entries cannot be converted and move to extra["legacy_optical_images"],
because a record's extra cannot use the name of one of its fields. specimens.specimen_images held no data and is dropped.

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
"""

import json
import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5b6c7d8e9f0"
down_revision: str | Sequence[str] | None = "f4a5b6c7d8e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def loaded(value):
    return json.loads(value) if isinstance(value, str) else value


def save(bind, updates: list[dict]) -> None:
    if updates:
        bind.execute(
            sa.text(
                "UPDATE sections SET optical_images = CAST(:images AS jsonb), extra = CAST(:extra AS jsonb) WHERE id = :id"
            ),
            updates,
        )


def upgrade() -> None:
    op.drop_column("specimens", "specimen_images")
    op.alter_column("sections", "optical_image", new_column_name="optical_images")
    bind = op.get_bind()
    s3_url = re.compile(r"^https://([a-z0-9.-]+)\.s3\.([a-z0-9-]+)\.amazonaws\.com/(.+)$")
    rows = bind.execute(
        sa.text(
            "SELECT id, optical_images, extra FROM sections WHERE optical_images IS NOT NULL OR extra ? 'optical_images'"
        )
    ).all()
    updates = []
    for row in rows:
        images = {}
        if row.optical_images is not None:
            images["post_dropoff_image"] = loaded(row.optical_images)
        extra = loaded(row.extra) or {}
        legacy = extra.pop("optical_images", {})
        snapshot = legacy.get("autotome_qc_snapshot")
        path = snapshot.get("image_path") if isinstance(snapshot, dict) else None
        match = s3_url.match(path) if isinstance(path, str) and not snapshot.get("metadata") else None
        if match:
            bucket, region, key = match.groups()
            images["qc_image"] = {
                "protocol": "s3",
                "server": f"https://s3.{region}.amazonaws.com",
                "bucket": bucket,
                "key": key,
            }
            del legacy["autotome_qc_snapshot"]
        if legacy:
            extra["legacy_optical_images"] = legacy
        updates.append({"id": row.id, "images": json.dumps(images) if images else None, "extra": json.dumps(extra)})
    save(bind, updates)


def downgrade() -> None:
    op.add_column("specimens", sa.Column("specimen_images", postgresql.JSONB(), nullable=True))
    bind = op.get_bind()
    aws_server = re.compile(r"^https://s3\.([a-z0-9-]+)\.amazonaws\.com$")
    rows = bind.execute(
        sa.text(
            "SELECT id, optical_images, extra FROM sections "
            "WHERE optical_images IS NOT NULL OR extra ? 'legacy_optical_images'"
        )
    ).all()
    updates = []
    for row in rows:
        images = loaded(row.optical_images) or {}
        extra = loaded(row.extra) or {}
        legacy = extra.pop("legacy_optical_images", {})
        qc_image = images.get("qc_image")
        if qc_image and (match := aws_server.match(qc_image["server"] or "")):
            path = f"https://{qc_image['bucket']}.s3.{match.group(1)}.amazonaws.com/{qc_image['key']}"
            legacy["autotome_qc_snapshot"] = {"image_path": path, "metadata": {}}
        if legacy:
            extra["optical_images"] = legacy
        dropoff = images.get("post_dropoff_image")
        updates.append({"id": row.id, "images": json.dumps(dropoff) if dropoff else None, "extra": json.dumps(extra)})
    save(bind, updates)
    op.alter_column("sections", "optical_images", new_column_name="optical_image")
