"""
Tax calculators for Bharat FinanceMCP (Phase 6).

Currently implements:
- calculate_indian_tax(...) – simple capital-gains estimation for retail investors.

The aim is not to be a full-fledged tax engine but to give the AI a
transparent, well-explained estimate that can be refined with a human
tax advisor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional

from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


AssetType = Literal["equity", "equity_mf", "debt_mf", "gold"]


DEFAULT_DEBT_SLAB_RATE_PERCENT = 30.0


@dataclass
class HoldingPeriod:
    days: int
    months: int
    label: Literal["short_term", "long_term"]
    start_date: str
    end_date: str


def _format_inr(amount: float | int | None) -> str:
    """
    Format a number as Indian Rupee with lakh/crore-style grouping.

    Example:
        1234567.8 -> "₹ 12,34,567.80"
    """
    if amount is None:
        return "₹ 0.00"

    negative = amount < 0
    value = abs(float(amount))
    integer_part = int(value)
    decimal_part = f"{value:.2f}".split(".")[1]

    s = str(integer_part)
    if len(s) <= 3:
        grouped = s
    else:
        # Last 3 digits stay together, the rest are grouped in 2s.
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts + [last3])

    prefix = "-₹ " if negative else "₹ "
    return f"{prefix}{grouped}.{decimal_part}"


def _parse_dates(buy_date: str, sell_date: str) -> HoldingPeriod:
    """
    Parse input dates and compute an approximate holding period.

    Uses dateutil to be forgiving about date formats while still giving
    month-accurate holding periods for tax classification.
    """
    start = date_parser.parse(buy_date).date()
    end = date_parser.parse(sell_date).date()
    if end < start:
        start, end = end, start

    delta_days = (end - start).days
    rel = relativedelta(end, start)
    months = rel.years * 12 + rel.months
    label: Literal["short_term", "long_term"] = "long_term" if months >= 12 else "short_term"

    return HoldingPeriod(
        days=delta_days,
        months=months,
        label=label,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
    )


def _normalise_asset_type(asset_type: str) -> str:
    t = (asset_type or "").strip().lower()
    if t in {"equity", "share", "stock", "stocks", "eq"}:
        return "equity"
    if t in {"equity_mf", "equity-mf", "equity mf", "equity mutual fund", "equityfund"}:
        return "equity_mf"
    if t in {"debt", "debt_mf", "debt-mf", "debt mf", "debt mutual fund"}:
        return "debt_mf"
    if t in {"gold", "sov_gold_bond", "sbg", "etf_gold", "gold_etf"}:
        return "gold"
    # Fallback – treat unknown as equity for safety but mark it.
    return t or "equity"


def calculate_indian_tax(
    asset_type: str,
    buy_price: float,
    sell_price: float,
    buy_date: str,
    sell_date: str,
) -> Dict[str, Any]:
    """
    Estimate Indian capital-gains tax for a simple buy/sell transaction.

    Rules implemented:
    - For Equity / Equity Mutual Funds:
        * Short-term (< 12 months): 20% on full gains (no basic exemption logic).
        * Long-term (>= 12 months): 12.5% on gains exceeding ₹1.25 lakh.
    - For Debt Mutual Funds / Gold:
        * Recent budgets tax capital gains at the investor's slab rate
          regardless of holding period (no indexation here).
          This tool assumes a default slab rate of 30% unless changed in code.

    This is a simplified calculator for educational / planning purposes only
    and is **not** a replacement for professional tax advice.
    """
    norm_type = _normalise_asset_type(asset_type)
    hp = _parse_dates(buy_date, sell_date)

    gain = float(sell_price) - float(buy_price)
    is_profit = gain > 0

    if not is_profit:
        tax_liability = 0.0
        taxable_gain = 0.0
        tax_rate_percent: Optional[float] = None
        regime_note = "No tax – this transaction results in a loss or no gain."
    else:
        tax_rate_percent = 0.0
        taxable_gain = gain
        regime_note = ""

        if norm_type in {"equity", "equity_mf"}:
            if hp.label == "short_term":
                tax_rate_percent = 20.0
                taxable_gain = gain
                regime_note = (
                    "Short-term capital gains on equity / equity mutual funds "
                    "assumed at 20% flat for this calculator."
                )
            else:
                tax_rate_percent = 12.5
                exemption = 125000.0
                taxable_gain = max(0.0, gain - exemption)
                regime_note = (
                    "Long-term capital gains on equity / equity mutual funds "
                    "assumed at 12.5% on gains above ₹1.25 lakh."
                )
        elif norm_type in {"debt_mf", "gold"}:
            tax_rate_percent = DEFAULT_DEBT_SLAB_RATE_PERCENT
            taxable_gain = gain
            regime_note = (
                "Debt funds / gold are taxed at the investor's income slab rate; "
                "this tool assumes a default slab rate of "
                f"{DEFAULT_DEBT_SLAB_RATE_PERCENT:.1f}% for estimation."
            )
        else:
            tax_rate_percent = 20.0
            taxable_gain = gain
            regime_note = (
                "Unknown asset type – treating gains as short-term at 20% "
                "for a conservative rough estimate."
            )

        tax_liability = round(taxable_gain * (tax_rate_percent / 100.0), 2)

    result: Dict[str, Any] = {
        "asset_type_input": asset_type,
        "asset_type_normalised": norm_type,
        "buy_price": float(buy_price),
        "sell_price": float(sell_price),
        "gain": round(gain, 2),
        "is_profit": is_profit,
        "holding_period": {
            "days": hp.days,
            "approx_months": hp.months,
            "label": hp.label,
            "from": hp.start_date,
            "to": hp.end_date,
        },
        "tax_regime_note": regime_note,
        "taxable_gain": round(taxable_gain, 2),
        "tax_rate_percent": tax_rate_percent,
        "estimated_tax_liability": tax_liability,
        "formatted": {
            "gain_inr": _format_inr(gain),
            "tax_liability_inr": _format_inr(tax_liability),
        },
    }

    result["table"] = {
        "columns": ["Metric", "Value"],
        "rows": [
            ["Asset Type (normalised)", result["asset_type_normalised"]],
            ["Holding Period (days)", hp.days],
            ["Holding Period (approx. months)", hp.months],
            ["Holding Classification", hp.label.replace("_", " ").title()],
            ["Buy Price", _format_inr(buy_price)],
            ["Sell Price", _format_inr(sell_price)],
            ["Gain / Loss", _format_inr(gain)],
            ["Taxable Gain", _format_inr(taxable_gain)],
            [
                "Estimated Tax Liability",
                _format_inr(tax_liability),
            ],
        ],
    }

    return result


def sip_required_for_target(
    target_amount: float,
    years: int,
    expected_return: float,
) -> Dict[str, Any]:
    """
    Given a target corpus, horizon, and expected annual return, compute
    the monthly SIP required using the standard SIP future-value formula.

    FV = P * [((1 + r)^n - 1) / r] * (1 + r)

    where:
        FV = target_amount
        P  = required monthly investment
        r  = monthly rate = expected_return / 12 / 100
        n  = years * 12
    """
    FV = float(target_amount)
    n = int(years) * 12
    r = float(expected_return) / 12.0 / 100.0

    if FV <= 0 or n <= 0:
        required = 0.0
    elif r == 0:
        # No growth assumption: simple division.
        required = FV / n
    else:
        factor = ((1 + r) ** n - 1.0) / r * (1 + r)
        if factor <= 0:
            required = 0.0
        else:
            required = FV / factor

    return {
        "target_amount": round(FV, 2),
        "years": int(years),
        "expected_return": float(expected_return),
        "required_monthly_investment": round(required, 2),
    }

