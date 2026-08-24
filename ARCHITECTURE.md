# HungryRadar Architecture

This document is for people implementing HungryRadar. It describes the seams between our domain logic, external provider SDKs, the Strands agent, and the graph.

## System context

Google Places is the canonical source for intrinsic place data: identity, description, category, address, hours, website/menu links, Maps links, and routing details. HungryRadar does not copy another source into that role.

Reservation providers answer whether a party can book or join a waitlist. Google visit data supplies a secondary wait-risk signal when no reservation is available. The agent interprets these facts and explains the result.

```text
User request
    |
    v
Application service  <--- deterministic product rules
    |
    +--> Google Places adapter       ---> canonical Place
    +--> Reservation adapters        ---> reservation / waitlist facts
    +--> Google visit-data adapter   ---> time-specific wait-risk facts
    +--> Investigation graph         ---> lifecycle, gates, backtracking
    |
    v
Strands agent                        ---> chooses investigation steps and explains
    |
    v
Recommendation with evidence
```

## Components

The current implementation has four working layers:

- `models.py`, `decision.py`, and `lifecycle.py` contain provider-independent data, recommendation rules, and gated session state.
- `adapters/` contains the Google Places, Distance Matrix, and booking-page HTTP clients.
- `tools/` exposes those adapters to Strands and enforces the lifecycle session gates.
- `agent.py` builds the Strands agent, prompt, and command-line entry point.

## Data Flow

Place resolution starts with Google Places, availability checks enrich the canonical place record, and the agent returns a recommendation with evidence.

## Current package layout

The current `src/hungryradar` files are the first slice of this layout. Add a directory only when it has a real implementation behind it.

```text
src/hungryradar/
  agent.py                 # Strands agent, system prompt, and CLI
  config.py                # Environment-backed settings
  models.py                # Canonical place and recommendation models
  decision.py              # Pure recommendation rules
  lifecycle.py             # Typed transitions and checkpoints
  ports.py                 # Provider-facing interfaces
  adapters/
    google_places.py       # Google Places API client and mapping
    google_distance_matrix.py
    booking_page.py        # Booking-page fetch and text extraction
  tools/
    lifecycle.py           # Session registry and tool gates
    places.py               # Google Places tools
    travel.py               # Travel-time tool
    booking.py              # Booking and official-site tools
    recommendation.py      # Final deterministic recommendation tool
```

## Where the SDKs live

Our code owns the interfaces and normalized models. Vendor SDKs stay inside adapters.

```text
Google Places SDK/API
    -> adapters/google_places/client.py
    -> adapters/google_places/mapper.py
    -> Place model

Reservation provider SDK/API
    -> adapters/reservations/<provider>/client.py
    -> ReservationResult model

Strands Agents SDK
    -> orchestration/strands_agent.py
    -> calls application use cases and read-only tools
    -> never owns persistence or vendor response parsing
```

This keeps a provider swap boring. The rest of the application should not know whether a `Place` came from an HTTP client, an SDK, or a test fixture.

## Strands boundary

Strands is the investigation coordinator, not the business rules engine.

```python
agent = Agent(system_prompt=SYSTEM_PROMPT, tools=ALL_TOOLS)
agent(user_request)
```

Each tool receives the same `session_id`. The lifecycle gate rejects calls made out of order. The agent may choose which permitted evidence tool to call next, but it cannot call `finalize_recommendation` until `record_availability` has recorded explicit availability evidence.

## Running one agent cycle

```text
start_investigation(session_id, inputs_valid)
    -> find_places(...) or get_place_details(...)
    -> check_official_updates(...)
    -> find_booking_links(...)
    -> check_reservations(...) and check_waitlist(...)
    -> calculate_travel_time(...)
    -> record_availability(...)
    -> finalize_recommendation(...)
```

The agent can stop early when a result is clear, but it must preserve evidence links and `checked_at` timestamps. A failed or blocked provider call produces uncertainty; it is never converted into a positive availability fact.

## Investigation graph

The graph is the reservation lifecycle. It is a circular set of gated user-facing nodes, not a restaurant knowledge graph. Each node has a small checklist of evidence. A central runner records evidence, permits only checked transitions, and backpedals when the user declines a proposal or a later check invalidates an earlier assumption.

```text
INPUTS
    | valid request
    v
IDENTIFY_LISTINGS
    | one or more resolved Google Place IDs
    v
CHECK_AVAILABILITY
    | reservations, waitlists, hours, and wait risk
    +--> reservation available --------------------> CHECK_RESERVATION_FORM
    |
    +--> waitlist available -----------------------> WAITLIST_AVAILABLE
    |
    +--> no credible path --------------------------> NO_MATCH
             |
             v
CHECK_RESERVATION_FORM
    | form matches internal reservation structure
    v
PROPOSE_CONFIRM
    +--> user confirms -----------------------------> BOOK
    +--> user declines -----------------------------> IDENTIFY_LISTINGS

BOOK
    +--> booking succeeds --------------------------> BOOKED
    +--> booking fails -----------------------------> PROPOSE_CONFIRM

Any node with missing, stale, or conflicting evidence --backpedals-->
the earliest node that can repair that evidence.
```

### Transition contract

```python
Transition(
    current=PROPOSE_CONFIRM,
    next=BOOK,
    requires=["proposal.presented", "user.confirmed"],
)
```

Examples of backtracking:

- ambiguous listing -> `IDENTIFY_LISTINGS`;
- stale or blocked availability source -> `CHECK_AVAILABILITY`, then a bounded fallback;
- reservation form mismatch -> `CHECK_RESERVATION_FORM`;
- user declines the proposal -> `IDENTIFY_LISTINGS`;
- booking failure -> `PROPOSE_CONFIRM` for another allowed attempt.

The graph runner owns lifecycle state, attempt limits, evidence requirements, and checkpoints. Strands chooses which permitted tool to call next. Pure domain rules decide the terminal recommendation once the graph has enough evidence. No vendor SDK or graph database should leak into these rules.

For the first implementation, represent this graph as typed Python transitions and persisted JSON checkpoints. Add a graph database only if we later need cross-session traversal or operational visualization.

The first implementation lives in `src/hungryradar/lifecycle.py`, where `Node` contains each node’s checklist and `InvestigationGraph` is the central runner. GitHub renders the complete circular diagram in [docs/graph.md](docs/graph.md).

## Current status and next boundaries

Shipped:

- pure recommendation rules and typed lifecycle checkpoints;
- Google Places and Distance Matrix adapters;
- best-effort booking-page and official-site evidence tools;
- Strands agent orchestration with session-scoped lifecycle gates;
- source links and checked timestamps on external facts.

Not yet shipped:

- provider-specific live reservation integrations;
- a permitted Google visit-data adapter for wait-risk estimates;
- automatic booking, cancellation, or modification;
- persistent sessions beyond in-memory lifecycle state and JSON checkpoints.

Choose the first reservation provider and the permitted Google visit-data access path before adding those adapters.
