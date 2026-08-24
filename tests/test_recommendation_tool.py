import unittest

from hungryradar.tools.recommendation import finalize_recommendation
from hungryradar.tools.lifecycle import record_availability, start_investigation
from hungryradar.lifecycle import Step


class FinalizeRecommendationToolTests(unittest.TestCase):
    def setUp(self):
        self.session_id = f"recommendation-test-{self._testMethodName}"
        start_investigation(session_id=self.session_id, inputs_valid=True)
        from hungryradar.tools.lifecycle import graph_for

        graph_for(self.session_id).record(**{"listings.found": True})
        graph_for(self.session_id).advance(Step.CHECK_AVAILABILITY)

    def test_bookable(self):
        record_availability(
            session_id=self.session_id,
            reservation_available=True,
            waitlist_available=False,
        )
        result = finalize_recommendation(
            session_id=self.session_id,
            place_id="p1",
            name="Nopa",
            address="560 Divisadero St",
            reservation_available=True,
        )

        self.assertEqual(result["status"], "bookable")
        self.assertEqual(result["place"]["name"], "Nopa")

    def test_high_wait_risk_beats_waitlist(self):
        record_availability(
            session_id=self.session_id,
            reservation_available=False,
            waitlist_available=True,
        )
        result = finalize_recommendation(
            session_id=self.session_id,
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
        record_availability(
            session_id=self.session_id,
            reservation_available=False,
            waitlist_available=False,
        )
        result = finalize_recommendation(
            session_id=self.session_id,
            place_id="p3",
            name="Nopa",
            address="560 Divisadero St",
            reservation_available=False,
        )

        self.assertEqual(result["status"], "unknown")


if __name__ == "__main__":
    unittest.main()
