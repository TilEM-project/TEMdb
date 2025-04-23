import httpx
from datetime import datetime
from urllib.parse import urlencode

async def list_acquisitions(
    base_url: str = "http://localhost:8000",
    cursor: str = None,
    limit: int = 50,
    sort_by: str = "start_time",
    sort_order: int = -1,
    montage_set_name: str = None,
    magnification: int = None,
    status: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    fields: list[str] = None
) -> dict:
    """
    Fetch acquisitions using the API endpoint
    """
    if fields is None:
        fields = ["acquisition_id", "status", "start_time", "montage_set_name"]

    # Build query parameters
    params = {
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "fields": fields
    }
    
    if cursor:
        params["cursor"] = cursor
    if montage_set_name:
        params["montage_set_name"] = montage_set_name
    if magnification:
        params["magnification"] = magnification
    if status:
        params["status"] = status
    if start_date:
        params["start_date"] = start_date.isoformat()
    if end_date:
        params["end_date"] = end_date.isoformat()

    url = f"{base_url}/acquisitions"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json()

async def main():
    try:
        result = await list_acquisitions(
            base_url="http://localhost:8000",
            limit=10,
            sort_by="start_time",
            sort_order=-1,
            status="completed"
        )
        print(f"Total acquisitions: {result['metadata']['total_count']}")
        for acq in result['acquisitions']:
            print(f"Acquisition ID: {acq['acquisition_id']}")
            
    except httpx.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
