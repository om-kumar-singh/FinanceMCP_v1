"""
Response optimizer / adaptive truncation for Bharat FinanceMCP (Phase 6).

The goal is to avoid oversized payloads being sent back to MCP clients
by trimming large historical arrays, verbose descriptions, and
non-essential metadata, while keeping the core numeric insight intact.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List


MAX_PAYLOAD_BYTES = 100 * 1024  # 100 KiB hard limit

HISTORICAL_KEYS = {
    "historical_prices",
    "price_history",
    "history",
    "nav_history",
    "prices",
}

LONG_TEXT_KEYS = {
    "description",
    "company_description",
    "summary",
    "news_summary",
    "long_description",
}

NON_ESSENTIAL_KEYS = {
    "uuid",
    "internal_id",
    "internalId",
    "trace_id",
    "request_id",
}


def _looks_like_price_series(items: Iterable[Any]) -> bool:
    """
    Heuristic to detect a list of historical price points.
    """
    sample = []
    for i, item in enumerate(items):
        if i >= 5:
            break
        sample.append(item)
    if not sample:
        return False
    for it in sample:
        if not isinstance(it, dict):
            return False
        keys = {k.lower() for k in it.keys()}
        if not ({"date", "close"} <= keys or {"date", "nav"} <= keys or {"date", "price"} <= keys):
            return False
    return True


def _truncate_string(value: str, limit: int = 200) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def _optimize_structure(obj: Any) -> Any:
    """
    Recursively optimize a Python structure (dict/list/primitives) according
    to the adaptive truncation rules.
    """
    if isinstance(obj, dict):
        new: Dict[str, Any] = {}
        for k, v in obj.items():
            if k in NON_ESSENTIAL_KEYS:
                continue

            if isinstance(v, list) and k in HISTORICAL_KEYS:
                v = v[-5:]

            if isinstance(v, str) and k in LONG_TEXT_KEYS:
                v = _truncate_string(v)

            new[k] = _optimize_structure(v)
        return new

    if isinstance(obj, list):
        if _looks_like_price_series(obj):
            obj = list(obj)[-5:]
        return [_optimize_structure(v) for v in obj]

    if isinstance(obj, str):
        # Do not blindly truncate all strings; only ones behind known keys
        # are truncated in the dict branch above.
        return obj

    return obj


def optimize_payload(data: Any) -> Any:
    """
    Apply adaptive truncation if the serialized payload would exceed 100KB.

    The function is safe to call on any tool output; if the payload is
    already small, it simply returns the original object untouched.
    """
    try:
        raw = json.dumps(data, ensure_ascii=False, default=str)
    except Exception:
        return data

    if len(raw.encode("utf-8")) <= MAX_PAYLOAD_BYTES:
        return data

    optimized = _optimize_structure(data)

    # Best-effort: we do not loop endlessly; a single optimization pass
    # usually brings payloads safely under the limit.
    return optimized

