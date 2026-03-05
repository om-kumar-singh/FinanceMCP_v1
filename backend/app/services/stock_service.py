"""
Stock data service using yfinance.
"""

import pandas_ta as ta
import yfinance as yf

from app.services.stock_search_service import resolve_symbol

# NIFTY 50 symbols (NSE)
NIFTY_50_SYMBOLS = [
    "RELIANCE.NS",
    "TCS.NS",
    "HDFCBANK.NS",
    "INFY.NS",
    "ICICIBANK.NS",
    "HINDUNILVR.NS",
    "ITC.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "AXISBANK.NS",
    "ASIANPAINT.NS",
    "MARUTI.NS",
    "TATAMOTORS.NS",
    "WIPRO.NS",
    "ULTRACEMCO.NS",
    "NESTLEIND.NS",
    "TITAN.NS",
    "BAJFINANCE.NS",
    "BAJAJFINSV.NS",
    "TECHM.NS",
    "HCLTECH.NS",
    "SUNPHARMA.NS",
    "DRREDDY.NS",
    "ONGC.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "COALINDIA.NS",
    "JSWSTEEL.NS",
]


def get_stock_quote(symbol: str) -> dict | None:
    """
    Fetch stock quote data for the given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., RELIANCE.NS, TCS.NS)

    Returns:
        Dict with quote data, or None if symbol is invalid or no data available.
    """
    if not symbol or not symbol.strip():
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    ticker = yf.Ticker(symbol)

    # Fetch 5 days of history to ensure we have previous close
    hist = ticker.history(period="5d")

    if hist is None or hist.empty:
        return None

    # Need at least 2 rows for previous close
    if len(hist) < 2:
        return None

    latest = hist.iloc[-1]
    previous = hist.iloc[-2]

    close = float(latest["Close"])
    previous_close = float(previous["Close"])
    price = round(close, 2)
    change = round(close - previous_close, 2)
    change_percent = round((change / previous_close) * 100, 2) if previous_close else 0
    volume = int(latest["Volume"]) if "Volume" in latest else 0
    day_high = round(float(latest["High"]), 2) if "High" in latest else price
    day_low = round(float(latest["Low"]), 2) if "Low" in latest else price

    return {
        "symbol": symbol,
        "price": price,
        "change": change,
        "change_percent": change_percent,
        "volume": volume,
        "day_high": day_high,
        "day_low": day_low,
    }


def get_stock_detail(symbol: str) -> dict | None:
    """
    Fetch stock quote plus fundamentals (PE, dividend yield, market cap, sector) for the AI advisor.

    Returns:
        Dict with symbol, price, pe, dividendYield, marketCap, sector (and quote fields), or None.
    """
    quote = get_stock_quote(symbol)
    if quote is None:
        return None

    symbol_clean = quote["symbol"]
    ticker = yf.Ticker(symbol_clean)
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    pe = info.get("trailingPE") or info.get("forwardPE")
    if pe is not None:
        pe = round(float(pe), 1)

    div_yield = info.get("dividendYield")
    if div_yield is not None:
        div_yield = round(float(div_yield) * 100, 2) if div_yield else 0.0
    else:
        div_yield = 0.0

    mcap = info.get("marketCap")
    if mcap is not None and mcap > 0:
        if mcap >= 1_00_000_00_00_000:  # >= 1L Cr
            market_cap_str = f"{mcap / 1_00_000_00_00_000:.1f}L Cr"
        elif mcap >= 1_00_000_00_000:  # >= 1000 Cr
            market_cap_str = f"{mcap / 1_00_000_00_000:.0f} Cr"
        else:
            market_cap_str = f"{mcap / 1_00_000_00:.0f} Cr"
    else:
        market_cap_str = "N/A"

    sector = (info.get("sector") or "N/A").strip() or "N/A"

    return {
        "symbol": symbol_clean,
        "price": quote["price"],
        "pe": pe,
        "dividendYield": div_yield,
        "marketCap": market_cap_str,
        "sector": sector,
        "change": quote.get("change"),
        "change_percent": quote.get("change_percent"),
        "volume": quote.get("volume"),
        "day_high": quote.get("day_high"),
        "day_low": quote.get("day_low"),
    }


