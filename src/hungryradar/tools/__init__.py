"""Strands tools available to the HungryRadar agent."""

from .booking import (
    check_official_updates,
    check_reservations,
    check_waitlist,
    find_booking_links,
)
from .places import find_places, get_place_details
from .recommendation import finalize_recommendation
from .travel import calculate_travel_time
from .lifecycle import record_availability, start_investigation

ALL_TOOLS = [
    start_investigation,
    record_availability,
    find_places,
    get_place_details,
    calculate_travel_time,
    find_booking_links,
    check_reservations,
    check_waitlist,
    check_official_updates,
    finalize_recommendation,
]
