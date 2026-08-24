"""Fetches a public web page and returns its visible text or its links.

Reservation platforms (OpenTable, Resy, Tock, ...) expose no shared public
availability API, so every booking-related tool reduces to this: fetch a
page, strip markup, hand the agent text or links to read for itself. See
README.md#implementation-notes.
"""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

_USER_AGENT = "HungryRadarBot/0.1 (restaurant availability checks)"


def fetch_page_text(url: str, *, max_chars: int = 4000) -> dict:
    try:
        response = httpx.get(
            url, headers={"User-Agent": _USER_AGENT}, timeout=10.0, follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"source_uri": url, "fetched": False, "error": str(exc), "page_text_snippet": ""}

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.get_text(separator=" ").split())

    return {"source_uri": url, "fetched": True, "page_text_snippet": text[:max_chars]}


def find_links_by_domain(url: str, domains: tuple[str, ...]) -> dict:
    try:
        response = httpx.get(
            url, headers={"User-Agent": _USER_AGENT}, timeout=10.0, follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"source_uri": url, "fetched": False, "error": str(exc), "links": []}

    soup = BeautifulSoup(response.text, "html.parser")
    links = {
        anchor["href"]
        for anchor in soup.find_all("a", href=True)
        if any(domain in anchor["href"] for domain in domains)
    }

    return {"source_uri": url, "fetched": True, "links": sorted(links)}
