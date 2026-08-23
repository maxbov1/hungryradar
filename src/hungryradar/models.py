"""Domain objects shared by providers and the recommendation logic."""

from dataclasses import dataclass
from enum import StrEnum


class RecommendationStatus(StrEnum):
    BOOKABLE = "bookable"
    HIGH_WAIT_RISK = "high_wait_risk"
    WAITLIST_AVAILABLE = "waitlist_available"
    WALK_IN_POSSIBLE = "walk_in_possible"
    DEAD_END = "dead_end"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Place:
    """The canonical place record, hydrated from Google Places."""

    place_id: str
    name: str
    address: str
    google_maps_uri: str | None = None
    description: str | None = None
    website_uri: str | None = None
    menu_uri: str | None = None
    rating: float | None = None
    price_level: str | None = None
    timezone: str | None = None
    open_at_requested_time: bool | None = None
    travel_minutes: int | None = None
    directions_uri: str | None = None


@dataclass(frozen=True)
class ReservationResult:
    available: bool = False
    waitlist_available: bool = False
    source_uri: str | None = None


@dataclass(frozen=True)
class VisitData:
    """Google's historical or live visit signal for the requested time."""

    typical_wait_minutes: int | None = None
    popular_times_level: str | None = None
    live_activity_level: str | None = None
    source_uri: str | None = None


@dataclass(frozen=True)
class Recommendation:
    place: Place
    status: RecommendationStatus
    reason: str
    next_action: str
    reservation: ReservationResult
    visit_data: VisitData | None = None
