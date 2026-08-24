import unittest

from hungryradar.tools.recommendation import finalize_recommendation


class FinalizeRecommendationToolTests(unittest.TestCase):
    def test_bookable(self):
        result = finalize_recommendation(
            place_id="p1",
            name="Nopa",
            address="560 Divisadero St",
            reservation_available=True,
        )

        self.assertEqual(result["status"], "bookable")
        self.assertEqual(result["place"]["name"], "Nopa")

    def test_high_wait_risk_beats_waitlist(self):
        result = finalize_recommendation(
            place_id="p2",
            name="Nopa",
            address="560 Divisadero St",
            reservation_available=False,
            waitlist_available=True,
            typical_wait_minutes=90,
            max_wait_minutes=30,
        )

        self.assertEqual(result["status"], "high_wait_risk")

    def test_no_evidence_is_unknown(self):
        result = finalize_recommendation(
            place_id="p3",
            name="Nopa",
            address="560 Divisadero St",
            reservation_available=False,
        )

        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