def get_stock_history(symbol: str, period: str = "6mo") -> dict | None:
    """
    Fetch OHLCV history for charts. period: 1mo, 3mo, 6mo, 1y.

    Returns:
        Dict with symbol, period, dates[], opens[], highs[], lows[], closes[], volumes[],
        or None if invalid. All numeric arrays for Recharts.
    """
    if not symbol or not symbol.strip():
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    if period not in ("1mo", "3mo", "6mo", "1y", "2y"):
        period = "6mo"

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist is None or hist.empty or len(hist) < 2:
        return None

    hist = hist.reset_index()
    if "Date" not in hist.columns and "Datetime" in hist.columns:
        hist["Date"] = hist["Datetime"]

    dates = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    for _, row in hist.iterrows():
        d = row.get("Date")
        if hasattr(d, "strftime"):
            dates.append(d.strftime("%Y-%m-%d"))
        else:
            dates.append(str(d)[:10])
        opens.append(round(float(row.get("Open", 0)), 2))
        highs.append(round(float(row.get("High", 0)), 2))
        lows.append(round(float(row.get("Low", 0)), 2))
        closes.append(round(float(row.get("Close", 0)), 2))
        volumes.append(int(row.get("Volume", 0)))

    return {
        "symbol": symbol,
        "period": period,
        "dates": dates,
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": volumes,
    }


def calculate_rsi(symbol: str, period: int = 14) -> dict | None:
    """
    Calculate RSI (Relative Strength Index) for the given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., RELIANCE.NS, TCS.NS)
        period: RSI lookback period (default 14)

    Returns:
        Dict with RSI data, or None if symbol is invalid or insufficient data.
    """
    if not symbol or not symbol.strip():
        return None

    if period < 2:
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    ticker = yf.Ticker(symbol)

    # Fetch enough history for RSI (period * 2 ensures sufficient data)
    days_needed = max(period * 2, 60)
    hist = ticker.history(period=f"{days_needed}d")

    if hist is None or hist.empty:
        return None

    if len(hist) < period + 1:
        return None

    rsi_series = ta.rsi(hist["Close"], length=period)

    if rsi_series is None or rsi_series.empty:
        return None

    latest_rsi = float(rsi_series.iloc[-1])

    if latest_rsi > 70:
        signal = "overbought"
    elif latest_rsi < 30:
        signal = "oversold"
    else:
        signal = "neutral"

    return {
        "symbol": symbol,
        "rsi": round(latest_rsi, 2),
        "period": period,
        "signal": signal,
    }


def calculate_macd(symbol: str) -> dict | None:
    """
    Calculate MACD (Moving Average Convergence Divergence) for the given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., RELIANCE.NS, TCS.NS)

    Returns:
        Dict with MACD data, or None if symbol is invalid or insufficient data.
    """
    if not symbol or not symbol.strip():
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    ticker = yf.Ticker(symbol)

    # Fetch at least 60 days of history for MACD (needs ~35+ for default 12/26/9)
    hist = ticker.history(period="60d")

    if hist is None or hist.empty:
        return None

    if len(hist) < 35:
        return None

    macd_df = ta.macd(hist["Close"], fast=12, slow=26, signal=9)

    if macd_df is None or macd_df.empty:
        return None

    # pandas_ta returns DataFrame with MACD line, Signal line, Histogram columns
    cols = macd_df.columns.tolist()
    if len(cols) < 3:
        return None

    latest = macd_df.iloc[-1]
    macd_line = float(latest[cols[0]])
    signal_line = float(latest[cols[1]])
    histogram = float(latest[cols[2]])

    # Handle NaN from insufficient warmup
    if any(v != v for v in (macd_line, signal_line, histogram)):
        return None

    trend = "bullish" if macd_line > signal_line else "bearish"

    return {
        "symbol": symbol,
        "macd": round(macd_line, 2),
        "signal": round(signal_line, 2),
        "histogram": round(histogram, 2),
        "trend": trend,
    }


