"""
Simple in-memory rate limiting utilities.
"""

import functools
import time
from typing import Any, Callable, TypeVar, ParamSpec


F = TypeVar("F", bound=Callable[..., Any])
P = ParamSpec("P")


def rate_limit(calls_per_minute: int = 60) -> Callable[[F], F]:
    """
    Decorator to limit how often a function can be called.

    If the limit is exceeded, returns a dict with an error message
    instead of raising an exception. This keeps FastAPI handlers
    returning meaningful JSON errors instead of 500s.
    """

    window_seconds = 60

    def decorator(func: F) -> F:
        calls: list[float] = []

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs):
            nonlocal calls
            now = time.time()
            # Drop calls older than window
            calls = [ts for ts in calls if now - ts < window_seconds]
            if len(calls) >= calls_per_minute:
                return {
                    "error": "Rate limit exceeded. Please try again later.",
                }
            calls.append(now)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator

