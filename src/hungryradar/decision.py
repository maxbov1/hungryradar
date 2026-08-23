"""Pure recommendation rules.

The order matters: reservations win, then wait risk, then waitlist or walk-in.
"""

from .models import (
    Place,
    Recommendation,
    RecommendationStatus,
    ReservationResult,
    VisitData,
)


def recommend(
    place: Place,
    reservation: ReservationResult,
    visit_data: VisitData | None = None,
    *,
    max_wait_minutes: int | None = None,
    walk_ins_possible: bool = False,
) -> Recommendation:
    if reservation.available:
        return Recommendation(
            place,
            RecommendationStatus.BOOKABLE,
            "A reservation is available for the requested party and time.",
            "Reserve this table.",
            reservation,
            visit_data,
        )

    wait = visit_data.typical_wait_minutes if visit_data else None
    if max_wait_minutes is not None and wait is not None and wait > max_wait_minutes:
        return Recommendation(
            place,
            RecommendationStatus.HIGH_WAIT_RISK,
            f"No reservation is available, and the typical wait is about {wait} minutes.",
            "Choose another restaurant or a less busy time.",
            reservation,
            visit_data,
        )

    if reservation.waitlist_available:
        return Recommendation(
            place,
            RecommendationStatus.WAITLIST_AVAILABLE,
            "No reservation is available, but a waitlist can be joined.",
            "Join the waitlist.",
            reservation,
            visit_data,
        )

    if walk_ins_possible:
        return Recommendation(
            place,
            RecommendationStatus.WALK_IN_POSSIBLE,
            "No reservation is available, but public information supports a walk-in.",
            "Go only if you are comfortable with an unconfirmed wait.",
            reservation,
            visit_data,
        )

    return Recommendation(
        place,
        RecommendationStatus.UNKNOWN,
        "No reservation or waitlist is visible, and walk-in availability is unverified.",
        "Verify with the restaurant or choose another option.",
        reservation,
        visit_data,
    )
