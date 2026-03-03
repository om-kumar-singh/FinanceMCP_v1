"""
Mutual fund NAV and SIP calculator services.
"""

import os

import requests

MF_API_BASE = os.getenv("MF_API_BASE_URL", "https://api.mfapi.in/mf")


def get_mutual_fund_nav(scheme_code: str) -> dict | None:
    """
    Fetch latest NAV for a mutual fund scheme.

    Args:
        scheme_code: Mutual fund scheme code (e.g., 119551)

    Returns:
        Dict with scheme_code, scheme_name, nav, date, or None on error.
    """
    if not scheme_code or not str(scheme_code).strip():
        return None

    scheme_code = str(scheme_code).strip()
    url = f"{MF_API_BASE}/{scheme_code}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    meta = data.get("meta")
    nav_data = data.get("data")

    if not meta or not nav_data:
        return None
    if not isinstance(nav_data, list) or len(nav_data) == 0:
        return None

    latest = nav_data[0]
    nav_str = latest.get("nav")
    date = latest.get("date")

    if not nav_str or not date:
        return None

    try:
        nav = float(nav_str)
    except (TypeError, ValueError):
        return None

    # Daily change (if we have at least 2 NAV points)
    change = None
    change_percent = None
    if len(nav_data) >= 2:
        prev = nav_data[1]
        prev_nav_str = prev.get("nav")
        try:
            prev_nav = float(prev_nav_str)
        except (TypeError, ValueError):
            prev_nav = None
        if prev_nav and prev_nav != 0:
            change = round(nav - prev_nav, 4)
            change_percent = round((change / prev_nav) * 100, 2)

    scheme_name = meta.get("scheme_name", "")
    code = meta.get("scheme_code", scheme_code)

    result: dict = {
        "scheme_code": str(code),
        "scheme_name": scheme_name,
        "nav": round(nav, 4),
        "date": date,
    }
    if change is not None and change_percent is not None:
        result["change"] = change
        result["change_percent"] = change_percent

    return result


def calculate_sip(
    monthly_investment: float,
    years: int,
    annual_return: float,
) -> dict:
    """
    Calculate SIP (Systematic Investment Plan) future value.

    Args:
        monthly_investment: Monthly investment amount (P)
        years: Investment period in years
        annual_return: Expected annual return percentage

    Returns:
        Dict with monthly_investment, years, annual_return, future_value
    """
    r = annual_return / 12 / 100
    n = years * 12

    if r <= 0:
        fv = monthly_investment * n
    else:
        fv = monthly_investment * ((1 + r) ** n - 1) / r * (1 + r)

    return {
        "monthly_investment": monthly_investment,
        "years": years,
        "annual_return": annual_return,
        "future_value": round(fv),
    }


def search_mutual_funds(query: str) -> list[dict] | None:
    """
    Search mutual funds by name or keyword using mfapi.in search API.

    Args:
        query: Search term (e.g., "hdfc tax saver").

    Returns:
        List of up to 10 dicts with scheme_code, scheme_name, fund_house, scheme_type.
        Returns empty list on no matches, or None on error.
    """
    if query is None:
        return []

    query_str = str(query).strip()
    if not query_str:
        return []

    url = f"{MF_API_BASE}/search"

    try:
        response = requests.get(url, params={"q": query_str}, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return None

    try:
        data = response.json()
    except ValueError:
        return None

    if not isinstance(data, list):
        return []

    results: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        code = item.get("schemeCode") or item.get("scheme_code")
        name = item.get("schemeName") or item.get("scheme_name")
        fund_house = item.get("fundHouse") or item.get("fund_house") or ""
        scheme_type = item.get("schemeType") or item.get("scheme_type") or ""
        if not code or not name:
            continue
        results.append(
            {
                "scheme_code": str(code),
                "scheme_name": name,
                "fund_house": fund_house,
                "scheme_type": scheme_type,
            }
        )
        if len(results) >= 10:
            break

    return results


def calculate_capital_gains(
    buy_price: float,
    sell_price: float,
    quantity: int,
    holding_days: int,
    asset_type: str = "equity",
) -> dict:
    """
    Calculate capital gains and tax for equity or debt instruments (Indian tax rules).

    Args:
        buy_price: Purchase price per unit.
        sell_price: Sell price per unit.
        quantity: Number of units.
        holding_days: Holding period in days.
        asset_type: "equity" or "debt".

    Returns:
        Dict with investment details, gains, tax, and net profit.
    """
    atype = (asset_type or "equity").strip().lower()
    if atype not in ("equity", "debt"):
        atype = "equity"

    total_investment = buy_price * quantity
    total_returns = sell_price * quantity
    profit_or_loss = total_returns - total_investment

    gain_type = "STCG" if holding_days < 365 else "LTCG"

    tax_rate = 0.0
    tax_amount = 0.0
    exemption_applied = 0.0
    tax_message = ""

    if atype == "equity":
        if profit_or_loss > 0:
            if gain_type == "STCG":
                # Short-term equity gains taxed at 20%
                tax_rate = 20.0
                tax_amount = round(profit_or_loss * 0.20, 2)
            else:
                # Long-term equity gains: first ₹1,25,000 exempt, rest at 12.5%
                exempt_limit = 125000.0
                exemption_applied = min(profit_or_loss, exempt_limit)
                taxable_gain = max(0.0, profit_or_loss - exempt_limit)
                if taxable_gain > 0:
                    tax_rate = 12.5
                    tax_amount = round(taxable_gain * 0.125, 2)
        # For losses or zero gains, no tax is applied
    else:
        # Debt mutual funds: gains taxed as per income tax slab
        tax_message = "Taxed as per your income tax slab"
        # Tax rate and amount depend on user's slab; we do not compute them here.
        tax_rate = 0.0
        tax_amount = 0.0

    net_profit_after_tax = profit_or_loss - tax_amount

    result: dict = {
        "buy_price": buy_price,
        "sell_price": sell_price,
        "quantity": quantity,
        "holding_days": holding_days,
        "asset_type": atype,
        "total_investment": total_investment,
        "total_returns": total_returns,
        "profit_or_loss": profit_or_loss,
        "gain_type": gain_type,
        "tax_amount": tax_amount,
        "tax_rate": tax_rate,
        "net_profit_after_tax": net_profit_after_tax,
        "exemption_applied": exemption_applied,
    }

    if tax_message:
        result["tax_message"] = tax_message

    return result
