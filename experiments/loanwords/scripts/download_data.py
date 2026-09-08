"""Step 1 — fetch the candidate loan-word sources and cache them.

Writes one JSON file per source into `data/` (gitignored), plus a manifest
recording what was fetched and when. Nothing here decides anything; it only
puts the raw material on disk so `coverage.py` can be re-run without touching
the network.

Three sources, because the licence question depends on how much each yields:

* **en.wiktionary `Hungarian terms borrowed from *`** — conscious borrowings.
  CC BY-SA 4.0.
* **en.wiktionary `Hungarian terms derived from *`** — the wider net, including
  inherited vocabulary and indirect descent. CC BY-SA 4.0.
* **Wikidata lexemes** — CC0, and the only genuinely public-domain option.

The two sources the original specification named do **not** exist:
`Category:Hungarian_loanwords` on en.wiktionary is empty, and hu.wiktionary has
no etymology categories at all — its category tree is bilingual dictionaries
(`magyar-X szótár`). Verified 2026-09-08; see `../README.md`.

Usage:
    uv run python experiments/loanwords/scripts/download_data.py
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_DIR, log  # noqa: E402
from wiktionary import USER_AGENT, categories, members  # noqa: E402

WIKI = "en.wiktionary.org"
PREFIXES = {
    "borrowed": "Hungarian terms borrowed from",
    "derived": "Hungarian terms derived from",
    "learned": "Hungarian learned borrowings from",
    "orthographic": "Hungarian orthographic borrowings from",
    "semantic": "Hungarian semantic loans from",
}
WIKIDATA_QUERY = """
SELECT ?lemma ?source WHERE {
  ?l dct:language wd:Q9067 ; wikibase:lemma ?lemma .
  OPTIONAL { ?l wdt:P5191 ?src . ?src wikibase:lemma ?source . }
}
"""


def fetch_wiktionary() -> None:
    """Cache the members of every Hungarian borrowing category."""
    for key, prefix in PREFIXES.items():
        out = DATA_DIR / f"wiktionary-{key}.json"
        if out.exists():
            log("wiktionary", f"Already cached → {out}")
            continue
        found = categories(WIKI, prefix)
        log("wiktionary", f"{key}: {len(found)} categories")
        record: dict[str, list[str]] = {}
        for name, size in found:
            if size == 0:
                continue
            donor = name[len(prefix) :].strip()
            record[donor] = sorted(members(WIKI, name))
            log("wiktionary", f"  {donor}: {len(record[donor])}")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True))
        log("wiktionary", f"{sum(map(len, record.values()))} entries → {out}")


def fetch_wikidata() -> None:
    """Cache every Hungarian lexeme Wikidata knows about."""
    out = DATA_DIR / "wikidata-lexemes.json"
    if out.exists():
        log("wikidata", f"Already cached → {out}")
        return
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": WIKIDATA_QUERY, "format": "json"}
    )
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/sparql-results+json",
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:  # noqa: S310
        payload = json.load(response)
    rows = [
        {
            "lemma": row["lemma"]["value"],
            "source": row.get("source", {}).get("value"),
        }
        for row in payload["results"]["bindings"]
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    log("wikidata", f"{len(rows)} lexemes → {out}")


def main() -> None:
    """Fetch every source."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fetch_wiktionary()
    fetch_wikidata()
    log("done", f"Sources cached in {DATA_DIR}")


if __name__ == "__main__":
    main()
