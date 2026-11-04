"""Store SQL NULL instead of the JSON value null in nullable JSONB columns.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e3f4a5b6c7d8"
down_revision: str | Sequence[str] | None = "d2e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def json_columns() -> dict[str, list[str]]:
    return {
        "layouts": ["fiducials", "apertures"],
        "specimens": ["functional_imaging_metadata"],
        "blocks": ["microCT_info", "default_storage"],
        "datasets": ["default_storage", "metadata_json"],
        "lens_corrections": ["shared_transform", "solver_params"],
        "sections": ["optical_image", "position", "section_metrics", "run_parameters"],
        "rois": ["roi_payload"],
        "acquisition_tasks": ["sub_region", "tags", "metadata"],
        "acquisitions": ["calibration_info", "storage_locations", "sub_region"],
        "tiles": ["image", "matcher", "supertile_raster_position"],
    }


def upgrade() -> None:
    for table, columns in json_columns().items():
        assignments = ", ".join(f'"{column}" = NULLIF("{column}", \'null\'::jsonb)' for column in columns)
        matches = " OR ".join(f"\"{column}\" = 'null'::jsonb" for column in columns)
        op.execute(sa.text(f"UPDATE {table} SET {assignments} WHERE {matches}"))


def downgrade() -> None:
    # JSON null and SQL NULL read the same through the API, so there is nothing to restore.
    pass
