"""
Rule-based query processing for financial questions.
"""

import re
from typing import Any

from app.services.ipo_service import get_upcoming_ipos
from app.services.macro_service import get_gdp, get_inflation, get_repo_rate
from app.services.mutual_fund_service import calculate_sip, get_mutual_fund_nav

# Stock name to symbol mapping (NSE)
STOCK_SYMBOLS = {
    "reliance": "RELIANCE.NS",
    "reli": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
    "hdfcbank": "HDFCBANK.NS",
    "sbi": "SBIN.NS",
    "icici": "ICICIBANK.NS",
    "icici bank": "ICICIBANK.NS",
    "bharti": "BHARTIARTL.NS",
    "airtel": "BHARTIARTL.NS",
    "itc": "ITC.NS",
    "kotak": "KOTAKBANK.NS",
    "kotak bank": "KOTAKBANK.NS",
    "lt": "LT.NS",
    "larsen": "LT.NS",
    "asian paint": "ASIANPAINT.NS",
    "asianpaint": "ASIANPAINT.NS",
    "maruti": "MARUTI.NS",
    "tata": "TATAMOTORS.NS",
    "tata motors": "TATAMOTORS.NS",
}
DEFAULT_STOCK = "RELIANCE.NS"
DEFAULT_SCHEME_CODE = "119551"


