"""
Macroeconomic tools for Bharat FinanceMCP (Phase 5).

Provides high-level Indian macro indicators for the AI:
- RBI policy rates and CRR
- CPI / (placeholder) WPI inflation
- GDP growth (World Bank)
- Foreign exchange reserves

Design goals:
- Uses httpx for asynchronous HTTP with a 10-second timeout and up to 2 retries
- Scrapes RBI where no simple JSON API exists, with robust fallbacks
- Returns clean JSON dictionaries plus simple "Metric vs Value" tables
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
COMMON_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept-Language": "en-IN,en;q=0.9",
}
TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 2

WORLD_BANK_BASE = "https://api.worldbank.org/v2/country/IND/indicator"
INFLATION_INDICATOR = "FP.CPI.TOTL.ZG"  # CPI inflation (annual %)
GDP_INDICATOR = "NY.GDP.MKTP.KD.ZG"     # GDP growth (annual %)

# RBI sources
RBI_HOME_URL = "https://www.rbi.org.in/"
FOREX_RESERVES_URL = "https://www.rbi.org.in/Scripts/WSSView.aspx?Id=22015"


def _to_table(columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    """
    Minimal table abstraction (Metric vs Value) for AI consumption.
    """
    return {"columns": columns, "rows": rows}


async def _fetch_with_retries(
    url: str,
    params: Optional[Dict[str, Any]] = None,
) -> Optional[httpx.Response]:
    """
    Async HTTP GET with retry and 10-second timeout.
    """
    timeout = httpx.Timeout(TIMEOUT_SECONDS)
    async with httpx.AsyncClient(
        headers=COMMON_HEADERS,
        timeout=timeout,
        verify=False,  # Government sites often have fiddly SSL in local dev
    ) as client:
        last_error: Optional[Exception] = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                return resp
            except Exception as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(1.0)
                else:
                    return None
        return None


def _run(coro: Any) -> Any:
    """
    Run an async coroutine in a synchronous context.
    """
    return asyncio.run(coro)


def _make_soup(html: str) -> Optional[BeautifulSoup]:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return None


# ── RBI Policy Rates ────────────────────────────────────────

def _parse_rbi_policy_table(html: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort parser for RBI's "Policy Rates" / "Current Rates" table.
    """
    soup = _make_soup(html)
    if soup is None:
        return None

    tables = soup.find_all("table")
    target = None
    for table in tables:
        text = table.get_text(" ", strip=True).lower()
        if "policy repo rate" in text or "bank rate" in text:
            target = table
            break

    if target is None:
        return None

    metrics: Dict[str, float] = {}
    for row in target.find_all("tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue
        label = cols[0].get_text(" ", strip=True).lower()
        value_text = cols[1].get_text(" ", strip=True)
        m = re.search(r"(\d+(?:\.\d+)?)", value_text)
        if not m:
            continue
        value = float(m.group(1))
        if "repo" in label and "reverse" not in label:
            metrics["repo_rate"] = value
        elif "reverse repo" in label:
            metrics["reverse_repo_rate"] = value
        elif "msf" in label:
            metrics["msf_rate"] = value
        elif "bank rate" in label:
            metrics["bank_rate"] = value
        elif "cash reserve ratio" in label or "crr" in label:
            metrics["crr"] = value

    if not metrics:
        return None

    return metrics


def get_rbi_rates() -> Dict[str, Any]:
    """
    Fetches the current RBI policy rates and CRR.

    Tries to scrape RBI's home page "Current / Policy Rates" table.
    If scraping fails, returns a clearly-marked static fallback with
    an accuracy disclaimer.
    """
    resp = _run(_fetch_with_retries(RBI_HOME_URL))
    scraped: Optional[Dict[str, Any]] = None
    if resp is not None:
        scraped = _parse_rbi_policy_table(resp.text)

    if scraped:
        metrics = scraped
        metrics["source"] = "RBI (scraped from home page)"
        metrics.setdefault("last_updated", "See RBI current rates section")
    else:
        metrics = {
            "repo_rate": 6.5,
            "reverse_repo_rate": 3.35,
            "msf_rate": 6.75,
            "bank_rate": 6.75,
            "crr": 4.5,
            "source": "Static fallback – verify with RBI for most recent values.",
            "last_updated": "Approx. 2025-01 (example only)",
        }

    table = _to_table(
        ["Metric", "Value (%)"],
        [
            ["Policy Repo Rate", metrics.get("repo_rate")],
            ["Reverse Repo Rate", metrics.get("reverse_repo_rate")],
            ["MSF Rate", metrics.get("msf_rate")],
            ["Bank Rate", metrics.get("bank_rate")],
            ["Cash Reserve Ratio (CRR)", metrics.get("crr")],
        ],
    )

    return {
        "metrics": metrics,
        "table": table,
    }


# ── Inflation (CPI + placeholder WPI) ───────────────────────

def get_india_inflation() -> Dict[str, Any]:
    """
    Fetches latest CPI inflation for India from the World Bank API,
    and returns a placeholder for WPI (not available via World Bank).

    CPI indicator: FP.CPI.TOTL.ZG (annual %).
    """
    url = f"{WORLD_BANK_BASE}/{INFLATION_INDICATOR}"
    resp = _run(_fetch_with_retries(url, params={"format": "json", "per_page": 10}))
    latest_cpi_value: Optional[float] = None
    latest_cpi_year: Optional[int] = None

    if resp is not None:
        try:
            data = resp.json()
            if isinstance(data, list) and len(data) >= 2:
                records = data[1]
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    value = item.get("value")
                    date = item.get("date")
                    if value is not None and date:
                        latest_cpi_value = round(float(value), 2)
                        latest_cpi_year = int(date)
                        break
        except Exception:
            latest_cpi_value = None
            latest_cpi_year = None

    metrics = {
        "cpi_inflation_percent": latest_cpi_value,
        "cpi_year": latest_cpi_year,
        # WPI is not available via World Bank; leave as placeholder.
        "wpi_inflation_percent": None,
        "wpi_year": None,
        "wpi_note": "Wholesale Price Index (WPI) data is not available via the World Bank API. "
        "Please consult DPIIT/RBI for official WPI releases.",
    }

    table_rows = [
        ["CPI Inflation (annual %)", metrics["cpi_inflation_percent"], metrics["cpi_year"]],
        ["WPI Inflation (annual %)", metrics["wpi_inflation_percent"], metrics["wpi_year"]],
    ]
    table = _to_table(["Metric", "Value", "Year"], table_rows)

    return {
        "metrics": metrics,
        "table": table,
        "source": "World Bank (CPI); WPI requires Indian official sources.",
    }


# ── GDP Growth ───────────────────────────────────────────────

def get_india_gdp_growth() -> Dict[str, Any]:
    """
    Fetches the latest available annual GDP growth rate for India
    from the World Bank API (NY.GDP.MKTP.KD.ZG).
    """
    url = f"{WORLD_BANK_BASE}/{GDP_INDICATOR}"
    resp = _run(_fetch_with_retries(url, params={"format": "json", "per_page": 10}))
    latest_value: Optional[float] = None
    latest_year: Optional[int] = None

    if resp is not None:
        try:
            data = resp.json()
            if isinstance(data, list) and len(data) >= 2:
                records = data[1]
                for item in records:
                    if not isinstance(item, dict):
                        continue
                    value = item.get("value")
                    date = item.get("date")
                    if value is not None and date:
                        latest_value = round(float(value), 2)
                        latest_year = int(date)
                        break
        except Exception:
            latest_value = None
            latest_year = None

    metrics = {
        "gdp_growth_percent": latest_value,
        "year": latest_year,
    }

    table = _to_table(
        ["Metric", "Value", "Year"],
        [["GDP growth (annual %)", metrics["gdp_growth_percent"], metrics["year"]]],
    )

    return {
        "metrics": metrics,
        "table": table,
        "source": "World Bank (NY.GDP.MKTP.KD.ZG)",
    }


# ── Forex Reserves ───────────────────────────────────────────

def get_forex_reserves() -> Dict[str, Any]:
    """
    Fetches the latest foreign exchange reserves for India (USD million)
    from RBI's Weekly Statistical Supplement page.

    Because RBI pages change layout periodically, this function is
    best-effort; on failure it returns a clear 'data unavailable'
    message instead of crashing.
    """
    resp = _run(_fetch_with_retries(FOREX_RESERVES_URL))
    if resp is None:
        return {
            "error": "Foreign exchange reserves data currently unavailable.",
            "source": FOREX_RESERVES_URL,
        }

    soup = _make_soup(resp.text)
    if soup is None:
        return {
            "error": "Foreign exchange reserves data currently unavailable.",
            "source": FOREX_RESERVES_URL,
        }

    text = soup.get_text(" ", strip=True)

    # Heuristic: look for "Total Foreign Exchange Reserves" followed by a number
    value_million: Optional[float] = None
    match = re.search(
        r"Total Foreign Exchange Reserves[\s:]*([0-9,]+)",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        try:
            value_million = float(match.group(1).replace(",", ""))
        except Exception:
            value_million = None

    # Attempt to parse an "as on" date
    as_of: Optional[str] = None
    date_match = re.search(
        r"As on\s*([\d]{1,2}\s+[A-Za-z]{3,9}\s+\d{4})",
        text,
        flags=re.IGNORECASE,
    )
    if date_match:
        as_of = date_match.group(1)

    if value_million is None:
        return {
            "error": "Foreign exchange reserves figure could not be parsed.",
            "source": FOREX_RESERVES_URL,
        }

    metrics = {
        "forex_reserves_usd_million": value_million,
        "as_of": as_of,
        "note": "Value is approximate and parsed from RBI statistical supplement.",
    }

    table = _to_table(
        ["Metric", "Value", "As of"],
        [["Total Foreign Exchange Reserves (USD million)", value_million, as_of]],
    )

    return {
        "metrics": metrics,
        "table": table,
    }

