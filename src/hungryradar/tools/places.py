"""Strands tools for Google Places: find candidates, then hydrate one."""

from dataclasses import asdict

from strands import tool

from ..adapters.google_places import get_place, search_places
from ..config import settings


@tool
def find_places(query: str, max_results: int = 5) -> list[dict]:
    """Search Google Places for restaurant candidates matching a free-form query.

    Use this for the "find a restaurant" workflow, when the user gives a
    cuisine, area, or description instead of a specific name. Returns a short
    list of candidates (place_id, name, address, rating, price_level); call
    get_place_details on the one(s) you decide to investigate next.

    Args:
        query: Free-form search text, e.g. "Thai restaurants in San Francisco".
        max_results: Maximum number of candidates to return.
    """
    if not settings.google_maps_api_key:
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured"}]
    return search_places(settings.google_maps_api_key, query, max_results)


@tool
def get_place_details(place_id: str) -> dict:
    """Hydrate the canonical place record for one Google Place ID.

    Returns identity, address, rating, price level, website, Maps link, plus
    business status and opening hours as supporting evidence. This is the
    source of truth for restaurant identity; do not guess these fields.

    Args:
        place_id: The Google Place ID, from find_places or a user-provided link.
    """
    if not settings.google_maps_api_key:
        return {"error": "GOOGLE_MAPS_API_KEY is not configured"}
    place, extra = get_place(settings.google_maps_api_key, place_id)
    return {**asdict(place), **extra}
