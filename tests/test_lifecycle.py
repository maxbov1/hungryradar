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
    def test_gates_prevent_skipping_steps(self):
        graph = InvestigationGraph("session-1")

        with self.assertRaises(LifecycleError):
            graph.advance(Step.PLACE_RESOLVED)

        graph.record(**{"request.valid": True})
        graph.advance(Step.PLACE_RESOLVED)
        self.assertEqual(graph.current, Step.PLACE_RESOLVED)
        self.assertFalse(graph.checks_complete())
        graph.record(**{"place.resolved": True})
        self.assertTrue(graph.checks_complete())

    def test_high_wait_branch_is_terminal(self):
        graph = InvestigationGraph("session-2")
        graph.record(**{"request.valid": True})
        graph.advance(Step.PLACE_RESOLVED)
        graph.record(**{"place.resolved": True})
        graph.advance(Step.PLACE_CONTEXT_READY)
        graph.record(**{"place.context_ready": True})
        graph.advance(Step.RESERVATION_CHECKED)
        graph.record(**{"reservation.checked": True, "reservation.available": False})
        graph.advance(Step.WAITLIST_CHECKED)
        graph.record(**{"waitlist.checked": True, "waitlist.available": False})
        graph.advance(Step.VISIT_RISK_CHECKED)
        graph.record(**{"visit.checked": True, "visit.high_wait": True})
        graph.advance(Step.HIGH_WAIT_RISK)

        self.assertTrue(graph.is_terminal())

    def test_backtrack_invalidates_stale_evidence(self):
        graph = InvestigationGraph("session-3")
        graph.record(**{"request.valid": True})
        graph.advance(Step.PLACE_RESOLVED)
        graph.record(**{"place.resolved": True, "place.context_ready": True})
        graph.advance(Step.PLACE_CONTEXT_READY)
        graph.backtrack(Step.PLACE_RESOLVED, invalidate=("place.context_ready",))

        self.assertEqual(graph.current, Step.PLACE_RESOLVED)
        self.assertNotIn("place.context_ready", graph.checkpoint.evidence)
        self.assertEqual(graph.checkpoint.attempts[Step.PLACE_RESOLVED.value], 1)

    def test_checkpoint_round_trip(self):
        graph = InvestigationGraph("session-4")
        graph.record(**{"request.valid": True})
        graph.advance(Step.PLACE_RESOLVED)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            graph.checkpoint.save(path)
            restored = InvestigationGraph(
                "ignored", checkpoint=Checkpoint.load(path)
            )

        self.assertEqual(restored.checkpoint.session_id, "session-4")
        self.assertEqual(restored.current, Step.PLACE_RESOLVED)
        self.assertEqual(restored.checkpoint.evidence["request.valid"], True)


if __name__ == "__main__":
    unittest.main()
