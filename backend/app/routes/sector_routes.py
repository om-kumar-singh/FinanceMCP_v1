"""
Sector performance API routes.
"""

from fastapi import APIRouter, HTTPException

from app.services.sector_service import (
    SECTOR_STOCKS,
    get_all_sectors_summary,
    get_sector_performance,
)

sector_router = APIRouter(tags=["sector"])


@sector_router.get("/sector/{sector_name}")
def sector_detail(sector_name: str):
    """
    Get detailed performance for a given sector.

    Example: GET /sector/banking
    """
    data = get_sector_performance(sector_name)
    # get_sector_performance returns error message for invalid sectors
    if isinstance(data, dict) and data.get("error"):
        return data
    return data


@sector_router.get("/sectors/summary")
def sectors_summary():
    """
    Get summary performance across all sectors.

    Example: GET /sectors/summary
    """
    data = get_all_sectors_summary()
    if not data:
        raise HTTPException(
            status_code=503,
            detail="Unable to fetch sector summary. Service temporarily unavailable.",
        )
    return data


@sector_router.get("/sectors/list")
def sectors_list():
    """
    Get list of available sectors.

    Example: GET /sectors/list
    """
    return {"sectors": sorted(SECTOR_STOCKS.keys())}

