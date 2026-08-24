"""Google Distance Matrix API client."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

_BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def get_travel_time(
    api_key: str, origin: str, destination: str, mode: str = "driving"
) -> dict:
    checked_at = datetime.now(timezone.utc).isoformat()
    response = httpx.get(
        _BASE_URL,
        params={
            "origins": origin,
            "destinations": destination,
            "mode": mode,
            "key": api_key,
        },
        timeout=10.0,
    )
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "OK":
        return {
            "status": data.get("status", "UNKNOWN_ERROR"),
            "source_uri": _BASE_URL,
            "checked_at": checked_at,
        }

    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        return {
            "status": element["status"],
            "source_uri": _BASE_URL,
            "checked_at": checked_at,
        }

    return {
        "status": "OK",
        "source_uri": _BASE_URL,
        "checked_at": checked_at,
        "distance_text": element["distance"]["text"],
        "duration_text": element["duration"]["text"],
        "travel_minutes": round(element["duration"]["value"] / 60),
    }
