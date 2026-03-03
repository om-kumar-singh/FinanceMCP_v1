"""
Adaptive response size optimizer.
"""

import json
from typing import Any, Dict, List, Union

JsonType = Union[Dict[str, Any], List[Any]]

MAX_RESPONSE_SIZE = 100 * 1024  # 100 KB

_TEXT_FIELDS = {"description", "summary", "notes", "content"}
_ESSENTIAL_FIELDS = {
    "price",
    "change",
    "change_percent",
    "volume",
    "rsi",
    "macd",
    "signal",
    "nav",
    "pe",
    "pb",
    "symbol",
    "name",
    "date",
    "sector",
    "market_cap",
    "profit_loss",
    "return_percent",
}


def get_response_size_kb(data: JsonType) -> float:
    """
    Return size of JSON-encoded data in kilobytes.
    """
    try:
        raw = json.dumps(data).encode("utf-8")
    except Exception:
        return 0.0
    return round(len(raw) / 1024, 2)


def _truncate_text(value: str, max_len: int = 150) -> str:
    if len(value) <= max_len:
        return value
    return value[:max_len] + "..."


def _optimize_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
    optimized: Dict[str, Any] = {}
    for key, value in obj.items():
        key_lower = str(key).lower()
        if isinstance(value, str) and key_lower in _TEXT_FIELDS:
            optimized[key] = _truncate_text(value)
        elif isinstance(value, list):
            optimized[key] = _optimize_list(value, is_root=False)
        elif isinstance(value, dict):
            optimized[key] = _optimize_dict(value)
        else:
            optimized[key] = value
    return optimized


def _optimize_list(items: List[Any], is_root: bool) -> Any:
    if not items:
        return items

    # Historical-like data: list of dicts with a date/timestamp field
    first = items[0]
    if isinstance(first, dict) and any(
        k in first for k in ("date", "timestamp", "datetime", "time")
    ):
        return [_optimize_dict(obj) if isinstance(obj, dict) else obj for obj in items[-2:]]

    # Generic list truncation
    if is_root:
        truncated = [
            _optimize_dict(obj) if isinstance(obj, dict) else obj
            for obj in items[:20]
        ]
        if len(items) > 20:
            return {
                "items": truncated,
                "_truncated": True,
                "_total_count": len(items),
            }
        return truncated

    # Nested list: keep first 20 items without wrapping
    return [
        _optimize_dict(obj) if isinstance(obj, dict) else obj
        for obj in items[:20]
    ]


def _optimize(data: JsonType, is_root: bool) -> JsonType:
    if isinstance(data, dict):
        optimized = _optimize_dict(data)
        if is_root:
            optimized["_optimized"] = True
        return optimized
    if isinstance(data, list):
        result = _optimize_list(data, is_root=is_root)
        if isinstance(result, dict) and is_root:
            result["_optimized"] = True
        return result  # type: ignore[return-value]
    return data


def optimize_response(data: JsonType) -> JsonType:
    """
    Optimize a JSON-serializable structure to keep size under control.
    """
    return _optimize(data, is_root=True)

