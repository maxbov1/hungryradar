import unittest

from hungryradar.decision import recommend
from hungryradar.models import Place, RecommendationStatus, ReservationResult, VisitData


PLACE = Place("place-1", "Nopa", "San Francisco")


class RecommendationTests(unittest.TestCase):
    def test_reservation_wins_over_high_walk_in_wait(self):
        result = recommend(
            PLACE,
            ReservationResult(available=True),
            VisitData(typical_wait_minutes=90),
            max_wait_minutes=30,
        )

        self.assertEqual(result.status, RecommendationStatus.BOOKABLE)

    def test_high_wait_removes_no_reservation_place(self):
        result = recommend(
            PLACE,
            ReservationResult(),
            VisitData(typical_wait_minutes=55),
            max_wait_minutes=30,
            walk_ins_possible=True,
        )

        self.assertEqual(result.status, RecommendationStatus.HIGH_WAIT_RISK)

    def test_waitlist_is_used_when_wait_is_within_tolerance(self):
        result = recommend(
            PLACE,
            ReservationResult(waitlist_available=True),
            VisitData(typical_wait_minutes=20),
            max_wait_minutes=30,
        )

        self.assertEqual(result.status, RecommendationStatus.WAITLIST_AVAILABLE)


if __name__ == "__main__":
    unittest.main()
