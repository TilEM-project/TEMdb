from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

from temdb.server.sqlmodels import Base


def _tile(col: int) -> dict:
    return {
        "raster_index": col,
        "stage_position": {"x": float(col), "y": 0.0},
        "raster_position": {"row": 0, "col": col},
    }


async def _sql_nulls(test_db_manager, table: str, columns: list[str]) -> dict[str, int]:
    counts = ", ".join(f"count(*) FILTER (WHERE {column} IS NULL) AS {column}" for column in columns)
    async with test_db_manager.async_session_factory() as session:
        row = (await session.execute(text(f"SELECT {counts}, count(*) AS total FROM {table}"))).one()
    return dict(row._mapping)


def test_nullable_json_columns_store_sql_null():
    plain = [
        f"{table.name}.{column.name}"
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, JSONB) and column.nullable and not column.type.none_as_null
    ]
    assert plain == []


async def test_tile_create_stores_sql_null(async_client: AsyncClient, test_db_manager, test_acquisition):
    url = f"/api/v2/acquisitions/{test_acquisition.acquisition_id}/tiles"
    assert (await async_client.post(url, json=_tile(0))).status_code == 201
    bulk = await async_client.post(f"{url}/bulk", json=[_tile(1), _tile(2)])
    assert bulk.status_code == 200, bulk.text

    counts = await _sql_nulls(test_db_manager, "tiles", ["matcher", "supertile_raster_position"])
    assert counts == {"matcher": 3, "supertile_raster_position": 3, "total": 3}


async def test_section_create_stores_sql_null(
    async_client: AsyncClient, test_db_manager, test_cutting_session, test_substrate
):
    response = await async_client.post(
        "/api/v2/sections",
        json={
            "cutting_session_id": test_cutting_session.cutting_session_id,
            "timestamp": "2026-09-04T16:00:00+00:00",
            "media_id": test_substrate.media_id,
            "aperture_index": 1,
        },
    )
    assert response.status_code == 201, response.text

    columns = ["optical_images", "position", "section_metrics", "run_parameters"]
    counts = await _sql_nulls(test_db_manager, "sections", columns)
    assert counts == {**dict.fromkeys(columns, 1), "total": 1}
