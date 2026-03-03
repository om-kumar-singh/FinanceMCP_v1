from fastmcp import FastMCP
from dotenv import load_dotenv
import os
import sys

# Add backend to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

# Create MCP server instance (FastMCP only accepts name as first arg)
mcp = FastMCP("BharatFinanceMCP")


# ── STOCK TOOLS ──────────────────────────────────────────

@mcp.tool()
def get_stock_quote(symbol: str) -> dict:
    """
    Get real-time stock price and details for Indian stocks.

    Args:
        symbol: NSE symbol with .NS suffix or BSE with .BO suffix
                Examples: RELIANCE.NS, TCS.NS, HDFCBANK.NS, INFY.BO

    Returns:
        Current price, change, change_percent, volume,
        day_high, day_low

    Example: get_stock_quote("RELIANCE.NS")
    """
    from app.services.stock_service import get_stock_quote as _fn

    return _fn(symbol)


@mcp.tool()
def calculate_rsi(symbol: str, period: int = 14) -> dict:
    """
    Calculate RSI (Relative Strength Index) for a stock.
    RSI > 70 = Overbought (consider selling)
    RSI < 30 = Oversold (consider buying)
    RSI 30-70 = Neutral

    Args:
        symbol: NSE symbol e.g. RELIANCE.NS, TCS.NS
        period: Lookback period, default 14 days

    Returns:
        rsi value, period, signal (overbought/oversold/neutral)

    Example: calculate_rsi("TATAMOTORS.NS", 14)
    """
    from app.services.stock_service import calculate_rsi as _fn

    return _fn(symbol, period)


