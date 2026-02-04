from datetime import datetime
from typing import Any

from beanie import SortDirection
from fastapi import APIRouter, HTTPException, Query
from temdb.server.documents import AcquisitionDocument

lens_correction_api = APIRouter(tags=["Lens Corrections"])


@lens_correction_api.get(
    "/lens-corrections/current",
    response_model=AcquisitionDocument,
)
async def get_current_lens_correction(
    scope_id: str = Query(..., description="Microscope scope ID"),
    magnification: int = Query(..., description="Magnification setting"),
):
    """
    Get the current (most recent) lens correction for the given scope and magnification.
    """
    lc = await AcquisitionDocument.find_one(
        {
            "lens_correction": True,
            "hardware_settings.scope_id": scope_id,
            "acquisition_settings.magnification": magnification,
        },
        sort=[("start_time", SortDirection.DESCENDING)],
    )

    if not lc:
        raise HTTPException(
            status_code=404,
            detail=f"No lens correction found for scope_id={scope_id}, magnification={magnification}",
        )

    return lc


@lens_correction_api.get(
    "/lens-corrections/latest",
    response_model=AcquisitionDocument,
)
async def get_latest_lens_correction(
    scope_id: str = Query(..., description="Microscope scope ID"),
):
    """
    Get the most recent lens correction for a scope (any settings).
    """
    lc = await AcquisitionDocument.find_one(
        {
            "lens_correction": True,
            "hardware_settings.scope_id": scope_id,
        },
        sort=[("start_time", SortDirection.DESCENDING)],
    )

    if not lc:
        raise HTTPException(
            status_code=404,
            detail=f"No lens correction found for scope_id={scope_id}",
        )

    return lc


@lens_correction_api.get(
    "/lens-corrections",
    response_model=dict[str, Any],
)
async def list_lens_corrections(
    scope_id: str | None = Query(None, description="Filter by scope ID"),
    magnification: int | None = Query(None, description="Filter by magnification"),
    from_time: datetime | None = Query(None, description="Filter from this time"),
    to_time: datetime | None = Query(None, description="Filter to this time"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List lens correction acquisitions with optional filters.
    """
    query: dict[str, Any] = {"lens_correction": True}

    if scope_id:
        query["hardware_settings.scope_id"] = scope_id
    if magnification:
        query["acquisition_settings.magnification"] = magnification
    if from_time:
        query.setdefault("start_time", {})["$gte"] = from_time
    if to_time:
        query.setdefault("start_time", {})["$lte"] = to_time

    total = await AcquisitionDocument.find(query).count()

    lens_corrections = await AcquisitionDocument.find(
        query,
        sort=[("start_time", SortDirection.DESCENDING)],
        skip=offset,
        limit=limit,
    ).to_list()

    return {
        "lens_corrections": lens_corrections,
        "metadata": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@lens_correction_api.get(
    "/lens-corrections/orphans",
    response_model=dict[str, Any],
)
async def find_orphan_acquisitions(
    scope_id: str | None = Query(None, description="Filter by scope ID"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Find acquisitions that are not lens corrections but have no lens correction reference.
    """
    query: dict[str, Any] = {
        "lens_correction": {"$ne": True},
        "$or": [
            {"lens_correction_acquisition_id": None},
            {"lens_correction_acquisition_id": {"$exists": False}},
        ],
    }

    if scope_id:
        query["hardware_settings.scope_id"] = scope_id

    total = await AcquisitionDocument.find(query).count()

    acquisitions = await AcquisitionDocument.find(
        query,
        sort=[("start_time", SortDirection.DESCENDING)],
        skip=offset,
        limit=limit,
    ).to_list()

    return {
        "acquisitions": acquisitions,
        "metadata": {
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


@lens_correction_api.get(
    "/lens-corrections/{acquisition_id}/acquisitions",
    response_model=dict[str, Any],
)
async def get_acquisitions_by_lens_correction(
    acquisition_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """
    Get all acquisitions that used a specific lens correction.
    """
    lc = await AcquisitionDocument.find_one(
        {
            "acquisition_id": acquisition_id,
            "lens_correction": True,
        }
    )
    if not lc:
        raise HTTPException(
            status_code=404,
            detail=f"Lens correction acquisition not found: {acquisition_id}",
        )

    query = {"lens_correction_acquisition_id": acquisition_id}
    total = await AcquisitionDocument.find(query).count()

    acquisitions = await AcquisitionDocument.find(
        query,
        sort=[("start_time", SortDirection.DESCENDING)],
        skip=offset,
        limit=limit,
    ).to_list()

    return {
        "acquisitions": acquisitions,
        "metadata": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "lens_correction_acquisition_id": acquisition_id,
        },
    }
