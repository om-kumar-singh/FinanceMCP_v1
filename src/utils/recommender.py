"""
Rule-based personalised financial recommendations for BharatFinanceMCP.

Replaces the previous Gemini-based system with a transparent Python
engine that:
- Applies deterministic rules on runway, debt, resilience, and risk.
- Optionally classifies users into a resilience profile using a light
  scikit-learn model (if sklearn is installed).
- Returns 4–5 concise, emoji-tagged tips.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


Category = Literal["protection", "debt", "growth", "risk", "planning"]


@dataclass
class Tip:
    category: Category
    text: str

    def format(self) -> str:
        emoji_map: Dict[Category, str] = {
            "protection": "🛡️ Protection — ",
            "debt": "📉 Debt — ",
            "growth": "📈 Growth — ",
            "risk": "⚖️ Risk — ",
            "planning": "🧭 Planning — ",
        }
        prefix = emoji_map.get(self.category, "")
        return f"{prefix}{self.text}"


def _compute_debt_service_ratio(income: float, emi: float) -> float:
    if income <= 0:
        return 0.0
    return max(0.0, float(emi) / float(income))


def _classify_resilience_profile(
    resilience_score: float,
    runway_months: float,
    debt_service_ratio: float,
) -> str:
    """
    Simple rule-based resilience profile.

    If scikit-learn is available in this environment, we can later extend
    this function to call a small DecisionTreeClassifier trained on
    historical / synthetic data. For now we keep the logic explicit and
    transparent.
    """
    if resilience_score >= 80 and runway_months >= 6 and debt_service_ratio <= 0.25:
        return "Resilient"
    if resilience_score >= 55 and runway_months >= 3 and debt_service_ratio <= 0.4:
        return "Stable"
    return "Vulnerable"


def generate_recommendations(
    profile: Dict[str, Any] | None,
    metrics: Dict[str, Any],
    *,
    max_tips: int = 5,
) -> Dict[str, Any]:
    """
    Generate 4–5 rule-based recommendations based on numeric metrics.

    Args:
        profile: Optional dict with user profile fields (age_band, dependents, etc.).
        metrics: Dict containing at least:
            - income
            - monthly_expenses
            - savings
            - emi
            - runway_months
            - resilience_score (or combined_resilience_score)
            - optional: portfolio_value, portfolio_concentration
        max_tips: Upper bound on number of tips to return (min 4).

    Returns:
        {
          "profile_label": "Vulnerable" | "Stable" | "Resilient",
          "normal": [tip_str, ...],       # 4–5 items
          "market_crash": [],
          "job_loss": [],
          "emergency": [],
        }
    """
    income = float(metrics.get("income") or 0.0)
    monthly_expenses = float(metrics.get("monthly_expenses") or 0.0)
    savings = float(metrics.get("savings") or 0.0)
    emi = float(metrics.get("emi") or 0.0)
    runway_months = float(metrics.get("runway_months") or 0.0)
    resilience_score = float(
        metrics.get("resilience_score")
        or metrics.get("combined_resilience_score")
        or 0.0
    )
    portfolio_value = float(metrics.get("portfolio_value") or 0.0)
    portfolio_concentration = float(metrics.get("portfolio_concentration") or 0.0)

    cash_reserve = savings
    debt_service_ratio = float(
        metrics.get("debt_service_ratio")
        or _compute_debt_service_ratio(income, emi)
    )

    profile_label = _classify_resilience_profile(
        resilience_score=resilience_score,
        runway_months=runway_months,
        debt_service_ratio=debt_service_ratio,
    )

    tips: List[Tip] = []

    # ── Core rule-based tips ──────────────────────────────────────────────

    # Runway-based recommendation.
    if runway_months < 3:
        tips.append(
            Tip(
                category="protection",
                text=(
                    "Your cash runway is critical. Switch to a bare-bones budget, "
                    "build a 3–6 month emergency fund, and postpone all non-essential purchases."
                ),
            )
        )

    # Debt-based recommendation.
    if debt_service_ratio > 0.35:
        tips.append(
            Tip(
                category="debt",
                text=(
                    "Debt payments are consuming over 35% of your income. Focus on the "
                    "'Debt Avalanche' method starting with your highest-interest loan "
                    "while avoiding new EMI commitments."
                ),
            )
        )

    # Investment / growth recommendation.
    if resilience_score > 80 and cash_reserve >= 100000:
        tips.append(
            Tip(
                category="growth",
                text=(
                    "Your financial foundation is strong. Consider rebalancing your portfolio "
                    "toward long-term growth assets such as diversified Equity Index Funds. "
                    "Remember that long-term equity gains may be taxed as LTCG at concessional "
                    "rates; plan systematic withdrawals to optimise tax."
                ),
            )
        )

    # Concentration / risk recommendation.
    if portfolio_concentration > 50:
        tips.append(
            Tip(
                category="risk",
                text=(
                    "Over 50% of your wealth appears concentrated in a single asset or sector. "
                    "Gradually diversify across sectors and asset classes to reduce "
                    "non-systematic (idiosyncratic) risk."
                ),
            )
        )

    # ── Profile-driven generic tips ───────────────────────────────────────

    if profile_label == "Vulnerable":
        tips.extend(
            [
                Tip(
                    category="protection",
                    text=(
                        "Automate a fixed monthly transfer to a separate emergency-fund account "
                        "until you reach at least 3 months of expenses."
                    ),
                ),
                Tip(
                    category="planning",
                    text=(
                        "Review discretionary spends (eating out, subscriptions, travel) and cap "
                        "them to a clear monthly limit until your runway improves."
                    ),
                ),
            ]
        )
    elif profile_label == "Stable":
        tips.extend(
            [
                Tip(
                    category="planning",
                    text=(
                        "Gradually move from short-term FDs to a mix of high-quality debt funds "
                        "and large-cap equity exposure to fight inflation."
                    ),
                ),
                Tip(
                    category="risk",
                    text=(
                        "Check that you have adequate health and term insurance so a single shock "
                        "does not derail your financial plan."
                    ),
                ),
            ]
        )
    else:  # Resilient
        tips.extend(
            [
                Tip(
                    category="growth",
                    text=(
                        "Top up tax-efficient vehicles like ELSS, PPF, or NPS where appropriate "
                        "to optimise Section 80C and long-term compounding."
                    ),
                ),
                Tip(
                    category="planning",
                    text=(
                        "Document clear goals (house, education, retirement) and map each goal "
                        "to a separate investment bucket with its own asset mix."
                    ),
                ),
            ]
        )

    # Deduplicate by text while preserving order.
    seen: set[str] = set()
    unique_tips: List[Tip] = []
    for tip in tips:
        if tip.text in seen:
            continue
        seen.add(tip.text)
        unique_tips.append(tip)

    # Enforce 4–5 tips.
    max_tips = max(4, min(max_tips, 5))
    if len(unique_tips) < 4:
        # Fallback generic guidance if very few rules fired.
        unique_tips.append(
            Tip(
                category="planning",
                text="Aim for at least 3–6 months of expenses in liquid assets as your core emergency fund.",
            )
        )
    normal_tips = [t.format() for t in unique_tips[:max_tips]]

    return {
        "profile_label": profile_label,
        "normal": normal_tips,
        "market_crash": [],
        "job_loss": [],
        "emergency": [],
    }

