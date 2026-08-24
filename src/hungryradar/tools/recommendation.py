"""Strands tool that turns gathered evidence into the final recommendation.

Every other tool in this package hands the agent raw facts (place details,
page text, links). This tool is the single place where those facts turn into
one of the five statuses in README.md's status table, by calling the pure,
tested rules in decision.recommend() instead of leaving the wording and
status choice to the model.
"""

from dataclasses import asdict

from strands import tool

from ..decision import recommend
from ..models import Place, ReservationResult, VisitData
from ..lifecycle import Step
from .lifecycle import require_step


@tool
def finalize_recommendation(
    session_id: str,
    place_id: str,
    name: str,
    address: str,
    reservation_available: bool,
    google_maps_uri: str | None = None,
    website_uri: str | None = None,
    reservation_source_uri: str | None = None,
    reservation_checked_at: str | None = None,
    waitlist_available: bool = False,
    walk_ins_possible: bool = False,
    typical_wait_minutes: int | None = None,
    google_wait_source_uri: str | None = None,
    google_wait_checked_at: str | None = None,
    max_wait_minutes: int | None = None,
) -> dict:
    """Apply HungryRadar's decision rules to the evidence you have gathered.

    Call this exactly once per restaurant, as your last step for that
    restaurant, after you have checked hours, reservations, waitlist, and
    walk-in signals. It returns the status, reason, and next action to report
    verbatim - do not invent your own wording or status for a restaurant you
    have run this on.

    Args:
        place_id: The Google Place ID, from find_places or get_place_details.
        name: The restaurant's name, from get_place_details.
        address: The restaurant's address, from get_place_details.
        reservation_available: True only if check_reservations' evidence
            clearly shows an open table near the requested time.
        google_maps_uri: The Maps link, from get_place_details.
        website_uri: The official website, from get_place_details.
        reservation_source_uri: The page you checked for reservation/waitlist
            evidence, so the user can verify it themselves.
        waitlist_available: True only if the evidence clearly shows a
            waitlist can be joined.
        walk_ins_possible: True only if the evidence clearly supports a
            walk-in (e.g. "walk-ins welcome"), not merely the absence of
            evidence against it.
        typical_wait_minutes: Google's typical wait estimate for the
            requested time, if you have one; otherwise leave unset.
        max_wait_minutes: The user's stated wait tolerance in minutes, if
            they gave one.
    """
    graph = require_step(session_id, Step.CHECK_AVAILABILITY)
    evidence = graph.checkpoint.evidence
    if (
        evidence.get("availability.checked") is not True
        or evidence.get("reservation.available") != reservation_available
        or evidence.get("waitlist.available") != waitlist_available
        or evidence.get("walk_in.supported", False) != walk_ins_possible
    ):
        raise ValueError(
            "record_availability must confirm the provider evidence before finalizing"
        )

    place = Place(
        place_id=place_id,
        name=name,
        address=address,
        google_maps_uri=google_maps_uri,
        website_uri=website_uri,
    )
    reservation = ReservationResult(
        available=reservation_available,
        waitlist_available=waitlist_available,
        source_uri=reservation_source_uri,
        checked_at=reservation_checked_at,
    )
    visit_data = (
        VisitData(
            typical_wait_minutes=typical_wait_minutes,
            source_uri=google_wait_source_uri or google_maps_uri,
            checked_at=google_wait_checked_at,
        )
        if typical_wait_minutes is not None
        else None
    )

    result = recommend(
        place,
        reservation,
        visit_data,
        max_wait_minutes=max_wait_minutes,
        walk_ins_possible=walk_ins_possible,
    )

    return {
        "place": asdict(place),
        "status": result.status.value,
        "reason": result.reason,
        "next_action": result.next_action,
        "reservation": asdict(result.reservation),
        "visit_data": asdict(result.visit_data) if result.visit_data else None,
    }
