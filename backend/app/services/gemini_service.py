"""
Gemini client for resilience recommendations.

Uses Google's Generative Language API to generate scenario-based
financial resilience recommendations from user profile + metrics.
Falls back to None on any error; caller must provide rule-based fallback.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests


DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL_NAME", "models/gemini-2.0-flash")
FALLBACK_GEMINI_MODELS = [
  "models/gemini-flash-latest",
  "models/gemini-2.0-flash",
  "models/gemini-2.5-flash",
]


def _safe_get_api_key() -> Optional[str]:
  key = os.getenv("GEMINI_API_KEY")
  if not key or not key.strip():
    return None
  return key.strip()


def _build_endpoint(model_name: str) -> str:
  return f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"


_RECOS_CACHE: Dict[str, tuple[float, Dict[str, List[str]]]] = {}
_RECOS_CACHE_TTL_SEC = int(os.getenv("GEMINI_RECOS_CACHE_TTL_SEC", "900"))  # 15 minutes


def _cache_key(profile: Dict[str, Any] | None, metrics: Dict[str, Any]) -> str:
  payload = {"profile": profile or {}, "metrics": metrics}
  return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def _build_prompt(profile: Dict[str, Any] | None, metrics: Dict[str, Any]) -> str:
  profile_json = json.dumps(profile or {}, ensure_ascii=False, indent=2)
  metrics_json = json.dumps(metrics, ensure_ascii=False, indent=2)
  return (
    "You are a conservative, India-focused financial planner.\n"
    "Given a user's profile and shock-resilience metrics, generate concrete, "
    "actionable advice to reduce vulnerability to financial shocks.\n\n"
    "Respond ONLY with valid JSON in the following format (no backticks, no Markdown):\n"
    '{\n'
    '  "normal": ["tip 1", "tip 2", ...],\n'
    '  "market_crash": ["tip 1", ...],\n'
    '  "job_loss": ["tip 1", ...],\n'
    '  "emergency": ["tip 1", ...]\n'
    "}\n\n"
    "Guidelines:\n"
    "- Keep each bullet short, specific, and tailored to the data.\n"
    "- Use Indian context: rupees (₹), SIPs, EMIs, and local terminology when relevant.\n"
    "- Avoid generic platitudes; focus on clear next steps.\n"
    "- Return only the TOP 4–5 most important, non-overlapping tips per list (never more than 5).\n\n"
    "USER_PROFILE:\n"
    f"{profile_json}\n\n"
    "RESILIENCE_METRICS:\n"
    f"{metrics_json}\n"
  )


def _validate_recommendations(data: Any) -> Optional[Dict[str, List[str]]]:
  if not isinstance(data, dict):
    return None
  required_keys = ["normal", "market_crash", "job_loss", "emergency"]
  result: Dict[str, List[str]] = {}
  for key in required_keys:
    value = data.get(key)
    if not isinstance(value, list):
      return None
    # Keep only string tips, stripped and non-empty.
    tips: List[str] = []
    for item in value:
      if isinstance(item, str):
        t = item.strip()
        if t:
          tips.append(t)
    # Limit to at most 5 tips per scenario.
    result[key] = tips[:5]
  return result


def _extract_json_object(text: str) -> Optional[str]:
  if not text or not isinstance(text, str):
    return None
  start = text.find("{")
  end = text.rfind("}")
  if start == -1 or end == -1 or end <= start:
    return None
  return text[start : end + 1]


def generate_resilience_recommendations(
  profile: Dict[str, Any] | None,
  metrics: Dict[str, Any],
) -> Optional[Dict[str, List[str]]]:
  """
  Call Gemini to produce scenario recommendations.

  Returns:
      dict with keys normal, market_crash, job_loss, emergency on success,
      or None on any error or when API key/model is not configured.
  """
  api_key = _safe_get_api_key()
  if not api_key:
    return None

  # In-memory cache to reduce repeated Gemini calls (helps rate limits/quota).
  cache_key = None
  try:
    cache_key = _cache_key(profile, metrics)
    cached = _RECOS_CACHE.get(cache_key)
    if cached:
      ts, val = cached
      if (time.time() - ts) <= _RECOS_CACHE_TTL_SEC:
        return val
  except Exception:
    cache_key = None

  prompt = _build_prompt(profile, metrics)
  headers = {"Content-Type": "application/json"}
  params = {"key": api_key}
  body = {
    "contents": [
      {
        "parts": [
          {
            "text": prompt,
          }
        ]
      }
    ],
    "generationConfig": {
      "temperature": 0.4,
      "maxOutputTokens": 512,
    },
  }

  model_candidates = [DEFAULT_GEMINI_MODEL] + [m for m in FALLBACK_GEMINI_MODELS if m != DEFAULT_GEMINI_MODEL]
  last_error_text = None
  data = None

  for model_name in model_candidates:
    endpoint = _build_endpoint(model_name)
    try:
      resp = requests.post(
        endpoint,
        headers=headers,
        params=params,
        json=body,
        timeout=20,
      )
    except Exception as e:  # pragma: no cover - network errors
      print("Gemini HTTP error:", e)
      return None

    if resp.status_code != 200:
      last_error_text = resp.text[:500]
      if resp.status_code == 429:
        print("Gemini rate-limited/quota exceeded:", last_error_text)
        return None
      # Retry with fallback model if current model is not supported.
      try:
        err = resp.json().get("error", {})
        msg = str(err.get("message", "")).lower()
        if resp.status_code == 404 and "not found" in msg:
          continue
      except Exception:
        pass
      print("Gemini non-200 response:", resp.status_code, last_error_text)
      return None

    try:
      data = resp.json()
      break
    except Exception as e:  # pragma: no cover
      print("Gemini JSON decode error:", e)
      return None

  if data is None:
    if last_error_text:
      print("Gemini failed for all models:", last_error_text)
    return None

  try:
    candidates = data.get("candidates") or []
    first = candidates[0] if candidates else None
    if not first:
      return None
    parts = (((first.get("content") or {}).get("parts")) or [])
    text = parts[0].get("text") if parts else ""
    json_text = _extract_json_object(text) or text
    parsed = json.loads(json_text)
  except Exception as e:  # pragma: no cover
    print("Gemini parsing error:", e)
    return None

  validated = _validate_recommendations(parsed)
  if not validated:
    print("Gemini recommendations validation failed")
    return None

  if cache_key:
    _RECOS_CACHE[cache_key] = (time.time(), validated)

  return validated

