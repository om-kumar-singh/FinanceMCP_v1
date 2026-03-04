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

