"""
IPO & SME tools for Bharat FinanceMCP (Phase 4).

Data sources:
- Upcoming IPOs: chittorgarh.com
- Grey Market Premium (GMP): investorgain.com
- Live subscription: chittorgarh.com

The implementation:
- Uses httpx with a realistic desktop Chrome User-Agent
- Disables SSL verification (verify=False) to avoid common local SSL issues
- Uses BeautifulSoup4 with the lxml parser
- Wraps all scraping in try/except and returns clean error messages instead of
  raising exceptions
- Applies light fuzzy matching for ipo_name so minor typos still resolve
"""

from __future__ import annotations

import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

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
HTTP_TIMEOUT = 20.0

# Chittorgarh main IPO list (includes SME when scrolling)
IPO_LIST_URL = "https://www.chittorgarh.com/ipo/ipo_list.asp"
# Live subscription report
SUBSCRIPTION_URL = "https://www.chittorgarh.com/report/live-ipo-subscription-status/71/"
# Investorgain live GMP report
GMP_URL = "https://www.investorgain.com/report/live-ipo-gmp/331/"


def _safe_get(url: str, params: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Perform a resilient HTTP GET using httpx.

    - Adds realistic User-Agent
    - verify=False to avoid local SSL issues
    - Returns response text or None on any error
    """
    try:
        with httpx.Client(
            headers=COMMON_HEADERS,
            timeout=HTTP_TIMEOUT,
            verify=False,  # Local dev often has SSL issues; disable validation here.
        ) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.text
    except Exception:
        return None


def _make_soup(html: str) -> Optional[BeautifulSoup]:
    try:
        return BeautifulSoup(html, "lxml")
    except Exception:
        return None


def _fuzzy_match(target: str, candidates: List[str]) -> Tuple[Optional[str], float]:
    """
    Return the best fuzzy match (candidate, score) for target, or (None, 0.0).
    """
    target_clean = (target or "").strip().lower()
    if not target_clean or not candidates:
        return None, 0.0

    best_name: Optional[str] = None
    best_score = 0.0
    for cand in candidates:
        c = (cand or "").strip().lower()
        if not c:
            continue
        # Prefer substring matches
        if target_clean in c:
            score = 1.0
        else:
            score = SequenceMatcher(None, target_clean, c).ratio()
        if score > best_score:
            best_score = score
            best_name = cand
    return best_name, best_score


def _to_table(columns: List[str], rows: List[List[Any]]) -> Dict[str, Any]:
    """
    Simple table structure consumable by AI tools.
    """
    return {
        "columns": columns,
        "rows": rows,
    }


def _extract_ipo_detail(url: str, name: str) -> Optional[Dict[str, Any]]:
    """
    Parse a single Chittorgarh IPO detail page and extract key fields.
    """
    html = _safe_get(url)
    if not html:
        return None
    soup = _make_soup(html)
    if soup is None:
        return None

    text = soup.get_text(" ", strip=False)

    def _date_after(label: str) -> str:
        pattern = rf"{label}\s*([A-Za-z]+,\s+[A-Za-z]+\s+\d+,\s+\d{{4}})"
        m = re.search(pattern, text)
        return m.group(1).strip() if m else "N/A"

    open_date = _date_after("IPO Open")
    close_date = _date_after("IPO Close")

    price_match = re.search(
        r"Price Band[^\d]*(?:[\u20b9₹]?\s*)?(\d[\d,]*)\s*to\s*(?:[\u20b9₹]?\s*)?(\d[\d,]*)",
        text,
        re.IGNORECASE,
    )
    if not price_match:
        price_match = re.search(r"(\d{3,5})\s*to\s*(\d{3,5})", text)
    price_band = (
        f"{price_match.group(1)} to {price_match.group(2)}"
        if price_match
        else "N/A"
    )

    lot_match = re.search(
        r"(?:Market Lot|Lot Size)\s*[:\s]+([\d,]+)", text, re.IGNORECASE
    )
    lot_size = lot_match.group(1).strip() if lot_match else "N/A"

    issue_match = re.search(
        r"Issue Size[^\d]*(?:[\u20b9₹]?\s*)?([\d.,]+)\s*(?:Cr|Crore|Crores?)",
        text,
        re.IGNORECASE,
    )
    issue_size = issue_match.group(1).strip() + " Cr" if issue_match else "N/A"

    listing_match = re.search(
        r"Listing Date\s*([A-Za-z]+,\s+[A-Za-z]+\s+\d+,\s+\d{4})",
        text,
    )
    listing_date = listing_match.group(1).strip() if listing_match else "N/A"

    subscription_status = "N/A"
    try:
        if open_date != "N/A" and close_date != "N/A":
            fmt = "%a, %b %d, %Y"
            open_dt = datetime.strptime(open_date, fmt).date()
            close_dt = datetime.strptime(close_date, fmt).date()
            today = datetime.utcnow().date()
            if today < open_dt:
                subscription_status = "upcoming"
            elif open_dt <= today <= close_dt:
                subscription_status = "open"
            else:
                subscription_status = "closed"
    except Exception:
        subscription_status = "N/A"

    return {
        "name": name,
        "open_date": open_date,
        "close_date": close_date,
        "price_band": price_band,
        "lot_size": lot_size,
        "issue_size": issue_size,
        "listing_date": listing_date,
        "subscription_status": subscription_status,
    }


def get_upcoming_ipos() -> Dict[str, Any]:
    """
    Fetch a list of upcoming Mainboard and SME IPOs.

    Returns:
        {
          "table": {columns, rows},
          "items": [raw dicts],
        }
        or {"error": "..."} on failure.
    """
    html = _safe_get(IPO_LIST_URL)
    if not html:
        return {
            "error": "IPO data currently unavailable.",
            "source": IPO_LIST_URL,
        }

    soup = _make_soup(html)
    if soup is None:
        return {
            "error": "IPO data currently unavailable.",
            "source": IPO_LIST_URL,
        }

    ipo_links: List[Tuple[str, str]] = []
    seen: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if ("chittorgarh.com/ipo/" in href or (href.startswith("/ipo/") and "-ipo/" in href)):
            if "/ipo/ipo_" in href or "ipo_list" in href:
                continue
            url = href if href.startswith("http") else f"https://www.chittorgarh.com{href}"
            if url in seen:
                continue
            name = a.get_text(strip=True)
            if not name or "ipo" not in name.lower():
                continue
            seen.add(url)
            ipo_links.append((name, url))

    if not ipo_links:
        return {
            "error": "IPO list could not be parsed.",
            "source": IPO_LIST_URL,
        }

    items: List[Dict[str, Any]] = []
    for name, url in ipo_links[:20]:
        data = _extract_ipo_detail(url, name)
        if data:
            items.append(data)

    if not items:
        return {
            "error": "IPO detail pages could not be parsed.",
            "source": IPO_LIST_URL,
        }

    columns = ["Company", "Open Date", "Close Date", "Price Band", "Lot Size", "Issue Size", "Listing Date", "Status"]
    rows = [
        [
            it.get("name"),
            it.get("open_date"),
            it.get("close_date"),
            it.get("price_band"),
            it.get("lot_size"),
            it.get("issue_size"),
            it.get("listing_date"),
            it.get("subscription_status"),
        ]
        for it in items
    ]

    return {
        "table": _to_table(columns, rows),
        "items": items,
    }


def get_ipo_gmp(ipo_name: str) -> Dict[str, Any]:
    """
    Fetch current Grey Market Premium (GMP) for a specific IPO.

    Uses investorgain.com and fuzzy-matches ipo_name.
    """
    html = _safe_get(GMP_URL)
    if not html:
        return {
            "error": "GMP data currently unavailable.",
            "source": GMP_URL,
        }

    soup = _make_soup(html)
    if soup is None:
        return {
            "error": "GMP data currently unavailable.",
            "source": GMP_URL,
        }

    tables = soup.find_all("table")
    target = None
    for table in tables:
        header = table.find("tr")
        if not header:
            continue
        headers = [th.get_text(strip=True).lower() for th in header.find_all("th")]
        header_text = " ".join(headers)
        if "ipo" in header_text and "gmp" in header_text:
            target = table
            break

    if target is None:
        return {
            "error": "GMP data currently unavailable.",
            "source": GMP_URL,
        }

    rows_html = target.find_all("tr")[1:]
    rows: List[Dict[str, Any]] = []

    for row in rows_html:
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        try:
            name_text = cols[0].get_text(strip=True)
            gmp_text = cols[1].get_text(" ", strip=True)
            issue_text = cols[2].get_text(" ", strip=True)
            updated_text = cols[-1].get_text(" ", strip=True)

            name_clean = name_text.replace("IPO", "").strip()

            gmp_price = 0.0
            gmp_match = re.search(r"([+-]?\d+(?:\.\d+)?)", gmp_text)
            if gmp_match:
                gmp_price = float(gmp_match.group(1))

            issue_price = 0.0
            issue_match = re.search(r"(\d+(?:\.\d+)?)", issue_text.replace(",", ""))
            if issue_match:
                issue_price = float(issue_match.group(1))

            estimated_listing = issue_price + gmp_price if issue_price else 0.0
            gmp_percent = (
                round((gmp_price / issue_price) * 100, 2) if issue_price else 0.0
            )

            rows.append(
                {
                    "ipo_name": name_clean,
                    "gmp_price": gmp_price,
                    "gmp_percent": gmp_percent,
                    "issue_price": issue_price,
                    "estimated_listing": estimated_listing,
                    "last_updated": updated_text or "N/A",
                }
            )
        except Exception:
            continue

    if not rows:
        return {
            "error": "GMP data currently unavailable.",
            "source": GMP_URL,
        }

    names = [r["ipo_name"] for r in rows]
    best_name, score = _fuzzy_match(ipo_name, names)
    if not best_name or score < 0.5:
        return {
            "error": f"No close GMP match found for '{ipo_name}'.",
            "candidates": sorted(names)[:10],
        }

    best = next(r for r in rows if r["ipo_name"] == best_name)

    table = _to_table(
        ["IPO", "GMP (₹)", "GMP (%)", "Issue Price (₹)", "Est. Listing (₹)", "Last Updated"],
        [[
            best["ipo_name"],
            best["gmp_price"],
            best["gmp_percent"],
            best["issue_price"],
            best["estimated_listing"],
            best["last_updated"],
        ]],
    )

    return {
        "match": best,
        "match_score": round(score, 3),
        "table": table,
    }


def get_ipo_subscription(ipo_name: str) -> Dict[str, Any]:
    """
    Fetch live IPO subscription data (QIB, NII, Retail) from chittorgarh.com.

    Uses fuzzy matching on ipo_name to select the closest issue.
    """
    html = _safe_get(SUBSCRIPTION_URL)
    if not html:
        return {
            "error": "Subscription data currently unavailable.",
            "source": SUBSCRIPTION_URL,
        }

    soup = _make_soup(html)
    if soup is None:
        return {
            "error": "Subscription data currently unavailable.",
            "source": SUBSCRIPTION_URL,
        }

    # On Chittorgarh, the live IPO subscription section typically uses
    # a Bootstrap-style striped table. Prefer those first so we bind to
    # the "Live IPO" data block instead of any other summary tables.
    tables = soup.find_all("table")
    target = None
    for table in tables:
        classes = table.get("class") or []
        if "table-striped" not in classes:
            # Skip non-striped tables; live IPO table usually has this class.
            continue
        header = table.find("tr")
        if not header:
            continue
        headers = [th.get_text(strip=True).lower() for th in header.find_all("th")]
        header_text = " ".join(headers)
        if "issue name" in header_text and "qib" in header_text and "retail" in header_text:
            target = table
            break

    if target is None:
        return {
            "error": "Subscription data currently unavailable.",
            "source": SUBSCRIPTION_URL,
        }

    rows_html = target.find_all("tr")[1:]
    issues: List[Dict[str, Any]] = []

    for row in rows_html:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue
        try:
            name = cols[0].get_text(" ", strip=True)
            qib = cols[1].get_text(" ", strip=True)
            nii = cols[2].get_text(" ", strip=True)
            retail = cols[3].get_text(" ", strip=True)
            total = cols[4].get_text(" ", strip=True)

            issues.append(
                {
                    "ipo_name": name,
                    "qib": qib,
                    "nii": nii,
                    "retail": retail,
                    "total": total,
                }
            )
        except Exception:
            continue

    if not issues:
        return {
            "error": "Subscription data currently unavailable.",
            "source": SUBSCRIPTION_URL,
        }

    names = [i["ipo_name"] for i in issues]
    best_name, score = _fuzzy_match(ipo_name, names)
    if not best_name or score < 0.5:
        return {
            "error": f"No close subscription match found for '{ipo_name}'.",
            "candidates": sorted(names)[:10],
        }

    best = next(i for i in issues if i["ipo_name"] == best_name)

    table = _to_table(
        ["IPO", "QIB", "NII", "Retail", "Total"],
        [[best["ipo_name"], best["qib"], best["nii"], best["retail"], best["total"]]],
    )

    return {
        "match": best,
        "match_score": round(score, 3),
        "table": table,
    }

