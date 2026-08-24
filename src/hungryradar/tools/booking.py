"""Strands tools for booking-page evidence.

Reservation platforms (OpenTable, Resy, Tock, ...) expose no shared public
availability API. These tools fetch a page and return its visible text as
evidence with status "unknown"; they never assert "bookable" or "dead end"
themselves. See README.md#implementation-notes and the agent's system prompt,
which tells it to read page_text_snippet for genuine clues before deciding.
"""

from strands import tool

from ..adapters.booking_page import fetch_page_text, find_links_by_domain

KNOWN_BOOKING_DOMAINS = (
    "opentable.com",
    "resy.com",
    "exploretock.com",
    "sevenrooms.com",
    "yelp.com/reservations",
)


@tool
def find_booking_links(website_uri: str) -> dict:
    """Look for a reservation-provider link on a restaurant's official website.

    Takes the website URL (typically from get_place_details), not a place_id,
    since a place_id alone doesn't resolve to a website without that lookup.

    Args:
        website_uri: The restaurant's official website URL.
    """
    result = find_links_by_domain(website_uri, KNOWN_BOOKING_DOMAINS)
    result["known_domains_checked"] = list(KNOWN_BOOKING_DOMAINS)
    return result


@tool
def check_reservations(booking_uri: str, party_size: int, date_: str, time_: str) -> dict:
    """Fetch a reservation page's visible text as evidence for a party/time.

    This does not parse live availability - no reservation platform exposes a
    shared public API for that. Read page_text_snippet for genuine clues
    ("no tables available", "book now") before deciding a status; otherwise
    report Unknown.

    Args:
        booking_uri: The reservation page URL, from find_booking_links.
        party_size: Number of people.
        date_: Requested date, e.g. "2026-08-23".
        time_: Requested time, e.g. "19:30".
    """
    result = fetch_page_text(booking_uri)
    result["status"] = "unknown" if result.get("fetched") else "unreachable"
    result["party_size"] = party_size
    result["requested_date"] = date_
    result["requested_time"] = time_
    return result


@tool
def check_waitlist(booking_uri: str) -> dict:
    """Fetch a reservation/waitlist page's visible text as waitlist evidence.

    Same fetch-and-read approach as check_reservations: no status is asserted
    beyond "unknown"; read page_text_snippet for waitlist clues ("join our
    waitlist", "no waitlist available").

    Args:
        booking_uri: The reservation or waitlist page URL.
    """
    result = fetch_page_text(booking_uri)
    result["status"] = "unknown" if result.get("fetched") else "unreachable"
    return result


@tool
def check_official_updates(website_uri: str) -> dict:
    """Fetch a restaurant's official website text for closure or hours notices.

    Use this to catch conflicts Google Places wouldn't reflect yet, e.g.
    "closed for a private event tonight" or a holiday-hours banner.

    Args:
        website_uri: The restaurant's official website URL.
    """
    result = fetch_page_text(website_uri)
    result["status"] = "unknown" if result.get("fetched") else "unreachable"
    return result
