"""A minimal, polite MediaWiki category reader.

Stdlib only, one request at a time, with a descriptive User-Agent and a delay
between calls. The Wikimedia API etiquette guidelines ask for both; this study
reads a few hundred pages and has no reason to go faster.
"""

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Iterator

USER_AGENT = (
    "saphes-loanword-study/0.1 "
    "(https://github.com/crow-intelligence/saphes; hello@crowintelligence.org)"
)
DELAY = 0.2


def api(wiki: str, params: dict[str, str]) -> dict:
    """Call the MediaWiki API once and return the decoded JSON."""
    url = f"https://{wiki}/w/api.php?" + urllib.parse.urlencode(
        {**params, "format": "json", "formatversion": "2"}
    )
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = json.load(response)
    time.sleep(DELAY)
    return payload


def categories(wiki: str, prefix: str) -> list[tuple[str, int]]:
    """Return every category whose title starts with `prefix`, with its size."""
    found: list[tuple[str, int]] = []
    continue_at: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "allcategories",
            "acprefix": prefix,
            "aclimit": "500",
            "acprop": "size",
        }
        if continue_at:
            params["accontinue"] = continue_at
        payload = api(wiki, params)
        for entry in payload["query"]["allcategories"]:
            found.append((entry["category"], entry["size"]))
        continue_at = payload.get("continue", {}).get("accontinue")
        if not continue_at:
            return found


def members(wiki: str, category: str) -> Iterator[str]:
    """Yield the main-namespace page titles in one category."""
    continue_at: str | None = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": "500",
            "cmnamespace": "0",
        }
        if continue_at:
            params["cmcontinue"] = continue_at
        payload = api(wiki, params)
        for entry in payload["query"]["categorymembers"]:
            yield entry["title"]
        continue_at = payload.get("continue", {}).get("cmcontinue")
        if not continue_at:
            return
