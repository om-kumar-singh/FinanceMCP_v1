"""
Stock comparison API for the AI advisor.
"""

from fastapi import APIRouter, HTTPException, Query

from app.services.stock_service import get_stock_detail
from app.services.stock_search_service import resolve_symbol

compare_router = APIRouter(prefix="/compare", tags=["compare"])


def _resolve(symbol: str) -> str | None:
    s = (symbol or "").strip().upper()
    if not s:
        return None
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    return resolve_symbol(s) or (f"{s}.NS" if len(s) <= 10 else None)


@compare_router.get("")
def compare_stocks(
    symbol1: str = Query(..., alias="symbol1", description="First stock (e.g. HDFCBANK, RELIANCE)"),
    symbol2: str = Query(..., alias="symbol2", description="Second stock (e.g. ICICIBANK, TCS)"),
):
    """
    Compare two stocks: price, PE, dividend yield, and brief interpretation.

    Example: GET /compare?symbol1=HDFCBANK&symbol2=ICICIBANK
    """
    s1 = _resolve(symbol1)
    s2 = _resolve(symbol2)
    if not s1:
        raise HTTPException(status_code=400, detail=f"Could not resolve symbol: {symbol1}")
    if not s2:
        raise HTTPException(status_code=400, detail=f"Could not resolve symbol: {symbol2}")

    d1 = get_stock_detail(s1)
    d2 = get_stock_detail(s2)
    if d1 is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol1}")
    if d2 is None:
        raise HTTPException(status_code=404, detail=f"No data for {symbol2}")

    name1 = d1["symbol"].replace(".NS", "").replace(".BO", "")
    name2 = d2["symbol"].replace(".NS", "").replace(".BO", "")

    pe1 = d1.get("pe")
    pe2 = d2.get("pe")
    div1 = d1.get("dividendYield", 0)
    div2 = d2.get("dividendYield", 0)

    interpretation = []
    if pe1 is not None and pe2 is not None:
        if pe1 < pe2:
            interpretation.append(
                f"Lower PE of {name1} ({pe1}) may indicate relatively cheaper valuation compared to {name2} ({pe2})."
            )
        elif pe2 < pe1:
            interpretation.append(
                f"Lower PE of {name2} ({pe2}) may indicate relatively cheaper valuation compared to {name1} ({pe1})."
            )
        else:
            interpretation.append("Both stocks trade at similar P/E multiples.")
    if div1 > 0 or div2 > 0:
        if div1 > div2:
            interpretation.append(f"{name1} has higher dividend yield ({div1}%) than {name2} ({div2}%).")
        elif div2 > div1:
            interpretation.append(f"{name2} has higher dividend yield ({div2}%) than {name1} ({div1}%).")

    return {
        "symbol1": d1["symbol"],
        "symbol2": d2["symbol"],
        "name1": name1,
        "name2": name2,
        "price1": d1["price"],
        "price2": d2["price"],
        "pe1": pe1,
        "pe2": pe2,
        "dividendYield1": div1,
        "dividendYield2": div2,
        "marketCap1": d1.get("marketCap"),
        "marketCap2": d2.get("marketCap"),
        "sector1": d1.get("sector"),
        "sector2": d2.get("sector"),
        "interpretation": interpretation,
    }
