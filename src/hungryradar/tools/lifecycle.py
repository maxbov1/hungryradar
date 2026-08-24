"""Lifecycle session tools and gates for the Strands tool boundary."""

from strands import tool

from ..lifecycle import InvestigationGraph, LifecycleError, Step

_SESSIONS: dict[str, InvestigationGraph] = {}


def graph_for(session_id: str) -> InvestigationGraph:
    if not session_id:
        raise LifecycleError("session_id is required for every investigation tool")
    return _SESSIONS.setdefault(session_id, InvestigationGraph(session_id))


def require_step(session_id: str, *steps: Step) -> InvestigationGraph:
    graph = graph_for(session_id)
    if graph.current not in steps:
        expected = ", ".join(step.value for step in steps)
        raise LifecycleError(
            f"Session {session_id!r} is at {graph.current.value}; expected {expected}"
        )
    return graph


@tool
def start_investigation(session_id: str, inputs_valid: bool) -> dict:
    """Create a lifecycle session and pass validated request inputs."""
    graph = graph_for(session_id)
    if graph.current != Step.INPUTS:
        raise LifecycleError(f"Session {session_id!r} has already started")
    graph.record(**{"inputs.valid": inputs_valid})
    if inputs_valid:
        graph.advance(Step.IDENTIFY_LISTINGS)
    return {"session_id": session_id, "current": graph.current.value}


@tool
def record_availability(
    session_id: str,
    reservation_available: bool,
    waitlist_available: bool,
    walk_ins_possible: bool = False,
) -> dict:
    """Record the explicit availability result before finalizing a recommendation."""
    graph = require_step(session_id, Step.CHECK_AVAILABILITY)
    graph.record(
        **{
            "availability.checked": True,
            "reservation.available": reservation_available,
            "waitlist.available": waitlist_available,
            "walk_in.supported": walk_ins_possible,
        }
    )
    return {"session_id": session_id, "current": graph.current.value}
