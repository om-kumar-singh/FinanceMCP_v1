"""
Portfolio analysis API routes.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.services.portfolio_service import analyze_portfolio, get_portfolio_summary

portfolio_router = APIRouter(tags=["portfolio"])


def _validate_stocks_payload(stocks: Any) -> List[Dict[str, Any]]:
    if not isinstance(stocks, list):
        raise HTTPException(
            status_code=422,
            detail="stocks must be a list of stock objects.",
        )
    if not (1 <= len(stocks) <= 50):
        raise HTTPException(
            status_code=422,
            detail="stocks list must contain between 1 and 50 items.",
        )

    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(stocks):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail=f"stocks[{idx}] must be an object with symbol, quantity, and buy_price.",
            )
        symbol = item.get("symbol")
        quantity = item.get("quantity")
        buy_price = item.get("buy_price")

        if not symbol or not isinstance(symbol, str):
            raise HTTPException(
                status_code=422,
                detail=f"stocks[{idx}].symbol must be a non-empty string.",
            )
        try:
            quantity_val = float(quantity)
            buy_price_val = float(buy_price)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=422,
                detail=f"stocks[{idx}].quantity and buy_price must be numeric.",
            )

        if quantity_val <= 0:
            raise HTTPException(
                status_code=422,
                detail=f"stocks[{idx}].quantity must be greater than 0.",
            )
        if buy_price_val <= 0:
            raise HTTPException(
                status_code=422,
                detail=f"stocks[{idx}].buy_price must be greater than 0.",
            )

        cleaned.append(
            {
                "symbol": symbol,
                "quantity": quantity_val,
                "buy_price": buy_price_val,
            }
        )

    return cleaned


@portfolio_router.post("/portfolio/analyze")
def portfolio_analyze(payload: Dict[str, Any]):
    """
    Analyze a full portfolio and return detailed analytics.

    Body:
    {
      "stocks": [
        {"symbol": "RELIANCE.NS", "quantity": 10, "buy_price": 2000}
      ]
    }
    """
    stocks = payload.get("stocks")
    cleaned = _validate_stocks_payload(stocks)
    result = analyze_portfolio(cleaned)
    if "error" in result:
        raise HTTPException(
            status_code=503,
            detail=result["error"],
        )
    return result


@portfolio_router.post("/portfolio/summary")
def portfolio_summary(payload: Dict[str, Any]):
    """
    Get a quick summary for a portfolio without sector analysis.
    """
    stocks = payload.get("stocks")
    cleaned = _validate_stocks_payload(stocks)
    result = get_portfolio_summary(cleaned)
    if "error" in result:
        raise HTTPException(
            status_code=503,
            detail=result["error"],
        )
    return result

