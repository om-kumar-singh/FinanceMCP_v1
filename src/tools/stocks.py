"""
Core stock tools for BharatFinanceMCP.

This module focuses on:
- Company fundamentals (P/E, dividend yield, 52-week range)
- News aggregation for Indian equities

These tools are designed for AI usage and return compact, structured
data plus small tables that are easy to render in chat responses.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx
import yfinance as yf


HTTP_TIMEOUT = 15.0


def _to_table(columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    return {"columns": columns, "rows": rows}


def _normalise_symbol(raw: str) -> str:
    """
    Best-effort conversion from a user-facing name to an exchange symbol.

    - Leaves symbols with an explicit suffix (e.g. .NS, .BO) unchanged.
    - For bare tickers like 'HDFCBANK', appends '.NS'.
    - For names with spaces like 'HDFC Bank', removes spaces and appends '.NS'.
    """
    s = (raw or "").strip()
    if not s:
        return s

    if "." in s:
        return s

    base = s.replace(" ", "").upper()
    # Default to NSE; clients can override by passing an explicit .BO symbol.
    return f"{base}.NS"


# ── Fundamentals ───────────────────────────────────────────────


def get_company_fundamentals(symbol: str) -> Dict[str, Any]:
    """
    Fetch basic company fundamentals for an exchange symbol using yfinance.

    Returns P/E ratio, dividend yield, and 52-week high/low (when available),
    along with a compact table for easy display.
    """
    if not symbol or not str(symbol).strip():
        return {
            "error": "Symbol is required to fetch company fundamentals.",
        }
    norm_symbol = _normalise_symbol(symbol)

    ticker = yf.Ticker(norm_symbol)

    info: Dict[str, Any] = {}
    try:
        info = ticker.info  # type: ignore[assignment]
    except Exception:
        # yfinance may raise when symbol is invalid or rate-limited
        info = {}

    if not info:
        return {
            "error": f"Fundamental data not available for symbol '{symbol}'.",
            "symbol": symbol,
            "normalized_symbol": norm_symbol,
        }

    pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    dividend_yield_raw = info.get("dividendYield")
    if dividend_yield_raw is not None:
        dividend_yield_percent: Optional[float] = round(float(dividend_yield_raw) * 100.0, 2)
    else:
        dividend_yield_percent = None

    high_52 = info.get("fiftyTwoWeekHigh")
    low_52 = info.get("fiftyTwoWeekLow")

    result = {
        "symbol": symbol,
        "normalized_symbol": norm_symbol,
        "long_name": info.get("longName") or info.get("shortName"),
        "pe_ratio": pe_ratio,
        "dividend_yield_percent": dividend_yield_percent,
        "fifty_two_week_high": high_52,
        "fifty_two_week_low": low_52,
    }

    table_rows: List[List[Any]] = [
        ["Symbol (input)", result["symbol"]],
        ["Symbol (normalized)", result["normalized_symbol"]],
        ["Name", result["long_name"]],
        ["P/E Ratio", result["pe_ratio"]],
        ["Dividend Yield (%)", result["dividend_yield_percent"]],
        ["52-week High", result["fifty_two_week_high"]],
        ["52-week Low", result["fifty_two_week_low"]],
    ]

    return {
        "fundamentals": result,
        "table": _to_table(
            ["Metric", "Value"],
            table_rows,
        ),
        "source": "yfinance / Yahoo Finance",
    }


# ── Technicals & Index Data ────────────────────────────────────


def _fetch_price_history(symbol: str, period: str = "1y") -> Optional[Any]:
    """
    Helper to fetch OHLCV history for a symbol using yfinance.

    Returns a pandas DataFrame or None on failure.
    """
    norm = _normalise_symbol(symbol)
    try:
        ticker = yf.Ticker(norm)
        hist = ticker.history(period=period)
    except Exception:
        return None
    if hist is None or hist.empty:
        return None
    return hist


def _compute_rsi_from_close(close_series, period: int = 14) -> Optional[float]:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    if close_series is None or len(close_series) < period + 1:
        return None
    delta = close_series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    last = float(rsi.iloc[-1])
    if last != last:  # NaN check
        return None
    return round(last, 2)


def _compute_macd_from_close(close_series) -> Optional[Dict[str, float]]:
    try:
        import pandas as pd  # type: ignore
    except Exception:
        return None
    if close_series is None or len(close_series) < 35:
        return None
    exp12 = close_series.ewm(span=12, adjust=False).mean()
    exp26 = close_series.ewm(span=26, adjust=False).mean()
    macd_line = exp12 - exp26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    hist = macd_line - signal_line
    last_macd = float(macd_line.iloc[-1])
    last_signal = float(signal_line.iloc[-1])
    last_hist = float(hist.iloc[-1])
    if any(v != v for v in (last_macd, last_signal, last_hist)):
        return None
    return {
        "macd": round(last_macd, 2),
        "signal": round(last_signal, 2),
        "histogram": round(last_hist, 2),
    }


def get_stock_technicals(symbol: str) -> Dict[str, Any]:
    """
    Compute key technical indicators (RSI, MACD, moving averages) for a stock.

    This tool is designed to support rich interpretations like
    \"RSI is overbought but MACD has just turned bullish\" by returning a
    compact, structured summary along with a tiny price history.
    """
    if not symbol or not str(symbol).strip():
        return {
            "error": "Symbol is required to fetch technical indicators.",
        }

    norm = _normalise_symbol(symbol)
    hist = _fetch_price_history(norm, period="1y")
    if hist is None:
        return {
            "error": f"Price history is not available for symbol '{symbol}'.",
            "symbol": symbol,
            "normalized_symbol": norm,
        }

    close = hist["Close"]

    rsi_value = _compute_rsi_from_close(close, period=14)
    if rsi_value is None:
        rsi_signal = None
    elif rsi_value > 70:
        rsi_signal = "overbought"
    elif rsi_value < 30:
        rsi_signal = "oversold"
    else:
        rsi_signal = "neutral"

    macd_data = _compute_macd_from_close(close)
    if macd_data:
        trend = "bullish" if macd_data["macd"] > macd_data["signal"] else "bearish"
        macd_data["trend"] = trend

    # Moving averages
    sma20 = close.rolling(window=20).mean()
    sma50 = close.rolling(window=50).mean()
    sma200 = close.rolling(window=200).mean()
    latest_close = float(close.iloc[-1])

    def _safe_last(series) -> Optional[float]:
        try:
            val = float(series.iloc[-1])
            if val != val:
                return None
            return round(val, 2)
        except Exception:
            return None

    ma_data = {
        "price": round(latest_close, 2),
        "sma20": _safe_last(sma20),
        "sma50": _safe_last(sma50),
        "sma200": _safe_last(sma200),
    }

    # Small recent price window for context; adaptive optimizer will trim further if needed.
    recent = hist.tail(10).reset_index()
    recent_points: List[Dict[str, Any]] = []
    for _, row in recent.iterrows():
        try:
            date_val = row["Date"].strftime("%Y-%m-%d")
        except Exception:
            date_val = str(row["Date"])
        recent_points.append(
            {
                "date": date_val,
                "close": float(row["Close"]),
            }
        )

    result = {
        "symbol": symbol,
        "normalized_symbol": norm,
        "rsi": rsi_value,
        "rsi_signal": rsi_signal,
        "macd": macd_data,
        "moving_averages": ma_data,
        "historical_prices": recent_points,
    }

    table_rows: List[List[Any]] = [
        ["Symbol (input)", symbol],
        ["Symbol (normalized)", norm],
        ["RSI (14)", rsi_value],
        ["RSI Signal", rsi_signal],
        ["MACD", macd_data["macd"] if macd_data else None],
        ["MACD Signal", macd_data["signal"] if macd_data else None],
        ["MACD Histogram", macd_data["histogram"] if macd_data else None],
        ["MACD Trend", macd_data.get("trend") if macd_data else None],
        ["Price", ma_data["price"]],
        ["SMA20", ma_data["sma20"]],
        ["SMA50", ma_data["sma50"]],
        ["SMA200", ma_data["sma200"]],
    ]

    return {
        "technicals": result,
        "table": _to_table(["Metric", "Value"], table_rows),
        "source": "yfinance / derived technicals",
    }


INDEX_SYMBOLS: Dict[str, str] = {
    "NIFTY50": "^NSEI",
    "NIFTY": "^NSEI",
    "NSEI": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}


def get_index_snapshot(index_code: str = "NIFTY50") -> Dict[str, Any]:
    """
    Get latest index level and simple recent returns for a broad index
    such as NIFTY 50 or Bank NIFTY. Useful for comparing funds/stocks
    against the broader market.
    """
    code = (index_code or "NIFTY50").strip().upper()
    ticker_symbol = INDEX_SYMBOLS.get(code, code)

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist_1y = ticker.history(period="1y")
    except Exception:
        hist_1y = None

    if hist_1y is None or hist_1y.empty:
        return {
            "error": f"Unable to fetch index data for '{index_code}'.",
            "index_code": index_code,
            "ticker": ticker_symbol,
        }

    latest = hist_1y.iloc[-1]
    latest_close = float(latest["Close"])

    def _simple_return(days: int) -> Optional[float]:
        if len(hist_1y) <= days:
            return None
        past = hist_1y.iloc[-days]["Close"]
        if past == 0:
            return None
        return round(((latest_close - float(past)) / float(past)) * 100.0, 2)

    returns = {
        "1m_return_percent": _simple_return(21),
        "3m_return_percent": _simple_return(63),
        "6m_return_percent": _simple_return(126),
        "1y_return_percent": _simple_return(len(hist_1y) - 1),
    }

    table_rows = [
        ["Index Code", code],
        ["Ticker", ticker_symbol],
        ["Latest Level", round(latest_close, 2)],
        ["1M Return (%)", returns["1m_return_percent"]],
        ["3M Return (%)", returns["3m_return_percent"]],
        ["6M Return (%)", returns["6m_return_percent"]],
        ["1Y Return (%)", returns["1y_return_percent"]],
    ]

    return {
        "index_code": code,
        "ticker": ticker_symbol,
        "latest_level": round(latest_close, 2),
        "returns": returns,
        "table": _to_table(["Metric", "Value"], table_rows),
    }


def _fetch_newsapi_headlines(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch top headlines from NewsAPI for a given stock symbol / company name.
    """
    api_key = os.getenv("NEWSAPI_KEY") or os.getenv("NEWS_API_KEY")
    if not api_key:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": symbol,
        "language": "en",
        "pageSize": 5,
        "sortBy": "publishedAt",
        "apiKey": api_key,
    }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    articles = data.get("articles") or []
    cleaned: List[Dict[str, Any]] = []
    for art in articles[:5]:
        if not isinstance(art, dict):
            continue
        title = art.get("title") or ""
        description = art.get("description") or ""
        url_article = art.get("url") or ""
        published_at = art.get("publishedAt") or ""

        if not title:
            continue

        cleaned.append(
            {
                "title": title,
                "description": description,
                "url": url_article,
                "published_at": published_at,
                "source": (art.get("source") or {}).get("name"),
            }
        )
    return cleaned


