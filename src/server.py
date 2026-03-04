"""
Standalone FastMCP server that exposes:
- Mutual fund tools (mfapi.in)
- IPO & SME tools (Chittorgarh, Investorgain)
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastmcp import FastMCP

# When invoked as `python -m src.server`, this module is part of the `src`
# package. Use relative imports so Python can locate the tools correctly.
from .tools.calculators import calculate_indian_tax
from .tools.ipo import get_ipo_gmp, get_ipo_subscription, get_upcoming_ipos
from .tools.macro import (
    get_forex_reserves,
    get_india_gdp_growth,
    get_india_inflation,
    get_rbi_rates,
)
from .tools.mutual_funds import (
    get_mutual_fund_nav,
    mutual_fund_search,
    sip_calculator,
)
from .utils.optimizer import optimize_payload


# ── Logging setup ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("server.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("bharat_finance_mcp")


def _safe_tool_call(tool_name: str, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Wrapper around underlying tool functions that:
    - Logs success/failure to server.log
    - Applies adaptive truncation to large payloads
    - Returns a structured error dict instead of raising on failure
    """
    try:
        result = func(*args, **kwargs)
        logger.info("Tool '%s' executed successfully", tool_name)
        return optimize_payload(result)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Tool '%s' failed with error", tool_name)
        return {
            "error": f"Tool '{tool_name}' failed. See server.log for details.",
            "detail": str(exc),
            "tool": tool_name,
        }


mcp = FastMCP(
    name="BharatFinanceMCP",
    description=(
        "A comprehensive hub for Indian financial data including stocks, "
        "mutual funds, IPOs, macroeconomic indicators, and tax calculators."
    ),
)


# ── Mutual Fund Tools ──────────────────────────────────────

@mcp.tool()
def get_mutual_fund_nav_tool(scheme_code: str):
    """
    Useful for answering questions about the latest Indian mutual fund NAV,
    recent daily change, and valuation for a specific scheme code from mfapi.in.
    """
    return _safe_tool_call("get_mutual_fund_nav", get_mutual_fund_nav, scheme_code)


@mcp.tool()
def mutual_fund_search_tool(query: str):
    """
    Useful for discovering Indian mutual fund schemes by name or keyword,
    so the AI can suggest relevant funds and fetch their NAVs later.
    """
    return _safe_tool_call("mutual_fund_search", mutual_fund_search, query)


@mcp.tool()
def sip_calculator_tool(
    monthly_investment: float,
    years: int,
    expected_return: float,
):
    """
    Useful for estimating the future value of a SIP in Indian mutual funds,
    given monthly contribution, investment horizon in years, and expected return.
    """
    return _safe_tool_call(
        "sip_calculator",
        sip_calculator,
        monthly_investment,
        years,
        expected_return,
    )


# ── IPO & SME Tools ────────────────────────────────────────

@mcp.tool()
def get_upcoming_ipos_tool():
    """
    Useful for answering questions about upcoming Indian Mainboard and SME IPOs,
    including company names, open/close dates, price bands, and basic status.
    """
    return _safe_tool_call("get_upcoming_ipos", get_upcoming_ipos)


@mcp.tool()
def get_ipo_gmp_tool(ipo_name: str):
    """
    Useful for estimating Grey Market Premium (GMP) for a specific Indian IPO,
    helping the AI discuss expected listing price and sentiment using fuzzy name matching.
    """
    return _safe_tool_call("get_ipo_gmp", get_ipo_gmp, ipo_name)


@mcp.tool()
def get_ipo_subscription_tool(ipo_name: str):
    """
    Useful for answering questions about live IPO subscription levels in India,
    including QIB, NII, and Retail bids for a named IPO using fuzzy matching.
    """
    return _safe_tool_call("get_ipo_subscription", get_ipo_subscription, ipo_name)


# ── Macroeconomic Tools ────────────────────────────────────

@mcp.tool()
def get_rbi_rates_tool():
    """
    Useful for questions about current RBI policy rates (repo, reverse repo,
    MSF, bank rate) and Cash Reserve Ratio (CRR) that drive Indian lending
    and deposit rates.
    """
    return _safe_tool_call("get_rbi_rates", get_rbi_rates)


@mcp.tool()
def get_india_inflation_tool():
    """
    Useful for answering questions about recent Indian CPI inflation and
    providing context on price levels, with a note about WPI data coverage.
    """
    return _safe_tool_call("get_india_inflation", get_india_inflation)


@mcp.tool()
def get_india_gdp_growth_tool():
    """
    Useful for explaining India’s most recent annual GDP growth rate and
    macro growth trends based on World Bank data.
    """
    return _safe_tool_call("get_india_gdp_growth", get_india_gdp_growth)


@mcp.tool()
def get_forex_reserves_tool():
    """
    Useful for discussing India’s latest foreign exchange reserves in USD,
    including “as of” dates for macro stability and currency-risk questions.
    """
    return _safe_tool_call("get_forex_reserves", get_forex_reserves)


# ── Taxation Tools ────────────────────────────────────────────


@mcp.tool()
def calculate_indian_tax_tool(
    asset_type: str,
    buy_price: float,
    sell_price: float,
    buy_date: str,
    sell_date: str,
):
    """
    Useful for estimating Indian capital-gains tax on a single transaction
    in equity, mutual funds, debt funds, or gold, including holding period,
    gain/loss, and tax liability formatted in INR (lakhs/crores).
    """
    return _safe_tool_call(
        "calculate_indian_tax",
        calculate_indian_tax,
        asset_type,
        buy_price,
        sell_price,
        buy_date,
        sell_date,
    )


if __name__ == "__main__":
    # Run MCP server on stdio (for MCP clients like Claude Desktop).
    mcp.run()

