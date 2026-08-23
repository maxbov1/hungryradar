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

The major components are the domain models and rules, application use cases, provider adapters, Strands orchestration, and the investigation-graph runner described below.

## Data Flow

Place resolution starts with Google Places, availability checks enrich the canonical place record, and the agent returns a recommendation with evidence.

## Target package layout

The current `src/hungryradar` files are the first slice of this layout. Add a directory only when it has a real implementation behind it.

```text
src/hungryradar/
  domain/
    models.py              # Place, request, evidence, recommendation
    rules.py               # Pure reservation and wait-risk rules
  application/
    check_restaurant.py    # Bounded investigation use case
    find_restaurants.py    # Candidate search and ranking use case
  ports/
    places.py              # Our interface to canonical place data
    reservations.py        # Our interface to booking sources
    visit_data.py          # Our interface to wait/popular-times data
    lifecycle.py           # Investigation graph interface
  adapters/
    google_places/         # Google Places API client and mapping
    reservations/          # One adapter per supported booking source
    google_visit_data/     # Permitted Google visit-data access path
  orchestration/
    strands_agent.py       # Strands tools, prompt, and bounded loop
  graph/
    lifecycle.py           # Investigation nodes, edges, and gates
    checkpoints.py         # Evidence snapshots for backtracking/resume
  infrastructure/
    settings.py            # Environment/config loading
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
agent = StrandsAgent(tools=[
    resolve_place,
    get_place_snapshot,
    check_reservations,
    get_visit_data,
    check_walk_in_policy,
    calculate_directions,
])

result = agent.run(user_request)
```

Each tool should call an application service or provider port and return structured facts. The agent may decide what to check next, but the lifecycle runner decides whether the investigation can move to form validation, confirmation, booking, waitlist, no match, or unknown.

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

## First implementation order

1. Keep the current pure models and decision rules.
2. Add a Google Places adapter that maps a selected Place Details response into `Place`.
3. Add an application service that runs the bounded check flow.
4. Add one reservation adapter and one permitted visit-data adapter.
5. Add typed lifecycle transitions, evidence gates, and checkpoints.
6. Put Strands on top of the graph runner and expose only permitted next-step tools.

`TODO`: choose the first reservation provider and the permitted Google visit-data access path before implementing those adapters.