def _fetch_alpha_vantage_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Fetch news using Alpha Vantage's NEWS_SENTIMENT endpoint, if configured.

    This requires ALPHA_VANTAGE_API_KEY to be set in the environment.
    """
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        return []

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "sort": "LATEST",
        "apikey": api_key,
    }

    try:
        with httpx.Client(timeout=HTTP_TIMEOUT) as client:
            resp = client.get(url, params=params)
            if resp.status_code == 429:
                # Rate limit exceeded – signal caller to fall back.
                return []
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return []

    feed = data.get("feed") or []
    cleaned: List[Dict[str, Any]] = []
    for item in feed[:5]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        url_article = item.get("url") or ""
        published_at = item.get("time_published") or ""
        if not title:
            continue
        cleaned.append(
            {
                "title": title,
                "description": summary,
                "url": url_article,
                "published_at": published_at,
                "source": "Alpha Vantage",
            }
        )
    return cleaned


def _fetch_yfinance_news(symbol: str) -> List[Dict[str, Any]]:
    """
    Fallback news fetcher using yfinance's built-in news field.
    """
    try:
        ticker = yf.Ticker(symbol)
        items = getattr(ticker, "news", None) or []
    except Exception:
        items = []

    cleaned: List[Dict[str, Any]] = []
    for item in items[:5]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or ""
        summary = item.get("summary") or ""
        url_article = item.get("link") or item.get("url") or ""
        published_at = item.get("providerPublishTime") or ""
        if not title:
            continue
        cleaned.append(
            {
                "title": title,
                "description": summary,
                "url": url_article,
                "published_at": published_at,
                "source": item.get("publisher"),
            }
        )
    return cleaned


def get_stock_news(symbol: str) -> Dict[str, Any]:
    """
    Fetch and summarize recent news for a given stock symbol / company.

    Order of preference:
    1. Alpha Vantage NEWS_SENTIMENT (requires ALPHA_VANTAGE_API_KEY)
    2. NewsAPI (if NEWSAPI_KEY / NEWS_API_KEY is set)
    3. yfinance's built-in news field as a final fallback
    """
    if not symbol or not str(symbol).strip():
        return {
            "error": "Symbol or company name is required to fetch news.",
        }

    norm_symbol = _normalise_symbol(symbol)

    articles: List[Dict[str, Any]] = []

    # 1) Try Alpha Vantage (with implicit rate limit of 5 calls/min).
    articles = _fetch_alpha_vantage_news(norm_symbol)

    # 2) If nothing (no key or rate limited), try NewsAPI.
    if not articles:
        articles = _fetch_newsapi_headlines(norm_symbol)

    # 3) If still nothing, fall back to yfinance.
    if not articles:
        articles = _fetch_yfinance_news(norm_symbol)

    if not articles:
        return {
            "error": "No recent news found or news APIs are not configured.",
            "symbol": symbol,
            "normalized_symbol": norm_symbol,
        }

    # Take the most relevant 3 articles for chat responses.
    top_articles = articles[:3]

    rows: List[List[Any]] = []
    for art in top_articles:
        rows.append(
            [
                art.get("title"),
                (art.get("description") or "")[:200],
                art.get("published_at"),
                art.get("url"),
            ]
        )

    table = _to_table(
        ["Headline", "Summary (truncated)", "Published At", "URL"],
        rows,
    )

    return {
        "symbol": symbol,
        "normalized_symbol": norm_symbol,
        "articles": top_articles,
        "table": table,
        "source": "NewsAPI (https://newsapi.org)",
    }

