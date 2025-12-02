import json
import re
from pathlib import Path
import os
import glob

import logging

from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Body

from temdb.models.v1.grids import Grid, GridUpdate, GridRecord

grid_api = APIRouter(
    tags=["Grids"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_dir_nodes(rootdir):
    entries = []
    root_path = Path(rootdir)

    for entry in root_path.iterdir():
        if not entry.name.startswith(".") and entry.is_dir():
            entries.append(entry)
            if len(entries) % 100 == 0:
                print(len(entries))
            if entry.name != "0":
                entries += get_dir_nodes(entry)

    return entries


def find_valid_folders(root_dir):
    """Returns a dict of valid directories between the start and end barcodes for the selected machine."""

    exclusions = ["DONOTUSE", "tile_qc", "Lowmag"]
    matches = {}

    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"Directory not found: {root_dir}")
        return

    for entry in get_dir_nodes(root_path):
        dirname = entry.name
        full_path = str(entry)  # Convert Path object to string
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
    add_count = 0
    try:
        for root_dir in records:
            matches = find_valid_folders(root_dir)
            for dir in matches:
                for name in glob.glob(os.path.join(matches[dir], "0", r"_metadata*.*")):
                    name = name.replace("\\", "/")  # Windows
                    try:
                        with open(name) as f:
                            s = f.read()
                            record = json.loads(s)
                            # Create the document from the raw record
                            document = Grid.from_raw_record(record)
                            # Save it to the database
                            await document.save_to_db()
                            add_count += 1
                    except Exception as e:
                        print(f"could not process: {name}, {str(e)}")

        return {"msg": f"Added {add_count} records."}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not parse metadata record: {str(e)}",
        ) from e



def transform_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "metadata": data[0]["metadata"] if "metadata" in data[0] else None,
        "data": (
            data[1]["data"] if len(data) > 1 and "data" in data[1] else []
        ),
        "quality_control": (
            data[2]["tile_qc"]
            if len(data) > 2 and "tile_qc" in data[2]
            else {}
        ),
        "alerts": (
            data[2]["alerts"] if len(data) > 2 and "alerts" in data[2] else []
        ),
        "thumbnail": (
            data[2]["thumbnail"]
            if len(data) > 2 and "thumbnail" in data[2]
            else None
        ),
    }

@grid_api.put("/grids/add")
async def add_grid(grid_record: List[Dict[str, Any]]):
    # try:
    formatted_grid_data = transform_data(grid_record)
    logger.info(f"Formatted grid data: {formatted_grid_data}")
    document = Grid.from_raw_record(formatted_grid_data)
    await document.save_to_db()
    return {"msg": "Record added successfully"}
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Could not parse metadata record: {str(e)}",
    #     ) from e


@grid_api.patch("/grids/patch/{specimen_id}/{id}")
async def patch(specimen_id: str, id: str, updated_fields: GridUpdate = Body(...)):
    try:
        existing_grid = await Grid.get(id)
        if not existing_grid:
            raise HTTPException(status_code=404, detail="Grid not found")

        update_data = updated_fields.model_dump(exclude_unset=True)

        if update_data:
            for field, value in update_data.items():
                setattr(existing_grid, field, value)

            await existing_grid.save()

        return existing_grid
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not update grid: {str(e)}",
        ) from e