def _extract_stock_symbol(query: str) -> str:
    """Extract stock symbol from query using keyword matching."""
    q = query.lower()
    for name, symbol in sorted(STOCK_SYMBOLS.items(), key=lambda x: -len(x[0])):
        if name in q:
            return symbol
    # Check for symbol pattern like RELIANCE.NS or TCS.NS
    match = re.search(r"\b([A-Z]{2,10}\.NS)\b", query, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return DEFAULT_STOCK


def _extract_scheme_code(query: str) -> str:
    """Extract mutual fund scheme code from query."""
    match = re.search(r"\b(\d{5,6})\b", query)
    return match.group(1) if match else DEFAULT_SCHEME_CODE


def _extract_sip_params(query: str) -> tuple[float, int, float]:
    """Extract SIP params: monthly_investment, years, annual_return."""
    numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", query)
    nums = [float(n) for n in numbers]
    monthly = 5000.0
    years = 10
    annual = 12.0
    if len(nums) >= 1:
        monthly = nums[0]
    if len(nums) >= 2:
        years = int(nums[1])
    if len(nums) >= 3:
        annual = nums[2]
    # Check for percentage
    pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
    if pct_match:
        annual = float(pct_match.group(1))
    return (monthly, years, annual)


def process_query(query: str) -> dict[str, Any]:
    """
    Process natural language financial query using rule-based intent detection.

    Returns:
        Dict with query, result, source on success; or message on no match.
    """
    if not query or not str(query).strip():
        return {"message": "Sorry, I could not understand the query"}

    q = str(query).strip().lower()

    # SIP: "sip" keyword
    if "sip" in q:
        monthly, years, annual = _extract_sip_params(query)
        result = calculate_sip(monthly, years, annual)
        return {"query": query, "result": result, "source": "sip"}

    # RSI: "rsi" keyword
    if "rsi" in q:
        from app.services.stock_service import calculate_rsi

        symbol = _extract_stock_symbol(query)
        result = calculate_rsi(symbol)
        if result is None:
            return {"query": query, "result": {"error": f"No RSI data for {symbol}"}, "source": "rsi"}
        return {"query": query, "result": result, "source": "rsi"}

    # MACD: "macd" keyword
    if "macd" in q:
        from app.services.stock_service import calculate_macd

        symbol = _extract_stock_symbol(query)
        result = calculate_macd(symbol)
        if result is None:
            return {"query": query, "result": {"error": f"No MACD data for {symbol}"}, "source": "macd"}
        return {"query": query, "result": result, "source": "macd"}

    # GAINERS/LOSERS: "gainer" or "loser" keyword
    if "gainer" in q or "loser" in q:
        from app.services.stock_service import get_top_gainers_losers

        result = get_top_gainers_losers(count=10)
        if result is None:
            return {"query": query, "result": {"error": "Unable to fetch gainers/losers data"}, "source": "gainers_losers"}
        return {"query": query, "result": result, "source": "gainers_losers"}

    # MOVING AVERAGES: "moving average" or "sma" or "ma" keyword (exclude macd, macro)
    if "moving average" in q or "sma" in q or ("ma" in q and "macd" not in q and "macro" not in q):
        from app.services.stock_service import calculate_moving_averages

        symbol = _extract_stock_symbol(query)
        result = calculate_moving_averages(symbol)
        if result is None:
            return {"query": query, "result": {"error": f"No moving averages data for {symbol}"}, "source": "moving_averages"}
        return {"query": query, "result": result, "source": "moving_averages"}

    # BOLLINGER BANDS: "bollinger" or "bb" keyword
    if "bollinger" in q or "bb" in q:
        from app.services.stock_service import calculate_bollinger_bands

        symbol = _extract_stock_symbol(query)
        result = calculate_bollinger_bands(symbol)
        if result is None:
            return {"query": query, "result": {"error": f"No Bollinger Bands data for {symbol}"}, "source": "bollinger"}
        return {"query": query, "result": result, "source": "bollinger"}

    # MUTUAL FUND SEARCH: "search"/"find" + "fund" or "mutual fund" + name
    if (
        ("search" in q and "fund" in q)
        or ("find" in q and "fund" in q)
        or ("mutual fund" in q and not re.search(r"\b(\d{5,6})\b", q))
    ):
        from app.services.mutual_fund_service import search_mutual_funds

        search_query = "large cap"

        # Prefer term after "search" or "find"
        for keyword in ("search", "find"):
            idx = q.find(keyword)
            if idx != -1:
                raw = query[idx + len(keyword) :].strip(" :,-")
                if raw:
                    search_query = raw
                    break

        # If still default and "mutual fund" present, take text after it
        if search_query == "large cap" and "mutual fund" in q:
            idx = q.find("mutual fund")
            raw = query[idx + len("mutual fund") :].strip(" :,-")
            if raw:
                search_query = raw

        result = search_mutual_funds(search_query)
        if result is None:
            return {
                "query": query,
                "result": {"error": "Unable to search mutual funds"},
                "source": "mutual_fund_search",
            }
        if not result:
            return {
                "query": query,
                "result": {"funds": [], "message": f"No mutual funds found for '{search_query}'."},
                "source": "mutual_fund_search",
            }
        return {
            "query": query,
            "result": {"funds": result, "query": search_query},
            "source": "mutual_fund_search",
        }

    # MUTUAL FUND: "mutual fund" or "nav"
    if "mutual fund" in q or ("nav" in q and "mutual" not in q):
        scheme_code = _extract_scheme_code(query)
        result = get_mutual_fund_nav(scheme_code)
        if result is None:
            return {"query": query, "result": {"error": f"No NAV data for scheme {scheme_code}"}, "source": "mutual_fund"}
        return {"query": query, "result": result, "source": "mutual_fund"}

    # IPO GMP: "gmp" or "grey market" keyword
    if "gmp" in q or "grey market" in q:
        from app.services.ipo_service import get_gmp

        ipo_name = None

        # Prefer text after "gmp of"
        lower_q = q
        if "gmp of" in lower_q:
            idx = lower_q.find("gmp of")
            raw = query[idx + len("gmp of") :].strip(" :,-?.")
            ipo_name = raw or None
        elif "grey market" in lower_q:
            idx = lower_q.find("grey market")
            raw = query[idx + len("grey market") :].strip(" :,-?.")
            ipo_name = raw or None

        result = get_gmp(ipo_name)
        if result is None:
            return {
                "query": query,
                "result": {"error": "Unable to fetch GMP data"},
                "source": "gmp",
            }
        return {"query": query, "result": result, "source": "gmp"}

    # IPO PERFORMANCE: "ipo performance", "listing gain", or "ipo return"
    if "ipo performance" in q or "listing gain" in q or "ipo return" in q:
        from app.services.ipo_service import get_ipo_performance

        numbers = re.findall(r"\b(\d+)\b", query)
        limit = int(numbers[0]) if numbers else 10
        if limit < 1:
            limit = 10

        result = get_ipo_performance(limit=limit)
        if result is None:
            return {
                "query": query,
                "result": {"error": "Unable to fetch IPO performance data"},
                "source": "ipo_performance",
            }
        return {"query": query, "result": result, "source": "ipo_performance"}

    # SME STOCK ANALYSIS: "sme" + "stock" or "sme" + "analysis"
    if "sme" in q and ("stock" in q or "analysis" in q):
        from app.services.ipo_service import get_sme_stock_analysis

        symbol_match = re.search(r"\b([A-Z]{1,10}\.(?:NS|BO))\b", query, re.IGNORECASE)
        if symbol_match:
            symbol = symbol_match.group(1).upper()
        else:
            symbol = "DELHIVERY.NS"

        result = get_sme_stock_analysis(symbol)
        if result is None:
            return {
                "query": query,
                "result": {"error": f"No SME stock data for {symbol}"},
                "source": "sme_stock",
            }
        return {"query": query, "result": result, "source": "sme_stock"}

    # SECTOR PERFORMANCE: "sector" + sector name
    if "sector" in q:
        from app.services.sector_service import get_all_sectors_summary, get_sector_performance, SECTOR_STOCKS

        # Specific sector query
        for sector_key in SECTOR_STOCKS.keys():
            if sector_key in q:
                result = get_sector_performance(sector_key)
                return {"query": query, "result": result, "source": "sector_performance"}

        # All sectors / summary style query
        if (
            "all sector" in q
            or "sector summary" in q
            or "best sector" in q
            or "which sector" in q
        ):
            result = get_all_sectors_summary()
            return {"query": query, "result": result, "source": "sector_summary"}

    # IPO: "ipo" keyword (including "upcoming ipo")
    if "ipo" in q:
        result = get_upcoming_ipos()
        if result is None:
            return {"query": query, "result": {"error": "Unable to fetch IPO data"}, "source": "ipo"}
        return {"query": query, "result": result, "source": "ipo"}

    # PORTFOLIO: guidance to use the portfolio API
    if "portfolio" in q and ("analyze" in q or "rebalance" in q or "my portfolio" in q):
        message = (
            "To analyze your portfolio, please use POST /portfolio/analyze with your stock list. "
            "Format: [{'symbol': 'RELIANCE.NS', 'quantity': 10, 'buy_price': 2000}]."
        )
        return {"query": query, "message": message, "source": "portfolio_hint"}

    # CAPITAL GAINS / TAX: "capital gain" or tax-related keywords
    if (
        "capital gain" in q
        or "stcg" in q
        or "ltcg" in q
        or ("tax" in q and ("stock" in q or "invest" in q or "investment" in q))
    ):
        from app.services.mutual_fund_service import calculate_capital_gains

        numbers = re.findall(r"\b(\d+(?:\.\d+)?)\b", query)
        buy_price = float(numbers[0]) if len(numbers) >= 1 else 0.0
        sell_price = float(numbers[1]) if len(numbers) >= 2 else 0.0
        quantity = int(float(numbers[2])) if len(numbers) >= 3 else 1
        holding_days = int(float(numbers[3])) if len(numbers) >= 4 else 365

        asset_type = "equity"
        if "debt" in q:
            asset_type = "debt"

        result = calculate_capital_gains(
            buy_price=buy_price,
            sell_price=sell_price,
            quantity=quantity,
            holding_days=holding_days,
            asset_type=asset_type,
        )
        return {"query": query, "result": result, "source": "capital_gains"}

    # MACRO: repo, inflation, gdp
    if "repo" in q:
        result = get_repo_rate()
        return {"query": query, "result": result, "source": "macro"}
    if "inflation" in q:
        result = get_inflation()
        if result is None:
            return {"query": query, "result": {"error": "Unable to fetch inflation data"}, "source": "macro"}
        return {"query": query, "result": result, "source": "macro"}
    if "gdp" in q:
        result = get_gdp()
        if result is None:
            return {"query": query, "result": {"error": "Unable to fetch GDP data"}, "source": "macro"}
        return {"query": query, "result": result, "source": "macro"}

    # STOCK: price, stock, share
    if any(w in q for w in ("price", "stock", "share", "quote")):
        from app.services.stock_service import get_stock_quote

        symbol = _extract_stock_symbol(query)
        result = get_stock_quote(symbol)
        if result is None:
            return {"query": query, "result": {"error": f"No data for {symbol}"}, "source": "stock_api"}
        return {"query": query, "result": result, "source": "stock_api"}

    return {"message": "Sorry, I could not understand the query"}
