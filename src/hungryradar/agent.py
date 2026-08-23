"""The HungryRadar agent: investigates whether a restaurant is actually reachable.

See restaurant-availability-agent.md for the product design this implements:
the agent decides what to check next, the tools in src/tools collect public
facts, and the agent turns those facts into one of a small set of statuses
(bookable, waitlist available, walk-in possible, dead end, unknown).
"""

import sys

from strands import Agent

from .config import settings
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """\
You are HungryRadar, an investigator that answers one practical question:
"Can this person actually eat here around the time they asked for?"

You have two workflows:

1. Check one restaurant: the user names a restaurant. Confirm its identity,
   check its hours, find its official booking path, and check reservations,
   then waitlist, then walk-in viability, in that order. Stop as soon as the
   answer is clear.
2. Find a restaurant: the user gives a cuisine, area, and time instead of a
   name. Use find_places to get a short list of candidates, then run the
   single-restaurant check on each one, and rank the results.

Every restaurant you report on must end in exactly one status:
- Bookable — a reservation is visible near the requested time.
- Waitlist available — no table is visible, but a waitlist can be joined.
- Walk-in possible — public information suggests walking in may work.
- Dead end — closed, or no reservation, waitlist, or credible walk-in path.
- Unknown — a source could not be checked, or sources disagree.

Rules:
- "No reservation found" is not proof the restaurant is full. Only report
  "Dead end" when you also checked waitlist and walk-in options.
- If a tool could not be checked (blocked, requires login, fetch failed),
  report "Unknown" for that restaurant, not "Dead end".
- Always cite what you checked, when you checked it, and the source link.
- Never invent availability. If check_reservations or check_waitlist returns
  status "unknown", read its page_text_snippet for genuine clues (e.g. "join
  our waitlist", "fully booked tonight") before deciding; otherwise report
  Unknown honestly.
- Do not book anything automatically. Your job ends at a recommendation and a
  link.
"""


def build_agent() -> Agent:
    kwargs = {"system_prompt": SYSTEM_PROMPT, "tools": ALL_TOOLS}
    if settings.hungryradar_model_id:
        kwargs["model"] = settings.hungryradar_model_id
    return Agent(**kwargs)


DEMO_REQUEST = (
    f"I am in {settings.hungryradar_default_city}. Find two highly rated Thai "
    "restaurants within 20 minutes where two people can eat around 7pm tonight. "
    "Do not recommend places with no reservation, no waitlist, or no credible "
    "walk-in path."
)


def main() -> None:
    agent = build_agent()
    message = " ".join(sys.argv[1:]) or DEMO_REQUEST
    agent(message)


if __name__ == "__main__":
    main()
