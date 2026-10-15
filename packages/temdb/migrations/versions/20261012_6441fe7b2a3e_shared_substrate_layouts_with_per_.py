"""shared substrate layouts with per-aperture status

Revision ID: 6441fe7b2a3e
Revises: 9b8c7d6e5f4a
Create Date: 2026-10-12 14:59:37.476543

Substrates with the same media type, aperture geometry and refpoint share one layout. Each aperture becomes a Shape,
refpoint becomes the layout's fiducials, and the most common metadata.name in the group becomes its name; a refpoint missing any of origin, end and ref gives no fiducials. The layout_id is the media
type, aperture count and a hash of the geometry. Aperture statuses move to substrates.aperture_status in index order.
Sections keep aperture_index and lose aperture_uid.

Data the new schema has no column for moves to substrates.extra["lasso"] under its original names: uid, status,
source_path, refpoint_world, metadata, refpoint (when it gave no fiducials), and the aperture uids and tracking_uids
in index order. The downgrade restores them from there.

The upgrade stops and lists any substrate or section it cannot convert; the downgrade stops for sections with a
position and for layouts no substrate uses.
"""

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "6441fe7b2a3e"
down_revision: str | Sequence[str] | None = "9b8c7d6e5f4a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

substrate_types = {"grid_disc", "wafer", "tape", "stick", "grid", "washer", "unknown"}
aperture_statuses = {"available", "used", "damaged"}
refpoint_names = ("origin", "end", "ref")


def media_type_of(value: str) -> str:
    name = value.strip().lower().replace(" ", "_")
    return "grid_disc" if name == "griddisc" else name


def point(value) -> list[float] | None:
    """[x, y] from a 2- or 3-element point whose z is 0, or None."""
    if not isinstance(value, list) or len(value) not in (2, 3) or (len(value) == 3 and value[2] != 0):
        return None
    return [value[0], value[1]]


def shape_of(aperture: dict) -> dict | None:
    """The layout Shape for a stored aperture, or None when it has no equivalent."""
    centroid = point(aperture.get("centroid"))
    name = str(aperture.get("shape_type") or "").lower()
    params = aperture.get("shape_params") or {}
    if centroid is None:
        return None
    if name == "circle" and len(params.keys() & {"radius", "diameter"}) == 1:
        diameter = params.get("diameter", (params.get("radius") or 0) * 2)
        return {
            "shape_type": "circle",
            "shape_params": {"diameter": diameter},
            "centroid": centroid,
        }
    if name == "polygon" and isinstance(params.get("vertices"), list) and len(params["vertices"]) >= 3:
        return {
            "shape_type": "polygon",
            "shape_params": {"vertices": params["vertices"]},
            "centroid": centroid,
        }
    return None


def complete(refpoint):
    """The refpoint, or None when it is missing any point; an incomplete refpoint cannot place a layout."""
    if isinstance(refpoint, dict) and any(refpoint.get(name) is None for name in refpoint_names):
        return None
    return refpoint


def fiducials_of(refpoint: dict | None) -> list[dict]:
    refpoint = complete(refpoint)
    return [
        {
            "name": name,
            "shape_type": "circle",
            "shape_params": {"diameter": 0},
            "centroid": point(refpoint[name]),
            "through_shape": False,
        }
        for name in refpoint_names
        if refpoint and name in refpoint
    ]


def layout_name(members) -> str | None:
    names = Counter(name for _, name, _ in members if name)
    return min(names, key=lambda name: (-names[name], name)) if names else None


def layout_id(key: str) -> str:
    layout = json.loads(key)
    return f"{layout['media_type']}-{len(layout['apertures'])}-{hashlib.sha1(key.encode()).hexdigest()[:8]}"


