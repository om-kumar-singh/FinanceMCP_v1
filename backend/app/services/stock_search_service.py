"""
Stock search and symbol resolution service.
"""

from __future__ import annotations

import io
import logging
from difflib import SequenceMatcher
from typing import Any

import pandas as pd
import requests

from app.utils.cache import cacheable

logger = logging.getLogger(__name__)

NSE_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

STOCK_DATABASE: list[dict[str, Any]] = []
SYMBOL_INDEX: dict[str, list[dict[str, Any]]] = {}


# Popular NSE symbols for default suggestions
POPULAR_SYMBOLS: list[str] = [
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
    "TATAMOTORS.NS",
    "WIPRO.NS",
    "AXISBANK.NS",
    "LT.NS",
    "MARUTI.NS",
    "BAJFINANCE.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "ZOMATO.NS",
    "ADANIENT.NS",
]


FALLBACK_STOCKS: list[dict[str, str]] = [
    {"symbol": "RELIANCE.NS", "company_name": "Reliance Industries Limited", "display_symbol": "RELIANCE"},
    {"symbol": "TCS.NS", "company_name": "Tata Consultancy Services Limited", "display_symbol": "TCS"},
    {"symbol": "HDFCBANK.NS", "company_name": "HDFC Bank Limited", "display_symbol": "HDFCBANK"},
    {"symbol": "INFY.NS", "company_name": "Infosys Limited", "display_symbol": "INFY"},
    {"symbol": "ICICIBANK.NS", "company_name": "ICICI Bank Limited", "display_symbol": "ICICIBANK"},
    {"symbol": "HINDUNILVR.NS", "company_name": "Hindustan Unilever Limited", "display_symbol": "HINDUNILVR"},
    {"symbol": "ITC.NS", "company_name": "ITC Limited", "display_symbol": "ITC"},
    {"symbol": "SBIN.NS", "company_name": "State Bank of India", "display_symbol": "SBIN"},
    {"symbol": "BHARTIARTL.NS", "company_name": "Bharti Airtel Limited", "display_symbol": "BHARTIARTL"},
    {"symbol": "KOTAKBANK.NS", "company_name": "Kotak Mahindra Bank Limited", "display_symbol": "KOTAKBANK"},
    {"symbol": "BAJFINANCE.NS", "company_name": "Bajaj Finance Limited", "display_symbol": "BAJFINANCE"},
    {"symbol": "WIPRO.NS", "company_name": "Wipro Limited", "display_symbol": "WIPRO"},
    {"symbol": "AXISBANK.NS", "company_name": "Axis Bank Limited", "display_symbol": "AXISBANK"},
    {"symbol": "ASIANPAINT.NS", "company_name": "Asian Paints Limited", "display_symbol": "ASIANPAINT"},
    {"symbol": "MARUTI.NS", "company_name": "Maruti Suzuki India Limited", "display_symbol": "MARUTI"},
    {"symbol": "TATAMOTORS.NS", "company_name": "Tata Motors Limited", "display_symbol": "TATAMOTORS"},
    {"symbol": "LT.NS", "company_name": "Larsen & Toubro Limited", "display_symbol": "LT"},
    {"symbol": "SUNPHARMA.NS", "company_name": "Sun Pharmaceutical Industries Limited", "display_symbol": "SUNPHARMA"},
    {"symbol": "TITAN.NS", "company_name": "Titan Company Limited", "display_symbol": "TITAN"},
    {"symbol": "ULTRACEMCO.NS", "company_name": "UltraTech Cement Limited", "display_symbol": "ULTRACEMCO"},
    {"symbol": "NESTLEIND.NS", "company_name": "Nestle India Limited", "display_symbol": "NESTLEIND"},
    {"symbol": "TATASTEEL.NS", "company_name": "Tata Steel Limited", "display_symbol": "TATASTEEL"},
    {"symbol": "JSWSTEEL.NS", "company_name": "JSW Steel Limited", "display_symbol": "JSWSTEEL"},
    {"symbol": "ZOMATO.NS", "company_name": "Zomato Limited", "display_symbol": "ZOMATO"},
    {"symbol": "ADANIENT.NS", "company_name": "Adani Enterprises Limited", "display_symbol": "ADANIENT"},
    {"symbol": "DRREDDY.NS", "company_name": "Dr. Reddys Laboratories Limited", "display_symbol": "DRREDDY"},
    {"symbol": "CIPLA.NS", "company_name": "Cipla Limited", "display_symbol": "CIPLA"},
    {"symbol": "ONGC.NS", "company_name": "Oil and Natural Gas Corporation Limited", "display_symbol": "ONGC"},
    {"symbol": "POWERGRID.NS", "company_name": "Power Grid Corporation of India Limited", "display_symbol": "POWERGRID"},
    {"symbol": "NTPC.NS", "company_name": "NTPC Limited", "display_symbol": "NTPC"},
    {"symbol": "COALINDIA.NS", "company_name": "Coal India Limited", "display_symbol": "COALINDIA"},
    {"symbol": "HINDALCO.NS", "company_name": "Hindalco Industries Limited", "display_symbol": "HINDALCO"},
    {"symbol": "VEDL.NS", "company_name": "Vedanta Limited", "display_symbol": "VEDL"},
    {"symbol": "HCLTECH.NS", "company_name": "HCL Technologies Limited", "display_symbol": "HCLTECH"},
    {"symbol": "TECHM.NS", "company_name": "Tech Mahindra Limited", "display_symbol": "TECHM"},
    {"symbol": "M&M.NS", "company_name": "Mahindra and Mahindra Limited", "display_symbol": "M&M"},
    {"symbol": "BAJAJ-AUTO.NS", "company_name": "Bajaj Auto Limited", "display_symbol": "BAJAJ-AUTO"},
    {"symbol": "HEROMOTOCO.NS", "company_name": "Hero MotoCorp Limited", "display_symbol": "HEROMOTOCO"},
    {"symbol": "EICHERMOT.NS", "company_name": "Eicher Motors Limited", "display_symbol": "EICHERMOT"},
    {"symbol": "INDIGO.NS", "company_name": "InterGlobe Aviation Limited", "display_symbol": "INDIGO"},
    {"symbol": "PAYTM.NS", "company_name": "One97 Communications Limited", "display_symbol": "PAYTM"},
    {"symbol": "NYKAA.NS", "company_name": "FSN E-Commerce Ventures Limited", "display_symbol": "NYKAA"},
    {"symbol": "DELHIVERY.NS", "company_name": "Delhivery Limited", "display_symbol": "DELHIVERY"},
    {"symbol": "POLICYBZR.NS", "company_name": "PB Fintech Limited", "display_symbol": "POLICYBZR"},
    {"symbol": "DIVISLAB.NS", "company_name": "Divis Laboratories Limited", "display_symbol": "DIVISLAB"},
    {"symbol": "BAJAJFINSV.NS", "company_name": "Bajaj Finserv Limited", "display_symbol": "BAJAJFINSV"},
    {"symbol": "PERSISTENT.NS", "company_name": "Persistent Systems Limited", "display_symbol": "PERSISTENT"},
    {"symbol": "MPHASIS.NS", "company_name": "Mphasis Limited", "display_symbol": "MPHASIS"},
    {"symbol": "LTIM.NS", "company_name": "LTIMindtree Limited", "display_symbol": "LTIM"},
    {"symbol": "ADANIPORTS.NS", "company_name": "Adani Ports and Special Economic Zone Limited", "display_symbol": "ADANIPORTS"},
]


