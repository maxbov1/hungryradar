"""Interfaces for external data sources.

Adapters can implement these protocols without leaking SDK types into the core.
"""

from datetime import date, time
from typing import Protocol

from .models import Place, ReservationResult, VisitData


class PlaceProvider(Protocol):
    def get_place(self, place_id: str) -> Place: ...


class ReservationProvider(Protocol):
    def check(
        self, place: Place, party_size: int, date_: date, time_: time
    ) -> ReservationResult: ...


class VisitDataProvider(Protocol):
    def get_visit_data(
        self, place: Place, date_: date, time_: time
    ) -> VisitData | None: ...
