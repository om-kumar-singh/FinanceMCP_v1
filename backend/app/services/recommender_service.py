"""
Backend wrapper for the rule-based recommender in src/utils/recommender.py.

This module exists so backend code can simply import
`generate_resilience_recommendations` without worrying about Python paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import sys

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))

from src.utils.recommender import generate_recommendations  # type: ignore  # noqa: E402


def generate_resilience_recommendations(
    profile: Dict[str, Any] | None,
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Thin wrapper that forwards to the shared recommender module.
    """
    return generate_recommendations(profile or {}, metrics)