def get_top_gainers_losers(count: int = 10) -> dict | None:
    """
    Fetch NIFTY 50 stocks and return top N gainers and top N losers by daily % change.

    Args:
        count: Number of top gainers and losers to return (default 10)

    Returns:
        Dict with gainers and losers lists, or None on error.
    """
    if count < 1 or count > 50:
        return None

    results = []
    for symbol in NIFTY_50_SYMBOLS:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="5d")
        if hist is None or hist.empty or len(hist) < 2:
            continue
        latest = hist.iloc[-1]
        previous = hist.iloc[-2]
        close = float(latest["Close"])
        previous_close = float(previous["Close"])
        change_percent = round((close - previous_close) / previous_close * 100, 2) if previous_close else 0
        results.append({
            "symbol": symbol,
            "price": round(close, 2),
            "change_percent": change_percent,
        })

    if not results:
        return None

    sorted_by_change = sorted(results, key=lambda x: x["change_percent"], reverse=True)
    gainers = sorted_by_change[:count]
    losers = sorted_by_change[-count:][::-1]

    return {
        "gainers": gainers,
        "losers": losers,
    }


def calculate_moving_averages(symbol: str) -> dict | None:
    """
    Calculate SMA20, SMA50, SMA200 and current price vs each MA.

    Args:
        symbol: Stock ticker symbol (e.g., RELIANCE.NS, TCS.NS)

    Returns:
        Dict with price, SMAs, and signal (above/below) for each, or None if invalid.
    """
    if not symbol or not symbol.strip():
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="1y")

    if hist is None or hist.empty:
        return None

    if len(hist) < 200:
        return None

    close = hist["Close"]
    sma20 = ta.sma(close, length=20)
    sma50 = ta.sma(close, length=50)
    sma200 = ta.sma(close, length=200)

    if sma20 is None or sma50 is None or sma200 is None:
        return None

    latest_close = float(close.iloc[-1])
    latest_sma20 = float(sma20.iloc[-1])
    latest_sma50 = float(sma50.iloc[-1])
    latest_sma200 = float(sma200.iloc[-1])

    if any(v != v for v in (latest_sma20, latest_sma50, latest_sma200)):
        return None

    def _signal(price: float, ma: float) -> str:
        return "above" if price > ma else "below"

    return {
        "symbol": symbol,
        "price": round(latest_close, 2),
        "sma20": round(latest_sma20, 2),
        "sma50": round(latest_sma50, 2),
        "sma200": round(latest_sma200, 2),
        "signal_sma20": _signal(latest_close, latest_sma20),
        "signal_sma50": _signal(latest_close, latest_sma50),
        "signal_sma200": _signal(latest_close, latest_sma200),
    }


def calculate_bollinger_bands(symbol: str) -> dict | None:
    """
    Calculate Bollinger Bands (length=20, std=2) for the given symbol.

    Args:
        symbol: Stock ticker symbol (e.g., RELIANCE.NS, TCS.NS)

    Returns:
        Dict with upper, middle, lower bands and signal (overbought/oversold/neutral), or None if invalid.
    """
    if not symbol or not symbol.strip():
        return None

    symbol = symbol.strip().upper()
    if not (symbol.endswith(".NS") or symbol.endswith(".BO")):
        resolved = resolve_symbol(symbol)
        if not resolved:
            return None
        symbol = resolved

    ticker = yf.Ticker(symbol)
    hist = ticker.history(period="60d")

    if hist is None or hist.empty:
        return None

    if len(hist) < 25:
        return None

    bbands_df = ta.bbands(hist["Close"], length=20, std=2)

    if bbands_df is None or bbands_df.empty:
        return None

    cols = bbands_df.columns.tolist()
    if len(cols) < 3:
        return None

    latest = bbands_df.iloc[-1]
    lower = float(latest[cols[0]])
    middle = float(latest[cols[1]])
    upper = float(latest[cols[2]])

    if any(v != v for v in (lower, middle, upper)):
        return None

    price = float(hist["Close"].iloc[-1])

    if price > upper:
        signal = "overbought"
    elif price < lower:
        signal = "oversold"
    else:
        signal = "neutral"

    return {
        "symbol": symbol,
        "price": round(price, 2),
        "upper": round(upper, 2),
        "middle": round(middle, 2),
        "lower": round(lower, 2),
        "signal": signal,
    }