ALIAS_MAP: dict[str, list[str]] = {
    "reliance": ["RELIANCE.NS"],
    "ril": ["RELIANCE.NS"],
    "tata motors": ["TATAMOTORS.NS"],
    "hdfc bank": ["HDFCBANK.NS"],
    "hdfc": ["HDFCBANK.NS", "HDFC.NS"],
    "sbi": ["SBIN.NS"],
    "state bank": ["SBIN.NS"],
    "infosys": ["INFY.NS"],
    "infy": ["INFY.NS"],
    "wipro": ["WIPRO.NS"],
    "tcs": ["TCS.NS"],
    "tata consultancy": ["TCS.NS"],
    "airtel": ["BHARTIARTL.NS"],
    "bharti": ["BHARTIARTL.NS"],
    "itc": ["ITC.NS"],
    "ongc": ["ONGC.NS"],
    "ntpc": ["NTPC.NS"],
    "bajaj finance": ["BAJFINANCE.NS"],
    "bajaj": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "BAJAJHLDNG.NS"],
    "kotak": ["KOTAKBANK.NS"],
    "axis bank": ["AXISBANK.NS"],
    "icici": ["ICICIBANK.NS"],
    "maruti": ["MARUTI.NS"],
    "suzuki": ["MARUTI.NS"],
    "ultratech": ["ULTRACEMCO.NS"],
    "asian paints": ["ASIANPAINT.NS"],
    "titan": ["TITAN.NS"],
    "nestle": ["NESTLEIND.NS"],
    "hindustan unilever": ["HINDUNILVR.NS"],
    "hul": ["HINDUNILVR.NS"],
    "sun pharma": ["SUNPHARMA.NS"],
    "dr reddy": ["DRREDDY.NS"],
    "cipla": ["CIPLA.NS"],
    "divis": ["DIVISLAB.NS"],
    "lt": ["LT.NS"],
    "larsen": ["LT.NS"],
    "adani": ["ADANIENT.NS", "ADANIPORTS.NS", "ADANIGREEN.NS"],
    "power grid": ["POWERGRID.NS"],
    "coal india": ["COALINDIA.NS"],
    "jsw steel": ["JSWSTEEL.NS"],
    "tata steel": ["TATASTEEL.NS"],
    "hindalco": ["HINDALCO.NS"],
    "vedanta": ["VEDL.NS"],
    "m&m": ["M&M.NS"],
    "mahindra": ["M&M.NS"],
    "hero": ["HEROMOTOCO.NS"],
    "bajaj auto": ["BAJAJ-AUTO.NS"],
    "eicher": ["EICHERMOT.NS"],
    "royal enfield": ["EICHERMOT.NS"],
    "zomato": ["ZOMATO.NS"],
    "paytm": ["PAYTM.NS"],
    "nykaa": ["NYKAA.NS"],
    "policybazaar": ["POLICYBZR.NS"],
    "delhivery": ["DELHIVERY.NS"],
    "indigo": ["INDIGO.NS"],
    "interglobe": ["INDIGO.NS"],
    "hcl": ["HCLTECH.NS"],
    "tech mahindra": ["TECHM.NS"],
    "mphasis": ["MPHASIS.NS"],
    "persistent": ["PERSISTENT.NS"],
    "ltimindtree": ["LTIM.NS"],
    "mindtree": ["LTIM.NS"],
}


