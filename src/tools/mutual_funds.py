"""
Mutual fund tools built on the free mfapi.in REST API.

Tools:
1. get_mutual_fund_nav(scheme_code: str)
2. mutual_fund_search(query: str)
3. sip_calculator(monthly_investment: float, years: int, expected_return: float)

HTTP calls use aiohttp under the hood; functions themselves are
decorated with simple in-memory cache and rate limiting helpers
similar to those used for stock tools.
"""

from __future__ import annotations

import asyncio
import math
import os
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, ParamSpec

import aiohttp


F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")


def cache(ttl_seconds: int = 300) -> Callable[[F], F]:
    """
    Simple in-memory cache decorator.

    Matches the semantics of the cache decorator used for stock tools:
    caches results for a TTL based on function arguments.
    """

    def decorator(func: F) -> F:
        store: Dict[Tuple[Any, ...], Tuple[float, Any]] = {}

        def make_key(args: Tuple[Any, ...], kwargs: Dict[str, Any]) -> Optional[Tuple[Any, ...]]:
            try:
                return args + (frozenset(kwargs.items()),)
            except TypeError:
                # Unhashable arguments – skip caching.
                return None

        def wrapper(*args: P.args, **kwargs: P.kwargs):
            key = make_key(args, kwargs)
            if key is None:
                return func(*args, **kwargs)

            now = time.time()
            if key in store:
                ts, value = store[key]
                if now - ts <= ttl_seconds:
                    return value

            value = func(*args, **kwargs)
            store[key] = (now, value)
            return value

        return wrapper  # type: ignore[return-value]

    return decorator


def rate_limit(calls_per_minute: int = 60) -> Callable[[F], F]:
    """
    Simple in-memory rate limiter.

    If the per-minute call budget is exceeded, returns a JSON-style
    error dict instead of raising an exception.
    """

    window_seconds = 60

    def decorator(func: F) -> F:
        calls: List[float] = []

        def wrapper(*args: P.args, **kwargs: P.kwargs):
            nonlocal calls
            now = time.time()
            calls = [ts for ts in calls if now - ts < window_seconds]
            if len(calls) >= calls_per_minute:
                return {
                    "error": "Rate limit exceeded. Please try again later.",
                }
            calls.append(now)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


MF_API_BASE = os.getenv("MF_API_BASE_URL", "https://api.mfapi.in/mf")


async def _fetch_json(url: str, params: Optional[Dict[str, Any]] = None) -> Any:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


def _run(coro: Any) -> Any:
    """
    Run an async coroutine in a synchronous context.

    Assumes there is no currently running event loop (typical for CLI / MCP).
    """

    return asyncio.run(coro)


@cache(ttl_seconds=300)
@rate_limit(calls_per_minute=10)
def get_mutual_fund_nav(scheme_code: str) -> Dict[str, Any] | None:
    """
    Fetch the current NAV, date, and daily change for a mutual fund scheme.

    Args:
        scheme_code: Numeric mfapi.in scheme code (e.g. \"119551\").

    Returns:
        Dict with:
            - scheme_code
            - scheme_name
            - nav
            - date
            - change (optional)
            - change_percent (optional)
        or None on error / invalid input.
    """
    if not scheme_code or not str(scheme_code).strip():
        return None

    code_str = str(scheme_code).strip()
    url = f\"{MF_API_BASE}/{code_str}\"

    try:
        data = _run(_fetch_json(url))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    meta = data.get(\"meta\") or {}
    nav_data = data.get(\"data\") or []
    if not isinstance(nav_data, list) or not nav_data:
        return None

    latest = nav_data[0]
    nav_str = latest.get(\"nav\")
    date = latest.get(\"date\")
    if not nav_str or not date:
        return None

    try:
        nav = float(nav_str)
    except (TypeError, ValueError):
        return None

    change: Optional[float] = None
    change_percent: Optional[float] = None
    if len(nav_data) >= 2:
        prev = nav_data[1]
        prev_nav_str = prev.get(\"nav\")
        try:
            prev_nav = float(prev_nav_str)
        except (TypeError, ValueError):
            prev_nav = None
        if prev_nav and prev_nav != 0:
            change = round(nav - prev_nav, 4)
            change_percent = round((change / prev_nav) * 100, 2)

    scheme_name = meta.get(\"scheme_name\") or meta.get(\"schemeName\") or \"\"
    code = meta.get(\"scheme_code\") or meta.get(\"schemeCode\") or code_str

    result: Dict[str, Any] = {
        \"scheme_code\": str(code),
        \"scheme_name\": scheme_name,
        \"nav\": round(nav, 4),
        \"date\": date,
    }
    if change is not None and change_percent is not None:
        result[\"change\"] = change
        result[\"change_percent\"] = change_percent

    return result


@cache(ttl_seconds=300)
@rate_limit(calls_per_minute=10)
def mutual_fund_search(query: str) -> List[Dict[str, Any]] | Dict[str, Any]:
    """
    Search for mutual fund schemes by name using mfapi.in search endpoint.

    Args:
        query: Search string such as \"hdfc top 100\".

    Returns:
        List of matches (each with scheme_code, scheme_name, fund_house, scheme_type),
        an empty list on no matches, or an error dict if rate limited.
    """
    if query is None:
        return []

    q = str(query).strip()
    if not q:
        return []

    url = f\"{MF_API_BASE}/search\"
    try:
        data = _run(_fetch_json(url, params={\"q\": q}))
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    results: List[Dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get(\"schemeCode\") or item.get(\"scheme_code\")
        name = item.get(\"schemeName\") or item.get(\"scheme_name\")
        fund_house = item.get(\"fundHouse\") or item.get(\"fund_house\") or \"\"
        scheme_type = item.get(\"schemeType\") or item.get(\"scheme_type\") or \"\"
        if not code or not name:
            continue
        results.append(
            {
                \"scheme_code\": str(code),
                \"scheme_name\": name,
                \"fund_house\": fund_house,
                \"scheme_type\": scheme_type,
            }
        )
        if len(results) >= 10:
            break

    return results


def sip_calculator(
    monthly_investment: float,
    years: int,
    expected_return: float,
) -> Dict[str, Any]:
    """
    Project SIP future value using:

        FV = P * [((1 + r)^n - 1) / r] * (1 + r)

    where:
        P = monthly_investment
        r = monthly rate = expected_return / 12 / 100
        n = years * 12
    """
    P = float(monthly_investment)
    n = int(years) * 12
    r = float(expected_return) / 12.0 / 100.0

    if n <= 0 or P <= 0:
        fv = 0.0
    elif r == 0:
        fv = P * n
    else:
        fv = P * (((1 + r) ** n - 1.0) / r) * (1 + r)

    return {
        \"monthly_investment\": P,
        \"years\": int(years),
        \"expected_return\": float(expected_return),
        \"future_value\": round(fv, 2),
    }

