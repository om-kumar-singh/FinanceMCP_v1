"""
Market news API routes.
"""

from fastapi import APIRouter, HTTPException

from app.services.news_service import get_market_news


news_router = APIRouter(prefix="/news", tags=["news"])


@news_router.get("/{symbol}")
def market_news(symbol: str):
    """
    Get latest market news for a given symbol.

    Examples:
      - GET /news/RELIANCE.NS
      - GET /news/NSE        (NIFTY 50 index news)
      - GET /news/BSE        (BSE Sensex index news)
    """
    items = get_market_news(symbol)
    if not items:
        raise HTTPException(
            status_code=404,
            detail=f"No news found for symbol '{symbol}'. Try another stock or index like NSE/BSE.",
        )
    return items

