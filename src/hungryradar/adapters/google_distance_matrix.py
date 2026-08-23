"""Google Distance Matrix API client."""

from __future__ import annotations

import httpx

_BASE_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"


def get_travel_time(
    api_key: str, origin: str, destination: str, mode: str = "driving"
) -> dict:
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
        return {"status": data.get("status", "UNKNOWN_ERROR")}

    element = data["rows"][0]["elements"][0]
    if element.get("status") != "OK":
        return {"status": element["status"]}

    return {
        "status": "OK",
        "distance_text": element["distance"]["text"],
        "duration_text": element["duration"]["text"],
        "travel_minutes": round(element["duration"]["value"] / 60),
    }
