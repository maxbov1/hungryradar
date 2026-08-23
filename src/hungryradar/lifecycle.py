"""Typed reservation lifecycle graph with JSON checkpoints."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Step(StrEnum):
    INPUTS = "inputs"
    IDENTIFY_LISTINGS = "identify_listings"
    CHECK_AVAILABILITY = "check_availability"
    CHECK_RESERVATION_FORM = "check_reservation_form"
    PROPOSE_CONFIRM = "propose_confirm"
    BOOK = "book"
    BOOKED = "booked"
    WAITLIST_AVAILABLE = "waitlist_available"
    NO_MATCH = "no_match"
    UNKNOWN = "unknown"


TERMINAL_STEPS = frozenset(
    {Step.BOOKED, Step.WAITLIST_AVAILABLE, Step.NO_MATCH, Step.UNKNOWN}
)


@dataclass(frozen=True)
class Requirement:
    key: str
    expected: Any = True

    def met(self, evidence: dict[str, Any]) -> bool:
        return self.key in evidence and evidence[self.key] == self.expected


@dataclass(frozen=True)
class Node:
    """One user-facing lifecycle node and its completion checklist."""

    step: Step
    checks: tuple[Requirement, ...] = ()

    def complete(self, evidence: dict[str, Any]) -> bool:
        return all(check.met(evidence) for check in self.checks)


@dataclass(frozen=True)
class Transition:
    current: Step
    next: Step
    requires: tuple[Requirement, ...] = ()

    def allowed(self, evidence: dict[str, Any]) -> bool:
        return all(requirement.met(evidence) for requirement in self.requires)


class LifecycleError(ValueError):
    """Raised when a graph operation would skip a lifecycle gate."""


TRANSITIONS = (
    Transition(Step.INPUTS, Step.IDENTIFY_LISTINGS, (Requirement("inputs.valid"),)),
    Transition(
        Step.IDENTIFY_LISTINGS,
        Step.CHECK_AVAILABILITY,
        (Requirement("listings.found"),),
    ),
    Transition(
        Step.CHECK_AVAILABILITY,
        Step.CHECK_RESERVATION_FORM,
        (Requirement("availability.checked"), Requirement("reservation.available")),
    ),
    Transition(
        Step.CHECK_AVAILABILITY,
        Step.WAITLIST_AVAILABLE,
        (
            Requirement("availability.checked"),
            Requirement("reservation.available", False),
            Requirement("waitlist.available"),
        ),
    ),
    Transition(
        Step.CHECK_AVAILABILITY,
        Step.NO_MATCH,
        (
            Requirement("availability.checked"),
            Requirement("reservation.available", False),
            Requirement("waitlist.available", False),
        ),
    ),
    Transition(
        Step.CHECK_RESERVATION_FORM,
        Step.PROPOSE_CONFIRM,
        (Requirement("reservation.form.checked"), Requirement("form.valid")),
    ),
    Transition(
        Step.PROPOSE_CONFIRM,
        Step.BOOK,
        (Requirement("proposal.presented"), Requirement("user.confirmed")),
    ),
    Transition(
        Step.PROPOSE_CONFIRM,
        Step.IDENTIFY_LISTINGS,
        (Requirement("proposal.presented"), Requirement("user.confirmed", False)),
    ),
    Transition(
        Step.BOOK,
        Step.BOOKED,
        (Requirement("booking.attempted"), Requirement("booking.success")),
    ),
    Transition(
        Step.BOOK,
        Step.PROPOSE_CONFIRM,
        (
            Requirement("booking.attempted"),
            Requirement("booking.success", False),
            Requirement("proposal.presented"),
        ),
    ),
)


NODES = {
    Step.INPUTS: Node(Step.INPUTS, (Requirement("inputs.valid"),)),
    Step.IDENTIFY_LISTINGS: Node(
        Step.IDENTIFY_LISTINGS,
        (Requirement("listings.found"),),
    ),
    Step.CHECK_AVAILABILITY: Node(
        Step.CHECK_AVAILABILITY,
        (Requirement("availability.checked"),),
    ),
    Step.CHECK_RESERVATION_FORM: Node(
        Step.CHECK_RESERVATION_FORM,
        (Requirement("reservation.form.checked"),),
    ),
    Step.PROPOSE_CONFIRM: Node(
        Step.PROPOSE_CONFIRM,
        (Requirement("proposal.presented"),),
    ),
    Step.BOOK: Node(Step.BOOK, (Requirement("booking.attempted"),)),
}


@dataclass
class Checkpoint:
    """Everything needed to inspect or resume one reservation attempt."""

    session_id: str
    current: Step = Step.INPUTS
    evidence: dict[str, Any] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    history: list[Step] = field(default_factory=lambda: [Step.INPUTS])

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
    """A gated reservation lifecycle runner; tools only add evidence to it."""

    def __init__(self, session_id: str, checkpoint: Checkpoint | None = None) -> None:
        self.checkpoint = checkpoint or Checkpoint(session_id=session_id)

    @property
    def current(self) -> Step:
        return self.checkpoint.current

    def record(self, **evidence: Any) -> None:
        self.checkpoint.evidence.update(evidence)

    def allowed_transitions(self) -> tuple[Transition, ...]:
        return tuple(
            transition
            for transition in TRANSITIONS
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
                for transition in TRANSITIONS
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
