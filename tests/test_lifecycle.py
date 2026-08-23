import tempfile
import unittest
from pathlib import Path

from hungryradar.lifecycle import (
    Checkpoint,
    InvestigationGraph,
    LifecycleError,
    Step,
)


class LifecycleGraphTests(unittest.TestCase):
    def move_to_availability(self, graph: InvestigationGraph) -> None:
        graph.record(**{"inputs.valid": True})
        graph.advance(Step.IDENTIFY_LISTINGS)
        graph.record(**{"listings.found": True})
        graph.advance(Step.CHECK_AVAILABILITY)

    def test_gates_prevent_skipping_steps(self):
        graph = InvestigationGraph("session-1")

        with self.assertRaises(LifecycleError):
            graph.advance(Step.CHECK_AVAILABILITY)

        graph.record(**{"inputs.valid": True})
        graph.advance(Step.IDENTIFY_LISTINGS)
        self.assertFalse(graph.checks_complete())
        graph.record(**{"listings.found": True})
        self.assertTrue(graph.checks_complete())

    def test_reservation_path_reaches_booked(self):
        graph = InvestigationGraph("session-2")
        self.move_to_availability(graph)
        graph.record(
            **{"availability.checked": True, "reservation.available": True}
        )
        graph.advance(Step.CHECK_RESERVATION_FORM)
        graph.record(**{"reservation.form.checked": True, "form.valid": True})
        graph.advance(Step.PROPOSE_CONFIRM)
        graph.record(**{"proposal.presented": True, "user.confirmed": True})
        graph.advance(Step.BOOK)
        graph.record(**{"booking.attempted": True, "booking.success": True})
        graph.advance(Step.BOOKED)

        self.assertTrue(graph.is_terminal())

    def test_user_declining_proposal_backtracks_to_listings(self):
        graph = InvestigationGraph("session-3")
        self.move_to_availability(graph)
        graph.record(
            **{"availability.checked": True, "reservation.available": True}
        )
        graph.advance(Step.CHECK_RESERVATION_FORM)
        graph.record(**{"reservation.form.checked": True, "form.valid": True})
        graph.advance(Step.PROPOSE_CONFIRM)
        graph.record(**{"proposal.presented": True, "user.confirmed": False})
        graph.advance(Step.IDENTIFY_LISTINGS)

        self.assertEqual(graph.current, Step.IDENTIFY_LISTINGS)

    def test_failed_booking_returns_to_confirmation(self):
        graph = InvestigationGraph("session-4")
        self.move_to_availability(graph)
        graph.record(
            **{"availability.checked": True, "reservation.available": True}
        )
        graph.advance(Step.CHECK_RESERVATION_FORM)
        graph.record(**{"reservation.form.checked": True, "form.valid": True})
        graph.advance(Step.PROPOSE_CONFIRM)
        graph.record(**{"proposal.presented": True, "user.confirmed": True})
        graph.advance(Step.BOOK)
        graph.record(
            **{
                "booking.attempted": True,
                "booking.success": False,
                "proposal.presented": True,
            }
        )
        graph.advance(Step.PROPOSE_CONFIRM)

        self.assertEqual(graph.current, Step.PROPOSE_CONFIRM)

    def test_checkpoint_round_trip(self):
        graph = InvestigationGraph("session-5")
        graph.record(**{"inputs.valid": True})
        graph.advance(Step.IDENTIFY_LISTINGS)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            graph.checkpoint.save(path)
            restored = InvestigationGraph("ignored", checkpoint=Checkpoint.load(path))

        self.assertEqual(restored.checkpoint.session_id, "session-5")
        self.assertEqual(restored.current, Step.IDENTIFY_LISTINGS)
        self.assertEqual(restored.checkpoint.evidence["inputs.valid"], True)


if __name__ == "__main__":
    unittest.main()
