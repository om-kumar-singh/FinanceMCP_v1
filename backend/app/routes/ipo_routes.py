"""
IPO tracking API routes.
"""

from fastapi import APIRouter, HTTPException

from app.services.ipo_service import (
    get_gmp,
    get_ipo_performance,
    get_sme_stock_analysis,
    get_upcoming_ipos,
)

ipo_router = APIRouter(tags=["ipo"])


@ipo_router.get("/ipos")
def upcoming_ipos():
    """
    Get list of upcoming IPOs (top 5).

    Example: GET /ipos
    """
    data = get_upcoming_ipos()
    if data is None:
        return {"error": "Unable to fetch IPO data"}
    return data


@ipo_router.get("/gmp")
def ipo_gmp(ipo_name: str | None = None):
    """
    Get Grey Market Premium (GMP) data for IPOs.

    Example: GET /gmp or GET /gmp?ipo_name=Some IPO
    """
    data = get_gmp(ipo_name)
    return data


@ipo_router.get("/ipo-performance")
def ipo_performance(limit: int = 10):
    """
    Get recent IPO listing performance.

    Example: GET /ipo-performance?limit=10
    """
    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="limit must be at least 1.",
        )

    data = get_ipo_performance(limit=limit)
    if data is None:
        return {"error": "Unable to fetch IPO performance data"}
    return data


@ipo_router.get("/sme/{symbol}")
def sme_stock(symbol: str):
    """
    Get SME stock analysis for the given symbol.

    Example: GET /sme/XYZSME.NS
    """
    data = get_sme_stock_analysis(symbol)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for SME symbol '{symbol}'. Check if the symbol is valid.",
        )
    return data