def lasso_of(row, ordered) -> dict:
    """The substrate's fields that have no column in the new schema."""
    lasso = {
        "uid": row.uid,
        "status": row.status,
        "source_path": row.source_path,
        "refpoint_world": row.refpoint_world,
        "metadata": row.metadata,
        "refpoint": row.refpoint if complete(row.refpoint) is None else None,
        "aperture_uids": [aperture.get("uid") for aperture in ordered],
        "tracking_uids": [aperture.get("tracking_uid") for aperture in ordered],
    }
    return {key: value for key, value in lasso.items() if value is not None}


def substrate_problems(media_id, media_type, refpoint, apertures) -> list[str]:
    problems = []
    if media_type_of(media_type) not in substrate_types:
        problems.append(f"media_type {media_type!r} is not one of {sorted(substrate_types)}")
    refpoint = complete(refpoint)
    if refpoint is not None and (
        not isinstance(refpoint, dict)
        or not refpoint.keys() <= set(refpoint_names)
        or any(point(value) is None for value in refpoint.values())
    ):
        problems.append(f"refpoint {refpoint!r} is not origin/end/ref points with z 0")
    apertures = apertures or []
    if sorted(aperture.get("index", -1) for aperture in apertures) != list(range(len(apertures))):
        problems.append("aperture indexes are not 0..n-1")
    for aperture in apertures:
        if shape_of(aperture) is None:
            problems.append(
                f"aperture {aperture.get('index')}: shape {aperture.get('shape_type')!r} has no layout Shape"
            )
        if aperture.get("status") not in aperture_statuses:
            problems.append(f"aperture {aperture.get('index')}: status {aperture.get('status')!r}")
    return [f"substrate {media_id}: {problem}" for problem in problems]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    substrates = bind.execute(
        sa.text(
            "SELECT media_id, media_type, refpoint, metadata, apertures, uid, status, source_path, refpoint_world,"
            " extra FROM substrates ORDER BY media_id"
        )
    ).all()
    problems = [
        problem
        for row in substrates
        for problem in substrate_problems(row.media_id, row.media_type, row.refpoint, row.apertures)
    ] + [f"substrate {row.media_id}: extra already has a 'lasso' key" for row in substrates if "lasso" in row.extra]
    uids = {
        (row.media_id, aperture.get("index")): aperture.get("uid")
        for row in substrates
        for aperture in row.apertures or []
    }
    for section_id, media_id, uid, index in bind.execute(
        sa.text("SELECT section_id, media_id, aperture_uid, aperture_index FROM sections ORDER BY section_id")
    ).all():
        if index is None and uid is not None:
            problems.append(f"section {section_id}: aperture_uid {uid!r} with no aperture_index")
        elif index is not None and (media_id, index) not in uids:
            problems.append(f"section {section_id}: aperture_index {index} is not on substrate {media_id}")
        elif uid is not None and uids[media_id, index] != uid:
            problems.append(f"section {section_id}: aperture_uid {uid!r} is not aperture {index}'s")
    if problems:
        raise RuntimeError("Cannot convert:\n" + "\n".join(problems))

    groups = defaultdict(list)
    lasso = {}
    for row in substrates:
        ordered = sorted(row.apertures or [], key=lambda aperture: aperture["index"])
        layout = {
            "media_type": media_type_of(row.media_type),
            "apertures": [shape_of(aperture) for aperture in ordered],
            "fiducials": fiducials_of(row.refpoint),
        }
        key = json.dumps(layout, sort_keys=True)
        groups[key].append(
            (
                row.media_id,
                (row.metadata or {}).get("name"),
                [aperture["status"] for aperture in ordered],
            )
        )
        lasso[row.media_id] = lasso_of(row, ordered)

    op.create_table(
        "layouts",
        sa.Column("layout_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("fiducials", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("apertures", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("media_type", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "extra",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.PrimaryKeyConstraint("layout_id", name=op.f("pk_layouts")),
    )
    op.create_index("ix_layouts_media_type_name", "layouts", ["media_type", "name"], unique=False)
    op.add_column("substrates", sa.Column("substrate_layout_id", sa.String(), nullable=True))
    op.add_column(
        "substrates",
        sa.Column("aperture_status", postgresql.ARRAY(sa.String()), nullable=True),
    )

    insert_layout = sa.text(
        "INSERT INTO layouts (layout_id, name, fiducials, apertures, media_type)"
        " VALUES (:layout_id, :name, CAST(:fiducials AS jsonb), CAST(:apertures AS jsonb), :media_type)"
    )
    place_substrate = sa.text(
        "UPDATE substrates SET substrate_layout_id = :layout_id, aperture_status = :statuses,"
        " extra = extra || jsonb_build_object('lasso', CAST(:lasso AS jsonb)) WHERE media_id = :media_id"
    ).bindparams(sa.bindparam("statuses", type_=postgresql.ARRAY(sa.String())))
    for key, members in groups.items():
        layout = json.loads(key)
        bind.execute(
            insert_layout,
            {
                "layout_id": layout_id(key),
                "name": layout_name(members),
                "fiducials": json.dumps(layout["fiducials"]),
                "apertures": json.dumps(layout["apertures"]),
                "media_type": layout["media_type"],
            },
        )
        for media_id, _, statuses in members:
            bind.execute(
                place_substrate,
                {
                    "layout_id": layout_id(key),
                    "statuses": statuses,
                    "lasso": json.dumps(lasso[media_id]),
                    "media_id": media_id,
                },
            )

    op.alter_column("layouts", "extra", server_default=None)
    op.alter_column("substrates", "substrate_layout_id", nullable=False)
    op.alter_column("substrates", "aperture_status", nullable=False)
    op.create_check_constraint(
        op.f("ck_substrates_aperture_status_vocab"),
        "substrates",
        "aperture_status <@ ARRAY['available', 'used', 'damaged']::varchar[]",
    )
    op.drop_index(op.f("ix_substrates_media_type_status"), table_name="substrates")
    op.create_index(
        "ix_substrates_substrate_layout_id",
        "substrates",
        ["substrate_layout_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_substrates_substrate_layout_id_layouts"),
        "substrates",
        "layouts",
        ["substrate_layout_id"],
        ["layout_id"],
    )
    for column in (
        "source_path",
        "apertures",
        "media_type",
        "metadata",
        "refpoint",
        "status",
        "refpoint_world",
        "uid",
    ):
        op.drop_column("substrates", column)

    op.add_column(
        "sections",
        sa.Column("position", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_check_constraint(
        op.f("ck_sections_aperture_index_nonnegative"),
        "sections",
        "aperture_index >= 0",
    )
    op.create_index(
        "ix_sections_media_aperture",
        "sections",
        ["media_id", "aperture_index"],
        unique=False,
    )
    op.drop_column("sections", "aperture_uid")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    problems = [
        f"section {section_id}: has a position"
        for (section_id,) in bind.execute(
            sa.text("SELECT section_id FROM sections WHERE position IS NOT NULL ORDER BY 1")
        ).all()
    ] + [
        f"layout {layout_id}: no substrate uses it"
        for (layout_id,) in bind.execute(
            sa.text(
                "SELECT layout_id FROM layouts l WHERE NOT EXISTS"
                " (SELECT 1 FROM substrates s WHERE s.substrate_layout_id = l.layout_id) ORDER BY 1"
            )
        ).all()
    ]
    if problems:
        raise RuntimeError("Cannot downgrade:\n" + "\n".join(problems))

    op.add_column(
        "sections",
        sa.Column("aperture_uid", sa.VARCHAR(), autoincrement=False, nullable=True),
    )
    op.drop_index("ix_sections_media_aperture", table_name="sections")
    op.drop_constraint(op.f("ck_sections_aperture_index_nonnegative"), "sections", type_="check")
    op.drop_column("sections", "position")

    for column, column_type in (
        ("uid", sa.VARCHAR()),
        ("refpoint_world", postgresql.JSONB(astext_type=sa.Text())),
        ("status", sa.VARCHAR()),
        ("refpoint", postgresql.JSONB(astext_type=sa.Text())),
        ("metadata", postgresql.JSONB(astext_type=sa.Text())),
        ("media_type", sa.VARCHAR()),
        ("apertures", postgresql.JSONB(astext_type=sa.Text())),
        ("source_path", sa.VARCHAR()),
    ):
        op.add_column(
            "substrates",
            sa.Column(column, column_type, autoincrement=False, nullable=True),
        )

    restore = sa.text(
        "UPDATE substrates SET media_type = :media_type, refpoint = CAST(:refpoint AS jsonb),"
        " metadata = CAST(:metadata AS jsonb), apertures = CAST(:apertures AS jsonb), uid = :uid, status = :status,"
        " source_path = :source_path, refpoint_world = CAST(:refpoint_world AS jsonb), extra = extra - 'lasso'"
        " WHERE media_id = :media_id"
    )
    for media_id, statuses, name, fiducials, shapes, media_type, extra in bind.execute(
        sa.text(
            "SELECT s.media_id, s.aperture_status, l.name, l.fiducials, l.apertures, l.media_type, s.extra"
            " FROM substrates s JOIN layouts l ON l.layout_id = s.substrate_layout_id"
        )
    ).all():
        lasso = extra.get("lasso", {})
        apertures = []
        for index, (shape, status) in enumerate(zip(shapes or [], statuses, strict=True)):
            shape_type = shape["shape_type"].capitalize()
            params = dict(shape["shape_params"])
            aperture = {
                "index": index,
                "shape": f"{shape_type}:{json.dumps(params)}",
                "status": status,
                "centroid": [*shape["centroid"], 0.0],
                "shape_type": shape_type,
                "shape_params": params,
            }
            for name_in_lasso, key in (("aperture_uids", "uid"), ("tracking_uids", "tracking_uid")):
                if len(lasso.get(name_in_lasso, [])) == len(statuses):
                    aperture[key] = lasso[name_in_lasso][index]
            apertures.append(aperture)
        refpoint = lasso.get("refpoint") or {
            fiducial["name"]: [*fiducial["centroid"], 0.0] for fiducial in fiducials or [] if fiducial.get("name")
        }
        metadata = lasso.get("metadata") or ({"name": name} if name else None)
        bind.execute(
            restore,
            {
                "media_id": media_id,
                "media_type": "GridDisc" if media_type == "grid_disc" else media_type,
                "refpoint": json.dumps(refpoint) if refpoint else None,
                "metadata": json.dumps(metadata) if metadata else None,
                "apertures": json.dumps(apertures),
                "uid": lasso.get("uid"),
                "status": lasso.get("status"),
                "source_path": lasso.get("source_path"),
                "refpoint_world": json.dumps(lasso["refpoint_world"]) if "refpoint_world" in lasso else None,
            },
        )
    bind.execute(
        sa.text(
            "UPDATE sections s SET aperture_uid = a ->> 'uid' FROM substrates sub, jsonb_array_elements(sub.apertures) a"
            " WHERE sub.media_id = s.media_id AND (a ->> 'index')::int = s.aperture_index"
        )
    )

    op.alter_column("substrates", "media_type", nullable=False)
    op.drop_constraint(
        op.f("fk_substrates_substrate_layout_id_layouts"),
        "substrates",
        type_="foreignkey",
    )
    op.drop_index("ix_substrates_substrate_layout_id", table_name="substrates")
    op.create_index(
        op.f("ix_substrates_media_type_status"),
        "substrates",
        ["media_type", "status"],
        unique=False,
    )
    op.drop_constraint(op.f("ck_substrates_aperture_status_vocab"), "substrates", type_="check")
    op.drop_column("substrates", "aperture_status")
    op.drop_column("substrates", "substrate_layout_id")
    op.drop_index("ix_layouts_media_type_name", table_name="layouts")
    op.drop_table("layouts")