@cacheable(ttl_seconds=86400)
def _fetch_nse_equity_list() -> list[dict[str, Any]] | None:
    try:
        resp = requests.get(NSE_CSV_URL, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        logger.warning("Failed to download NSE equity CSV.", exc_info=True)
        return None

    try:
        df = pd.read_csv(io.StringIO(resp.text))
    except Exception:
        logger.warning("Failed to parse NSE equity CSV.", exc_info=True)
        return None

    records: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        symbol = str(row.get("SYMBOL") or "").strip().upper()
        name = str(row.get("NAME OF COMPANY") or "").strip()
        series = str(row.get("SERIES") or "").strip().upper()
        isin = str(row.get("ISIN NUMBER") or "").strip().upper()
        if not symbol or not name:
            continue
        yf_symbol = f"{symbol}.NS"
        record = {
            "symbol": yf_symbol,
            "display_symbol": symbol,
            "company_name": name,
            "short_name": symbol,
            "series": series,
            "isin": isin,
            "exchange": "NSE",
            "keywords": [symbol.lower(), name.lower()],
        }
        records.append(record)

    return records


def initialize_stock_database() -> None:
    """
    Load NSE stock database into memory. Safe to call multiple times.
    """
    global STOCK_DATABASE, SYMBOL_INDEX
    if STOCK_DATABASE:
        return

    records = _fetch_nse_equity_list()
    if not records:
        logger.warning("Using fallback stock list (50 stocks). NSE CSV unavailable.")
        records = []
        for item in FALLBACK_STOCKS:
            records.append(
                {
                    "symbol": item["symbol"],
                    "display_symbol": item["display_symbol"],
                    "company_name": item["company_name"],
                    "short_name": item["display_symbol"],
                    "series": "EQ",
                    "isin": "",
                    "exchange": "NSE",
                    "keywords": [
                        item["display_symbol"].lower(),
                        item["company_name"].lower(),
                    ],
                }
            )

    # Apply aliases as keywords
    symbol_to_record: dict[str, dict[str, Any]] = {r["symbol"]: r for r in records}

    for alias, symbols in ALIAS_MAP.items():
        for sym in symbols:
            rec = symbol_to_record.get(sym)
            if not rec:
                continue
            kws = rec.setdefault("keywords", [])
            if alias not in kws:
                kws.append(alias)

    STOCK_DATABASE = list(symbol_to_record.values())

    # Build index by first letter of display_symbol
    SYMBOL_INDEX = {}
    for rec in STOCK_DATABASE:
        display = rec.get("display_symbol", "")
        if not display:
            continue
        first = display[0].upper()
        SYMBOL_INDEX.setdefault(first, []).append(rec)

    logger.info("NSE Stock Database loaded: %s stocks", len(STOCK_DATABASE))


def _ensure_loaded() -> None:
    if not STOCK_DATABASE:
        initialize_stock_database()


def _score_match(query: str, record: dict[str, Any]) -> tuple[int, str]:
    q = query.lower().strip()
    if not q:
        return 0, ""

    disp = str(record.get("display_symbol", "")).upper()
    name = str(record.get("company_name", "")).lower()
    symbol = str(record.get("symbol", "")).upper()
    keywords = [str(k).lower() for k in record.get("keywords", [])]

    # 1. Exact symbol match (without suffix)
    if q == symbol or q == disp:
        return 100, "symbol_exact"

    # 2. Exact company name match
    if q == name:
        return 90, "name_exact"

    # 3. Startswith
    if disp.lower().startswith(q) or name.startswith(q):
        return 80, "startswith"

    # 4. Keyword/alias match
    if q in keywords:
        return 75, "keyword"

    # 5. Contains query in name or symbol
    if q in name or q in disp.lower():
        return 60, "contains"

    # 6. Fuzzy match (handle minor typos)
    ratio_name = SequenceMatcher(None, q, name[: len(q) + 5]).ratio() if name else 0.0
    ratio_sym = SequenceMatcher(None, q.upper(), disp).ratio() if disp else 0.0
    ratio = max(ratio_name, ratio_sym)
    if ratio >= 0.7:
        return int(40 + ratio * 10), "fuzzy"

    return 0, ""


@cacheable(ttl_seconds=300)
def search_stocks(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Smart fuzzy search across all NSE stocks.
    """
    _ensure_loaded()
    q = (query or "").strip()
    if not q:
        return []

    # Use index by first letter of query for initial narrowing
    first = q[0].upper()
    candidates = SYMBOL_INDEX.get(first, STOCK_DATABASE)

    scored: list[dict[str, Any]] = []
    for rec in candidates:
        score, match_type = _score_match(q, rec)
        if score <= 0:
            continue
        item = {
            "symbol": rec["symbol"],
            "display_symbol": rec["display_symbol"],
            "company_name": rec["company_name"],
            "exchange": rec.get("exchange", "NSE"),
            "match_score": score,
            "match_type": match_type,
        }
        scored.append(item)

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]


def resolve_symbol(query: str) -> str | None:
    """
    Resolve a plain text query to a yfinance symbol.
    """
    if not query or not str(query).strip():
        return None

    q = str(query).strip()

    # 1. If already has .NS or .BO suffix, return as-is
    upper = q.upper()
    if upper.endswith(".NS") or upper.endswith(".BO"):
        return upper

    _ensure_loaded()

    # 2. Exact display symbol match (without suffix)
    for rec in STOCK_DATABASE:
        if upper == rec.get("display_symbol", "").upper():
            return rec["symbol"]

    # 3. Use search_stocks and trust top result if score good enough
    matches = search_stocks(q, limit=1)
    if matches:
        top = matches[0]
        if top.get("match_score", 0) > 50:
            return top["symbol"]

    # 4. Fallback: assume NSE symbol and validate basic pattern
    candidate = f"{upper}.NS"
    # Basic format check; we do not hit yfinance here to avoid latency
    if any(rec["symbol"] == candidate for rec in STOCK_DATABASE):
        return candidate

    return None


def get_popular_stocks() -> list[dict[str, Any]]:
    """
    Return list of popular/trending stocks for default suggestions.
    """
    _ensure_loaded()
    symbol_map = {rec["symbol"]: rec for rec in STOCK_DATABASE}
    results: list[dict[str, Any]] = []

    for sym in POPULAR_SYMBOLS:
        rec = symbol_map.get(sym)
        if not rec:
            continue
        results.append(
            {
                "symbol": rec["symbol"],
                "display_symbol": rec["display_symbol"],
                "company_name": rec["company_name"],
                "exchange": rec.get("exchange", "NSE"),
            }
        )

    return results

