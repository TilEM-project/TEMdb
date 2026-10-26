"""Add structured image storage while retaining current non-S3 tile paths.

sections.optical_image becomes {name: FileObject}. S3 URLs are converted. Bare file names have no known location, so
they move unchanged to extra["optical_image_names"].

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
                "UPDATE sections SET optical_image = CAST(:images AS jsonb), extra = CAST(:extra AS jsonb) "
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
    rejected, updates = [], []
    rows = bind.execute(
        sa.text(
            "SELECT id, section_id, optical_image, extra FROM sections WHERE jsonb_typeof(optical_image) = 'object'"
        )
    ).all()
    for row in rows:
        files, stems = {}, {}
        for name, image in loaded(row.optical_image).items():
            path = image.get("image_path") if isinstance(image, dict) else None
            if not re.fullmatch(r"[a-z0-9_]+", name) or not isinstance(path, str) or image.get("metadata"):
                rejected.append((row.section_id, name))
            elif match := s3_url.match(path):
                bucket, region, key = match.groups()
                files[name] = {
                    "protocol": "s3",
                    "server": f"https://s3.{region}.amazonaws.com",
                    "bucket": bucket,
                    "key": key,
                }
            else:
                stems[name] = image
        extra = loaded(row.extra)
        if stems:
            extra["optical_image_names"] = stems
        updates.append({"id": row.id, "images": json.dumps(files) if files else None, "extra": json.dumps(extra)})
    if rejected:
        raise RuntimeError(
            f"{len(rejected)} optical_image entries need a lowercase name, an image_path and no metadata: {rejected[:20]}"
        )
    save_sections(bind, updates)


def downgrade() -> None:
    bind = op.get_bind()
    aws_server = re.compile(r"^https://s3\.([a-z0-9-]+)\.amazonaws\.com$")
    updates = []
    rows = bind.execute(
        sa.text(
            "SELECT id, optical_image, extra FROM sections "
            "WHERE jsonb_typeof(optical_image) = 'object' OR extra ? 'optical_image_names'"
        )
    ).all()
    for row in rows:
        images = {}
        for name, file in loaded(row.optical_image).items():
            if match := aws_server.match(file["server"] or ""):
                path = f"https://{file['bucket']}.s3.{match.group(1)}.amazonaws.com/{file['key']}"
            else:
                path = f"{file['server']}/{file['bucket']}/{file['key']}"
            images[name] = {"image_path": path, "metadata": {}}
        extra = loaded(row.extra)
        images.update(extra.pop("optical_image_names", {}))
        updates.append({"id": row.id, "images": json.dumps(images) if images else None, "extra": json.dumps(extra)})
    save_sections(bind, updates)

    op.alter_column("tiles", "image_path", existing_type=sa.String(), nullable=False)
    op.drop_column("tiles", "image")
    op.drop_column("datasets", "default_storage")
    op.drop_column("blocks", "default_storage")