@mcp.tool()
def calculate_macd(symbol: str) -> dict:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    MACD > Signal Line = Bullish trend
    MACD < Signal Line = Bearish trend

    Args:
        symbol: NSE symbol e.g. RELIANCE.NS, HDFCBANK.NS

    Returns:
        macd, signal, histogram, trend (bullish/bearish)

    Example: calculate_macd("HDFCBANK.NS")
    """
    from app.services.stock_service import calculate_macd as _fn

    return _fn(symbol)


@mcp.tool()
def calculate_bollinger_bands(symbol: str) -> dict:
    """
    Calculate Bollinger Bands for a stock.
    Price > Upper Band = Overbought
    Price < Lower Band = Oversold

    Args:
        symbol: NSE symbol e.g. RELIANCE.NS

    Returns:
        upper_band, middle_band, lower_band,
        current_price, signal

    Example: calculate_bollinger_bands("INFY.NS")
    """
    from app.services.stock_service import calculate_bollinger_bands as _fn

    return _fn(symbol)


@mcp.tool()
def calculate_moving_averages(symbol: str) -> dict:
    """
    Calculate SMA20, SMA50, SMA200 moving averages for a stock.
    Price above SMA = Bullish, below = Bearish
    Golden Cross (SMA50 > SMA200) = Strong bullish signal
    Death Cross (SMA50 < SMA200) = Strong bearish signal

    Args:
        symbol: NSE symbol e.g. RELIANCE.NS

    Returns:
        sma20, sma50, sma200, current_price,
        signals for each MA, golden_cross/death_cross

    Example: calculate_moving_averages("TCS.NS")
    """
    from app.services.stock_service import calculate_moving_averages as _fn

    return _fn(symbol)


@mcp.tool()
def get_top_gainers_losers(count: int = 10) -> dict:
    """
    Get top gaining and losing stocks from NIFTY 50 today.

    Args:
        count: Number of gainers and losers to return (default 10)
               Must be between 1 and 30

    Returns:
        gainers: list of top gaining stocks with change_percent
        losers: list of top losing stocks with change_percent

    Example: get_top_gainers_losers(5)
    """
    from app.services.stock_service import get_top_gainers_losers as _fn

    return _fn(count)


@mcp.tool()
def get_market_news(ticker: str) -> list[dict]:
    """
    Get latest market news for a given ticker using yfinance.

    Args:
        ticker: NSE/BSE stock symbol or index symbol.
                Examples:
                  - RELIANCE.NS, TCS.NS, HDFCBANK.NS
                  - NSE, NIFTY, NIFTY50 (mapped to NIFTY 50 index)
                  - BSE, SENSEX (mapped to BSE Sensex index)

    Returns:
        List of news items with:
          - title
          - publisher
          - link
          - publishedAt (formatted in Indian Standard Time)

    Example:
        get_market_news("RELIANCE.NS")
        get_market_news("NSE")
    """
    from app.services.news_service import get_market_news as _fn

    return _fn(ticker)


# ── MUTUAL FUND TOOLS ────────────────────────────────────

@mcp.tool()
def get_mutual_fund_nav(scheme_code: str) -> dict:
    """
    Get latest NAV for a mutual fund scheme.
    Find scheme codes at: https://www.mfapi.in/

    Args:
        scheme_code: Numeric scheme code e.g. "119551" for
                     HDFC Top 100 Fund

    Returns:
        scheme_code, scheme_name, nav, date

    Example: get_mutual_fund_nav("119551")
    """
    from app.services.mutual_fund_service import get_mutual_fund_nav as _fn

    return _fn(scheme_code)


@mcp.tool()
def search_mutual_funds(query: str):
    """
    Search mutual funds by name or keyword.

    Args:
        query: Search term e.g. "hdfc top", "tax saver",
               "large cap", "ELSS", "index fund"

    Returns:
        List of matching funds with scheme_code, scheme_name,
        fund_house, scheme_type (top 10 matches)

    Example: search_mutual_funds("parag parikh flexi cap")
    """
    from app.services.mutual_fund_service import search_mutual_funds as _fn

    return _fn(query)


@mcp.tool()
def calculate_sip(
    monthly_investment: float,
    years: int,
    annual_return: float,
) -> dict:
    """
    Calculate SIP (Systematic Investment Plan) future value.
    Uses compound interest formula for accurate projection.

    Args:
        monthly_investment: Amount to invest every month in ₹
                           e.g. 5000 means ₹5,000/month
        years: Investment duration in years (1-50)
        annual_return: Expected annual return percentage
                      e.g. 12 means 12% per year

    Returns:
        monthly_investment, years, annual_return,
        future_value (projected corpus in ₹)

    Example: calculate_sip(5000, 10, 12)
    Means: ₹5000/month for 10 years at 12% = future value
    """
    from app.services.mutual_fund_service import calculate_sip as _fn

    return _fn(monthly_investment, years, annual_return)


@mcp.tool()
def calculate_capital_gains(
    buy_price: float,
    sell_price: float,
    quantity: int,
    holding_days: int,
    asset_type: str = "equity",
) -> dict:
    """
    Calculate Indian capital gains tax on investments.

    Tax Rules (2024):
    EQUITY - STCG (< 1 year): 20% flat
    EQUITY - LTCG (>= 1 year): 12.5% above ₹1.25 lakh exemption
    DEBT: Taxed as per income slab

    Args:
        buy_price: Purchase price per unit in ₹
        sell_price: Selling price per unit in ₹
        quantity: Number of shares/units
        holding_days: Number of days held
        asset_type: "equity" for stocks/equity MF,
                    "debt" for debt funds

    Returns:
        profit_or_loss, gain_type (STCG/LTCG),
        tax_amount, tax_rate, net_profit_after_tax,
        exemption_applied

    Example: calculate_capital_gains(2000, 2800, 10, 400, "equity")
    Means: Bought at ₹2000, sold at ₹2800, 10 shares,
           held 400 days, equity investment
    """
    from app.services.mutual_fund_service import calculate_capital_gains as _fn

    return _fn(buy_price, sell_price, quantity, holding_days, asset_type)


# ── IPO TOOLS ────────────────────────────────────────────

@mcp.tool()
def get_upcoming_ipos() -> list:
    """
    Get list of upcoming and currently open IPOs in India.
    Data scraped from Chittorgarh.com

    Returns:
        List of IPOs with name, open_date, close_date,
        price_band, gmp, subscription_status, lot_size,
        issue_size, listing_date

    Example: get_upcoming_ipos()
    """
    from app.services.ipo_service import get_upcoming_ipos as _fn

    return _fn()


@mcp.tool()
def get_gmp(ipo_name: str | None = None):
    """
    Get Grey Market Premium (GMP) for IPOs.
    GMP shows unofficial market sentiment before listing.
    Positive GMP = expected listing above issue price.

    Args:
        ipo_name: Optional IPO name filter e.g. "Ola Electric"
                  If None, returns all current GMP data

    Returns:
        List with ipo_name, gmp_price (₹), gmp_percent,
        issue_price, estimated_listing price

    Example: get_gmp("Swiggy") or get_gmp() for all
    """
    from app.services.ipo_service import get_gmp as _fn

    return _fn(ipo_name)


@mcp.tool()
def get_ipo_performance(limit: int = 10) -> list:
    """
    Get recent IPO listing performance and returns.
    Shows how IPOs performed on listing day vs issue price.

    Args:
        limit: Number of recent IPOs to return (default 10)

    Returns:
        List with company_name, listing_date, issue_price,
        listing_price, listing_gain_percent,
        current_price, current_gain_percent

    Example: get_ipo_performance(5)
    """
    from app.services.ipo_service import get_ipo_performance as _fn

    return _fn(limit)


@mcp.tool()
def get_sme_stock_analysis(symbol: str) -> dict:
    """
    Analyze SME (Small & Medium Enterprise) stocks.
    SME stocks trade on NSE SME and BSE SME platforms.

    Args:
        symbol: Stock symbol with .NS or .BO suffix
                e.g. "DELHIVERY.NS", "POLICYBZR.NS"

    Returns:
        price, change, 52_week_high, 52_week_low,
        market_cap, pe_ratio, category (Micro/Small/Mid Cap SME),
        price_vs_52w_high, price_vs_52w_low,
        company_name, sector, industry

    Example: get_sme_stock_analysis("DELHIVERY.NS")
    """
    from app.services.ipo_service import get_sme_stock_analysis as _fn

    return _fn(symbol)


# ── MACRO ECONOMIC TOOLS ─────────────────────────────────

@mcp.tool()
def get_repo_rate() -> dict:
    """
    Get current RBI repo rate (key lending rate).
    Repo rate affects EMIs, loans, and market liquidity.
    Higher repo rate = tighter money supply = bearish for markets.

    Returns:
        repo_rate (%), last_updated date

    Example: get_repo_rate()
    """
    from app.services.macro_service import get_repo_rate as _fn

    return _fn()


@mcp.tool()
def get_inflation() -> list:
    """
    Get India CPI (Consumer Price Index) inflation data.
    Source: World Bank API

    Returns:
        List of yearly inflation data with year and
        inflation_percent sorted newest first (last 3 years)

    Example: get_inflation()
    """
    from app.services.macro_service import get_inflation as _fn

    return _fn()


@mcp.tool()
def get_gdp_growth() -> list:
    """
    Get India GDP growth rate data.
    Source: World Bank API

    Returns:
        List of yearly GDP growth data with year and
        gdp_growth_percent sorted newest first (last 3 years)

    Example: get_gdp_growth()
    """
    from app.services.macro_service import get_gdp as _fn

    return _fn()


# ── SECTOR TOOLS ─────────────────────────────────────────

@mcp.tool()
def get_sector_performance_tool(sector_name: str) -> dict:
    """
    Get detailed performance of an Indian market sector.

    Available sectors:
    banking, it, pharma, auto, fmcg, energy, metals, realestate

    Args:
        sector_name: One of the available sectors above
                     (case insensitive)

    Returns:
        sector_avg_day_change, sector_avg_week_change,
        sentiment (Bullish/Bearish/Neutral),
        top_performer, bottom_performer,
        advancing, declining counts,
        individual stock data for all stocks in sector

    Example: get_sector_performance_tool("banking")
    Example: get_sector_performance_tool("it")
    """
    from app.services.sector_service import get_sector_performance as _fn

    return _fn(sector_name.lower())


@mcp.tool()
def get_all_sectors_summary_tool() -> list:
    """
    Get performance summary of ALL Indian market sectors.
    Useful for identifying which sectors are outperforming today.

    Returns:
        List of all sectors sorted by avg_day_change (best first)
        Each entry: sector_name, sentiment, avg_day_change,
        top_performer, advancing, declining

    Example: get_all_sectors_summary_tool()
    """
    from app.services.sector_service import get_all_sectors_summary as _fn

    return _fn()


# ── PORTFOLIO TOOLS ──────────────────────────────────────

@mcp.tool()
def analyze_portfolio_tool(stocks: list) -> dict:
    """
    Comprehensive portfolio analysis with P&L, sector
    allocation and rebalancing suggestions.

    Args:
        stocks: List of stock dicts with these exact keys:
        [
          {"symbol": "RELIANCE.NS", "quantity": 10,
           "buy_price": 2000.0},
          {"symbol": "TCS.NS", "quantity": 5,
           "buy_price": 3500.0},
          {"symbol": "HDFCBANK.NS", "quantity": 20,
           "buy_price": 1500.0}
        ]
        - symbol: NSE symbol with .NS suffix
        - quantity: number of shares owned (integer)
        - buy_price: your purchase price per share (float)

    Returns:
        portfolio_summary: total_invested, total_current_value,
                          total_profit_loss, total_return_percent,
                          best_performer, worst_performer
        stocks: individual analysis for each stock
        sector_allocation: percentage in each sector
        rebalancing_suggestions: overweight/underweight advice
        overall_sentiment: Profit or Loss

    Example:
    analyze_portfolio_tool([
        {"symbol": "RELIANCE.NS", "quantity": 10,
         "buy_price": 2000},
        {"symbol": "TCS.NS", "quantity": 5,
         "buy_price": 3500}
    ])
    """
    from app.services.portfolio_service import analyze_portfolio as _fn

    return _fn(stocks)


if __name__ == "__main__":
    # Run as MCP server (stdio mode for Claude Desktop)
    mcp.run()

