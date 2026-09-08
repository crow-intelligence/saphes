"""Step 3 — build the candidate list a human adjudicates against Bakos.

Writes `results/candidates.tsv`: one row per lemma, with its donor languages,
its donor-era stratum, and its frequency in the MOKK Webcorpus. **It decides
nothing.** The verdict column is empty, to be filled in by a Hungarian speaker
working against Bakos Ferenc, *Idegen szavak és kifejezések szótára* — the same
candidates-then-decisions pattern `experiments/hungarian_boundaries/` used for
the morpheme-boundary table.

Frequency is attached so the list can be worked in the order that matters.
Adjudicating the top few hundred by corpus frequency settles most of the running
text; the long tail is mostly technical vocabulary nobody will meet.

The frequency list is the one the LIX calibration already downloads, read from
`experiments/lix_calibration/data/`. If it is absent the script still runs and
every frequency is 0, which is worse but not fatal.

Usage:
    uv run python experiments/loanwords/scripts/download_data.py
    uv run python experiments/loanwords/scripts/build_candidates.py
"""

import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from coverage import ANCIENT_DONORS, MODERN_DONORS, classify  # noqa: E402
from utils import DATA_DIR, RESULTS_DIR, log, require_file  # noqa: E402

FREQ = (
    Path(__file__).resolve().parents[2]
    / "lix_calibration"
    / "data"
    / "web2.2-freq-sorted.txt.gz"
)
SOURCES = ("borrowed", "learned", "orthographic", "semantic")


def frequencies() -> dict[str, int]:
    """Read the MOKK frequency list, or return an empty mapping if absent.

    Contract:
        Silences:

        - **A missing frequency file is not an error.** Every frequency comes
          back 0 and the candidate list is still usable, just unordered. The
          log line says so.
    """
    if not FREQ.exists():
        log("freq", f"No frequency list at {FREQ}; frequencies will all be 0")
        return {}
    counts: dict[str, int] = {}
    with gzip.open(FREQ, "rt", encoding="iso-8859-2", errors="replace") as handle:
        for line in handle:
            parts = line.split()
            if len(parts) < 2:
                continue
            word, raw = parts[0], parts[1]
            # The MOKK list marks some entries with a trailing asterisk; the
            # calibration study documents why they are kept.
            word = word.rstrip("*").casefold()
            if not raw.isdigit():
                continue
            counts[word] = counts.get(word, 0) + int(raw)
    log("freq", f"{len(counts):,} word forms")
    return counts


def main() -> None:
    """Write results/candidates.tsv."""
    rows: dict[str, dict[str, set[str]]] = {}
    for source in SOURCES:
        path = DATA_DIR / f"wiktionary-{source}.json"
        require_file(path, "download_data.py")
        for donor, titles in json.loads(path.read_text()).items():
            for title in titles:
                lemma, _ = classify(title)
                if not lemma:
                    continue
                entry = rows.setdefault(lemma, {"donors": set(), "sources": set()})
                entry["donors"].add(donor)
                entry["sources"].add(source)

    counts = frequencies()

    def stratum(donors: set[str]) -> str:
        if donors & MODERN_DONORS:
            return "modern"
        if donors & ANCIENT_DONORS:
            return "ancient"
        return "unclassified"

    ordered = sorted(
        rows.items(),
        key=lambda kv: (-counts.get(kv[0], 0), kv[0]),
    )
    lines = ["lemma\tfreq\tstratum\tdonors\tsources\tverdict\tnote"]
    for lemma, entry in ordered:
        lines.append(
            "\t".join(
                (
                    lemma,
                    str(counts.get(lemma, 0)),
                    stratum(entry["donors"]),
                    "|".join(sorted(entry["donors"])),
                    "|".join(sorted(entry["sources"])),
                    "",
                    "",
                )
            )
        )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "candidates.tsv"
    out.write_text("\n".join(lines) + "\n")
    log("write", f"{len(ordered):,} candidates → {out}")


if __name__ == "__main__":
    main()
