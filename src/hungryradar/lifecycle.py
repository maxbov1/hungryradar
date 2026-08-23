"""Typed investigation lifecycle graph with JSON checkpoints."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Step(StrEnum):
    REQUEST_RECEIVED = "request_received"
    PLACE_RESOLVED = "place_resolved"
    PLACE_CONTEXT_READY = "place_context_ready"
    RESERVATION_CHECKED = "reservation_checked"
    WAITLIST_CHECKED = "waitlist_checked"
    VISIT_RISK_CHECKED = "visit_risk_checked"
    WALK_IN_CHECKED = "walk_in_checked"
    BOOKABLE = "bookable"
    WAITLIST_AVAILABLE = "waitlist_available"
    WALK_IN_POSSIBLE = "walk_in_possible"
    HIGH_WAIT_RISK = "high_wait_risk"
    DEAD_END = "dead_end"
    UNKNOWN = "unknown"


TERMINAL_STEPS = frozenset(
    {
        Step.BOOKABLE,
        Step.WAITLIST_AVAILABLE,
        Step.WALK_IN_POSSIBLE,
        Step.HIGH_WAIT_RISK,
        Step.DEAD_END,
        Step.UNKNOWN,
    }
)


@dataclass(frozen=True)
class Requirement:
    key: str
    expected: Any = True

    def met(self, evidence: dict[str, Any]) -> bool:
        return self.key in evidence and evidence[self.key] == self.expected


@dataclass(frozen=True)
class Node:
    """One loop node and the checks that must be complete before leaving it."""

    step: Step
    checks: tuple[Requirement, ...] = ()

    def complete(self, evidence: dict[str, Any]) -> bool:
        return all(check.met(evidence) for check in self.checks)


@dataclass(frozen=True)
class Transition:
    current: Step
    next: Step
    requires: tuple[Requirement, ...] = ()
    backtrack_to: Step | None = None

    def allowed(self, evidence: dict[str, Any]) -> bool:
        return all(requirement.met(evidence) for requirement in self.requires)


class LifecycleError(ValueError):
    """Raised when a graph operation would skip a lifecycle gate."""


TRANSITIONS = (
    Transition(Step.REQUEST_RECEIVED, Step.PLACE_RESOLVED, (Requirement("request.valid"),)),
    Transition(
        Step.PLACE_RESOLVED,
        Step.PLACE_CONTEXT_READY,
        (Requirement("place.resolved"),),
    ),
    Transition(
        Step.PLACE_CONTEXT_READY,
        Step.RESERVATION_CHECKED,
        (Requirement("place.context_ready"),),
    ),
    Transition(
        Step.RESERVATION_CHECKED,
        Step.BOOKABLE,
        (Requirement("reservation.checked"), Requirement("reservation.available")),
    ),
    Transition(
        Step.RESERVATION_CHECKED,
        Step.WAITLIST_CHECKED,
        (
            Requirement("reservation.checked"),
            Requirement("reservation.available", False),
        ),
    ),
    Transition(
        Step.WAITLIST_CHECKED,
        Step.WAITLIST_AVAILABLE,
        (Requirement("waitlist.checked"), Requirement("waitlist.available")),
    ),
    Transition(
        Step.WAITLIST_CHECKED,
        Step.VISIT_RISK_CHECKED,
        (
            Requirement("waitlist.checked"),
            Requirement("waitlist.available", False),
        ),
    ),
    Transition(
        Step.VISIT_RISK_CHECKED,
        Step.HIGH_WAIT_RISK,
        (Requirement("visit.checked"), Requirement("visit.high_wait")),
    ),
    Transition(
        Step.VISIT_RISK_CHECKED,
        Step.WALK_IN_CHECKED,
        (Requirement("visit.checked"), Requirement("visit.high_wait", False)),
    ),
    Transition(
        Step.WALK_IN_CHECKED,
        Step.WALK_IN_POSSIBLE,
        (Requirement("walk_in.checked"), Requirement("walk_in.supported")),
    ),
    Transition(
        Step.WALK_IN_CHECKED,
        Step.DEAD_END,
        (Requirement("walk_in.checked"), Requirement("walk_in.supported", False)),
    ),
    Transition(
        Step.WALK_IN_CHECKED,
        Step.UNKNOWN,
        (Requirement("walk_in.unknown"),),
    ),
)


NODES = {
    Step.REQUEST_RECEIVED: Node(
        Step.REQUEST_RECEIVED,
        (Requirement("request.valid"),),
    ),
    Step.PLACE_RESOLVED: Node(
        Step.PLACE_RESOLVED,
        (Requirement("place.resolved"),),
    ),
    Step.PLACE_CONTEXT_READY: Node(
        Step.PLACE_CONTEXT_READY,
        (Requirement("place.context_ready"),),
    ),
    Step.RESERVATION_CHECKED: Node(
        Step.RESERVATION_CHECKED,
        (Requirement("reservation.checked"),),
    ),
    Step.WAITLIST_CHECKED: Node(
        Step.WAITLIST_CHECKED,
        (Requirement("waitlist.checked"),),
    ),
    Step.VISIT_RISK_CHECKED: Node(
        Step.VISIT_RISK_CHECKED,
        (Requirement("visit.checked"),),
    ),
    Step.WALK_IN_CHECKED: Node(
        Step.WALK_IN_CHECKED,
        (Requirement("walk_in.checked"),),
    ),
}


@dataclass
class Checkpoint:
    """Everything needed to inspect or resume one investigation."""

    session_id: str
    current: Step = Step.REQUEST_RECEIVED
    evidence: dict[str, Any] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    history: list[Step] = field(default_factory=lambda: [Step.REQUEST_RECEIVED])

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["current"] = self.current.value
        data["history"] = [step.value for step in self.history]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        return cls(
            session_id=data["session_id"],
            current=Step(data["current"]),
            evidence=data.get("evidence", {}),
            attempts=data.get("attempts", {}),
            history=[Step(step) for step in data.get("history", [data["current"]])],
        )

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "Checkpoint":
        return cls.from_dict(json.loads(Path(path).read_text()))


class InvestigationGraph:
    """A gated lifecycle runner; tools only add evidence to it."""

    def __init__(self, session_id: str, checkpoint: Checkpoint | None = None) -> None:
        self.checkpoint = checkpoint or Checkpoint(session_id=session_id)
        self._transitions = TRANSITIONS

    @property
    def current(self) -> Step:
        return self.checkpoint.current

    def record(self, **evidence: Any) -> None:
        self.checkpoint.evidence.update(evidence)

    def allowed_transitions(self) -> tuple[Transition, ...]:
        return tuple(
            transition
            for transition in self._transitions
            if transition.current == self.current
            and transition.allowed(self.checkpoint.evidence)
        )

    def current_node(self) -> Node | None:
        return NODES.get(self.current)

    def checks_complete(self) -> bool:
        node = self.current_node()
        return node is None or node.complete(self.checkpoint.evidence)

    def advance(self, next_step: Step) -> None:
        transition = next(
            (
                transition
                for transition in self._transitions
                if transition.current == self.current and transition.next == next_step
            ),
            None,
        )
        if transition is None or not transition.allowed(self.checkpoint.evidence):
            raise LifecycleError(
                f"Cannot advance {self.current} -> {next_step}; required evidence is missing"
            )

        self.checkpoint.current = next_step
        self.checkpoint.history.append(next_step)

    def backtrack(self, target: Step, *, invalidate: tuple[str, ...] = ()) -> None:
        if target not in self.checkpoint.history:
            raise LifecycleError(f"Cannot backtrack to unvisited step: {target}")

        for key in invalidate:
            self.checkpoint.evidence.pop(key, None)
        self.checkpoint.attempts[target.value] = (
            self.checkpoint.attempts.get(target.value, 0) + 1
        )
        self.checkpoint.current = target
        self.checkpoint.history.append(target)

    def is_terminal(self) -> bool:
        return self.current in TERMINAL_STEPS
