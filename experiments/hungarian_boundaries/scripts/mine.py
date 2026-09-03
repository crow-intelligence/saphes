"""Mine candidate morpheme boundaries for the Hungarian letter counter.

Hungarian writes nine letters with more than one character, and a compound seam
can put those characters next to each other without them being that letter:
`község` is `köz` + `ség`, so its `zs` is two letters. Nothing in the string
says so, and no error is raised — the count just comes out one too low.

This script proposes candidates. It does not decide them.

## What the corpus can and cannot establish

It CAN attest that a string occurs, at what token frequency, and that both
halves of a proposed split occur as free-standing words. That is real evidence
and it is what the ranking is built on.

It CANNOT establish that a boundary is there. `kincsásó` (`kincs` + `ásó`, a
real `cs`) and `gerincsérv` (`gerinc` + `sérv`, a false one) are structurally
identical strings; only a morphological analyser separates them, and adding one
is the dependency saphes declines to take. It also cannot tell a live derivation
from a frozen lexicalised noun.

The crawl part's `<lemma>` annotations do not help either, and it is worth
recording why: they cover well under 1% of tokens, and they are not a random
sample — the analyser emits them mostly on tokens it could *not* handle.

So the output is a review queue with a blank `decision` column, and nothing
reaches `saphes.hungarian.MORPHEME_BOUNDARIES` without a human filling it in.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

CALIBRATION_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "lix_calibration" / "scripts"
)
sys.path.insert(0, str(CALIBRATION_SCRIPTS))

from freqlist import read_mokk  # noqa: E402
from utils import DATA_DIR, log, require_file  # noqa: E402

from saphes.hungarian import hungarian_letter_count  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

SMOKE_FILE = "web2.2-freq-sorted.top100k.txt"
FULL_FILE = "web2.2-freq-sorted.txt.gz"

# A half only counts as evidence if it is a word in its own right at this
# frequency. Lower it and every frequent string finds a spurious split.
FREE_FLOOR = 100
# Candidates below this are not worth a reviewer's time; they cannot move any
# corpus-level number.
CANDIDATE_FLOOR = 50
MIN_HALF = 3
REPORT_LIMIT = 120


def raw_count(word: str) -> int:
    """Letter count with no boundary knowledge at all."""
    return hungarian_letter_count(word, boundaries={}, suffix_rule=False)


def compound_candidates(
    freq: dict[str, int], free: set[str]
) -> list[tuple[str, str, int, str, int, str, int]]:
    """Types whose count changes if they are split into two attested words.

    Only splits that change the number are proposed: if reading the seam as a
    boundary gives the same count, there is nothing to fix and no entry is
    needed. That is what keeps the doubled spellings out of here — `vasszeg` is
    six letters under either reading.
    """
    out = []
    for word, count in freq.items():
        if count < CANDIDATE_FLOOR:
            continue
        whole = raw_count(word)
        best = None
        for split in range(MIN_HALF, len(word) - MIN_HALF + 1):
            left, right = word[:split], word[split:]
            if left not in free or right not in free:
                continue
            if raw_count(left) + raw_count(right) <= whole:
                continue
            score = min(freq[left], freq[right])
            # A compound is rarer than either of its parts. Without this the
            # queue fills with monomorphemic words carrying a real digraph:
            # `hiszen` outranks `his` 2000:1 and is plainly not `his` + `zen`.
            # It is a filter on a review queue, not on a result, and it does
            # drop true positives — `fúvószenekar` (734) loses to `fúvós`
            # (661) — so the floor is stated rather than tuned away.
            if count >= score:
                continue
            if best is None or score > best[0]:
                best = (score, left, right)
        if best is not None:
            _, left, right = best
            if hungarian_letter_count(word) == hungarian_letter_count(
                word, boundaries={word: f"{left}-{right}"}
            ):
                continue  # the suffix rule already handles it
            out.append(
                (
                    word,
                    f"{left}-{right}",
                    count,
                    left,
                    freq[left],
                    right,
                    freq[right],
                )
            )
    return sorted(out, key=lambda row: -row[2])


def suffix_rule_exceptions(
    freq: dict[str, int], free: set[str]
) -> list[tuple[str, str, int, str, int, str, int]]:
    """Types where the -ság/-ség rule fires but the digraph is real.

    The rule splits `malacság` into `malac` + `ság` correctly. It cannot see
    that `kavicságy` is `kavics` + `ágy`. The detector is that the prefix
    ending in the *digraph* is an attested word while the prefix ending one
    character earlier is not, and that the remainder is a word too.
    """
    out = []
    for word, count in freq.items():
        if count < CANDIDATE_FLOOR:
            continue
        if hungarian_letter_count(word) == hungarian_letter_count(
            word, suffix_rule=False
        ):
            continue
        for index in range(1, len(word) - 2):
            if word[index] not in "zc" or not word[index + 1 :].startswith("s"):
                continue
            short, long_, rest = word[:index], word[: index + 2], word[index + 2 :]
            if short + word[index] in free or long_ not in free or rest not in free:
                continue
            out.append(
                (word, word, count, long_, freq[long_], rest, freq[rest])
            )
            break
    return sorted(out, key=lambda row: -row[2])


def main() -> None:
    """Mine both candidate classes and write the review queue."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke-test", action="store_true", help="use the 2.8 MB top-100k list"
    )
    args = parser.parse_args()

    name = SMOKE_FILE if args.smoke_test else FULL_FILE
    path = DATA_DIR / name
    require_file(path, "download_data.py")

    log("read", f"reading {name} (4% stratum)")
    counts, report = read_mokk(path)
    log("read", f"{report.types_kept:,} types, {report.tokens_kept:,} tokens")

    freq = dict(counts)
    free = {word for word, count in freq.items() if count >= FREE_FLOOR}
    log("read", f"{len(free):,} types are free-standing at >= {FREE_FLOOR}")

    log("mine", "compound seams")
    compounds = compound_candidates(freq, free)
    log("mine", f"{len(compounds):,} compound candidates")

    log("mine", "suffix-rule false positives")
    exceptions = suffix_rule_exceptions(freq, free)
    log("mine", f"{len(exceptions):,} rule-exception candidates")

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / "candidates.tsv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(
            [
                "kind",
                "candidate",
                "proposed",
                "token_freq",
                "left",
                "left_freq",
                "right",
                "right_freq",
                "count_now",
                "count_if_accepted",
                "decision",
            ]
        )
        for kind, rows in (("compound", compounds), ("rule-exception", exceptions)):
            for word, proposed, count, left, lf, right, rf in rows[:REPORT_LIMIT]:
                if kind == "compound":
                    fixed = hungarian_letter_count(word, boundaries={word: proposed})
                    now = hungarian_letter_count(word)
                else:
                    fixed = hungarian_letter_count(word, suffix_rule=False)
                    now = hungarian_letter_count(word)
                writer.writerow(
                    [kind, word, proposed, count, left, lf, right, rf, now, fixed, ""]
                )

    kept = min(len(compounds), REPORT_LIMIT) + min(len(exceptions), REPORT_LIMIT)
    dropped = len(compounds) + len(exceptions) - kept
    log("write", f"{out} ({kept} rows; {dropped} below the top-{REPORT_LIMIT} cut)")
    log("write", "decision column is blank on purpose — a human fills it in")


if __name__ == "__main__":
    main()
