import glob
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException
from temdb.server.documents import GridDocument, GridUpdate

grid_api = APIRouter(
    tags=["Grids"],
)

logger = logging.getLogger(__name__)


def get_dir_nodes(rootdir: str) -> list[Path]:
    """Recursively get all directory nodes."""
    entries = []
    root_path = Path(rootdir)

    for entry in root_path.iterdir():
        if not entry.name.startswith(".") and entry.is_dir():
            entries.append(entry)
            if len(entries) % 100 == 0:
                logger.debug(f"Found {len(entries)} directories")
            if entry.name != "0":
                entries += get_dir_nodes(str(entry))

    return entries


def find_valid_folders(root_dir: str) -> dict[str, str]:
    """Returns a dict of valid directories for grid metadata."""
    exclusions = ["DONOTUSE", "tile_qc", "Lowmag"]
    matches = {}

    root_path = Path(root_dir)
    if not root_path.exists():
        logger.warning(f"Directory not found: {root_dir}")
        return {}

    for entry in get_dir_nodes(root_dir):
        dirname = entry.name
        full_path = str(entry)
        bad = any(exclude in full_path for exclude in exclusions)

        if bad:
            continue

        if re.match("^[0-9]{6}$", dirname):  # 000000 to 999999
            matches[dirname] = full_path
        elif re.match("[0-9]{14}_reference$", dirname):
            # Also handle reference image directories
            matches[dirname] = full_path

    return matches


@grid_api.put("/grids/add_directory")
async def add_directory(records: list[str]):
    """Add grids from directories containing metadata files."""
    add_count = 0
    try:
        for root_dir in records:
            matches = find_valid_folders(root_dir)
            for dir_name in matches:
                for name in glob.glob(os.path.join(matches[dir_name], "0", r"_metadata*.*")):
                    name = name.replace("\\", "/")  # Windows compatibility
                    try:
                        with open(name) as f:
                            s = f.read()
                            record = json.loads(s)
                            document = GridDocument.from_raw_record(record)
                            await document.save_to_db()
                            add_count += 1
                    except Exception as e:
                        logger.warning(f"Could not process: {name}, {e}")

        return {"msg": f"Added {add_count} records."}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse metadata record: {e}",
        ) from e


def transform_data(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Transform raw grid data to common format."""
    return {
        "metadata": data[0]["metadata"] if "metadata" in data[0] else None,
        "data": data[1]["data"] if len(data) > 1 and "data" in data[1] else [],
        "quality_control": (data[2]["tile_qc"] if len(data) > 2 and "tile_qc" in data[2] else {}),
        "alerts": data[2]["alerts"] if len(data) > 2 and "alerts" in data[2] else [],
        "thumbnail": (data[2]["thumbnail"] if len(data) > 2 and "thumbnail" in data[2] else None),
    }


@grid_api.put("/grids/add")
async def add_grid(grid_record: list[dict[str, Any]]):
    """Add a new grid record."""
    formatted_grid_data = transform_data(grid_record)
    logger.info(f"Formatted grid data: {formatted_grid_data}")
    document = GridDocument.from_raw_record(formatted_grid_data)
    await document.save_to_db()
    return {"msg": "Record added successfully"}


@grid_api.patch("/grids/patch/{specimen_id}/{grid_id}")
async def patch_grid(specimen_id: str, grid_id: str, updated_fields: GridUpdate = Body(...)):
    """Update an existing grid record."""
    try:
        existing_grid = await GridDocument.get(grid_id)
        if not existing_grid:
            raise HTTPException(status_code=404, detail="Grid not found")

        update_data = updated_fields.model_dump(exclude_unset=True)

        if update_data:
            for field, value in update_data.items():
                setattr(existing_grid, field, value)

            await existing_grid.save()

        return existing_grid
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not update grid: {e}",
        ) from e


@grid_api.get("/grids/{grid_id}", response_model=GridDocument)
async def get_grid(grid_id: str):
    """Get a specific grid by ID."""
    grid = await GridDocument.get(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"Grid '{grid_id}' not found")
    return grid


@grid_api.get("/grids", response_model=list[GridDocument])
async def list_grids(
    specimen_id: str | None = None,
    session_id: str | None = None,
    media_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
):
    """List grids with optional filters."""
    query_filter = {}
    if specimen_id:
        query_filter["metadata.specimen_id"] = specimen_id
    if session_id:
        query_filter["metadata.session_id"] = session_id
    if media_id:
        query_filter["metadata.media_id"] = media_id

    return await GridDocument.find(query_filter).skip(skip).limit(limit).to_list()


@grid_api.delete("/grids/{grid_id}", status_code=204)
async def delete_grid(grid_id: str):
    """Delete a grid by ID."""
    grid = await GridDocument.get(grid_id)
    if not grid:
        raise HTTPException(status_code=404, detail=f"Grid '{grid_id}' not found")
    await grid.delete()
    return None
