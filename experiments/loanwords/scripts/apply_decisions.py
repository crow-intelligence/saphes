"""Step 4 — turn adjudicated verdicts into a lexicon.

Reads `results/decisions.tsv` — `candidates.tsv` with the `verdict` column
filled in — and writes `results/idegenszavak.txt`, one accepted lemma per line.

**It makes no linguistic judgement.** Every verdict comes from a human working
against Bakos Ferenc, *Idegen szavak és kifejezések szótára*; this script only
tallies them and reports what is still unadjudicated. It refuses to run at all
if `decisions.tsv` does not exist, rather than inventing a default.

Verdicts:

* ``accept`` — Bakos lists it; it is an *idegen szó*.
* ``reject`` — Bakos does not list it. Includes the assimilated borrowings
  (*jövevényszavak*) the donor-era proxy cannot separate: the Latin month
  names, `iskola`, `autó`.
* ``unsure`` — needs a second opinion. Counted, never shipped.
* empty — not yet reviewed. Counted, never shipped.

Nothing here writes into `src/`. Whether the resulting list may be committed at
all is a separate question about Wiktionary's CC BY-SA licence against saphes's
MIT, open in `../README.md`.

Usage:
    uv run python experiments/loanwords/scripts/build_candidates.py
    # ... adjudicate candidates.tsv -> decisions.tsv by hand ...
    uv run python experiments/loanwords/scripts/apply_decisions.py
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import RESULTS_DIR, log  # noqa: E402

DECISIONS = RESULTS_DIR / "decisions.tsv"
OUT = RESULTS_DIR / "idegenszavak.txt"
ACCEPTED = "accept"
KNOWN = frozenset({ACCEPTED, "reject", "unsure", ""})


def main() -> None:
    """Tally the verdicts and write the accepted lemmas."""
    if not DECISIONS.exists():
        log("input", f"Missing {DECISIONS}")
        log(
            "input",
            "Adjudicate results/candidates.tsv against Bakos, fill in the "
            "verdict column, and save it as results/decisions.tsv.",
        )
        sys.exit(1)

    rows = DECISIONS.read_text().splitlines()
    if not rows:
        log("input", "decisions.tsv is empty")
        sys.exit(1)

    header = rows[0].split("\t")
    try:
        lemma_at, verdict_at = header.index("lemma"), header.index("verdict")
        freq_at = header.index("freq")
    except ValueError:
        log(
            "input",
            f"decisions.tsv needs lemma, freq and verdict columns; got {header}",
        )
        sys.exit(1)

    verdicts: Counter = Counter()
    accepted: list[str] = []
    accepted_freq = 0
    total_freq = 0
    unknown: set[str] = set()

    for line in rows[1:]:
        if not line.strip():
            continue
        fields = line.split("\t")
        lemma = fields[lemma_at].strip()
        verdict = (
            fields[verdict_at].strip().casefold() if len(fields) > verdict_at else ""
        )
        frequency = int(fields[freq_at]) if fields[freq_at].isdigit() else 0
        if verdict not in KNOWN:
            unknown.add(verdict)
            continue
        verdicts[verdict or "unreviewed"] += 1
        total_freq += frequency
        if verdict == ACCEPTED:
            accepted.append(lemma)
            accepted_freq += frequency

    if unknown:
        log("verdict", f"Unrecognised verdicts, ignored: {sorted(unknown)}")
        log("verdict", f"Recognised values are {sorted(KNOWN - {''})} or empty")

    for verdict, count in verdicts.most_common():
        log("verdict", f"{verdict}: {count}")

    reviewed = sum(count for name, count in verdicts.items() if name != "unreviewed")
    log("verdict", f"{reviewed}/{sum(verdicts.values())} adjudicated")
    if total_freq:
        share = accepted_freq / total_freq
        log(
            "verdict", f"accepted lemmas carry {share:.1%} of candidate token frequency"
        )

    if not accepted:
        log("write", "Nothing accepted yet; no lexicon written")
        return

    OUT.write_text("\n".join(sorted(accepted)) + "\n")
    log("write", f"{len(accepted)} lemmas → {OUT}")


if __name__ == "__main__":
    main()
