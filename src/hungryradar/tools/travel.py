"""Strands tool for travel time between two points."""

from strands import tool

from ..adapters.google_distance_matrix import get_travel_time
from ..config import settings


@tool
def calculate_travel_time(origin: str, destination: str, mode: str = "driving") -> dict:
    """Estimate travel time and distance between two addresses or place names.

    Use this to check whether a restaurant is within the user's stated travel
    limit.

    Args:
        origin: The starting address or place name.
        destination: The restaurant's address (e.g. from get_place_details).
        mode: Travel mode: "driving", "walking", "bicycling", or "transit".
    """
    if not settings.google_maps_api_key:
        return {"status": "error", "error": "GOOGLE_MAPS_API_KEY is not configured"}
    return get_travel_time(settings.google_maps_api_key, origin, destination, mode)
