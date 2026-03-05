"""
Local alert registry for BharatFinanceMCP.

Stores simple NAV and news-sentiment alert rules in a JSON file so the
AI advisor can:
- Register alerts (on user request)
- Evaluate them on demand via a `check_alerts` MCP tool
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# Project root (same logic as in cache.py)
ROOT = Path(__file__).resolve().parents[2]
ALERTS_PATH = ROOT / ".alerts.json"


@dataclass
class NavAlertRule:
    scheme_code: str
    threshold_drop_percent: float  # e.g. 2.0 for -2% in a day


@dataclass
class NewsWatchRule:
    keywords: List[str]


def _load_alerts() -> Dict[str, Any]:
    if not ALERTS_PATH.exists():
        return {"nav_alerts": [], "news_watches": []}
    try:
        return json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"nav_alerts": [], "news_watches": []}


def _save_alerts(data: Dict[str, Any]) -> None:
    try:
        ALERTS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        return


def register_nav_alert(scheme_code: str, threshold_drop_percent: float) -> Dict[str, Any]:
    data = _load_alerts()
    alerts: List[Dict[str, Any]] = data.get("nav_alerts") or []
    # Overwrite existing rule for same scheme, if any.
    alerts = [a for a in alerts if a.get("scheme_code") != scheme_code]
    alerts.append(asdict(NavAlertRule(scheme_code=scheme_code, threshold_drop_percent=float(threshold_drop_percent))))
    data["nav_alerts"] = alerts
    _save_alerts(data)
    return {
        "status": "ok",
        "message": "NAV alert registered.",
        "rule": alerts[-1],
    }


def register_news_watch(keywords: List[str]) -> Dict[str, Any]:
    cleaned = [str(k).strip() for k in keywords if str(k).strip()]
    if not cleaned:
        return {
            "error": "At least one non-empty keyword is required.",
        }
    data = _load_alerts()
    watches: List[Dict[str, Any]] = data.get("news_watches") or []
    watches.append(asdict(NewsWatchRule(keywords=cleaned)))
    data["news_watches"] = watches
    _save_alerts(data)
    return {
        "status": "ok",
        "message": "News watch registered.",
        "rule": watches[-1],
    }


def list_alerts() -> Dict[str, Any]:
    data = _load_alerts()
    return data


def check_alerts(
    *,
    get_mutual_fund_nav_func,
    get_stock_news_func,
) -> Dict[str, Any]:
    """
    Evaluate all alert rules once using the provided tool functions.

    This function deliberately receives callables instead of importing
    tools directly, so it stays decoupled from tool modules.
    """
    data = _load_alerts()
    triggered: Dict[str, List[Dict[str, Any]]] = {
        "nav_alerts": [],
        "news_watches": [],
    }

    # NAV alerts: use daily change_percent from mutual fund tool response.
    for raw in data.get("nav_alerts") or []:
        scheme_code = str(raw.get("scheme_code") or "").strip()
        try:
            threshold = float(raw.get("threshold_drop_percent") or 0.0)
        except Exception:
            threshold = 0.0
        if not scheme_code or threshold <= 0:
            continue
        mf = get_mutual_fund_nav_func(scheme_code)
        if not isinstance(mf, dict):
            continue
        change_pct = mf.get("change_percent")
        if isinstance(change_pct, (int, float)) and change_pct <= -threshold:
            triggered["nav_alerts"].append(
                {
                    "scheme_code": scheme_code,
                    "threshold_drop_percent": threshold,
                    "latest_change_percent": change_pct,
                    "message": (
                        f"Scheme {scheme_code} fell by {change_pct}% today, "
                        f"breaching your alert threshold of {threshold}%."
                    ),
                }
            )

    # News watches: very lightweight sentiment scan via existing stock news tool.
    # We simply look for the presence of any recent headline; the LLM can
    # interpret sentiment further.
    for raw in data.get("news_watches") or []:
        keywords = raw.get("keywords") or []
        if not isinstance(keywords, list) or not keywords:
            continue
        joined = " ".join(str(k) for k in keywords)
        news = get_stock_news_func(joined)
        if not isinstance(news, dict):
            continue
        articles = news.get("articles") or []
        if articles:
            triggered["news_watches"].append(
                {
                    "keywords": keywords,
                    "article_count": len(articles),
                    "sample_headlines": [a.get("title") for a in articles[:3] if isinstance(a, dict)],
                }
            )

    return {
        "alerts": data,
        "triggered": triggered,
    }

