"""Measure LIX across Hungarian registers, and map the interpretation bands.

Two questions the threshold study left open.

**Does the threshold hold outside web and news?** Every corpus in the
calibration is a web crawl or a news wire, yet every caveat it ships tells the
reader that a threshold belongs to a register. This runs the same measurement on
parliamentary speech, corruption journalism and song lyrics.

**What does a Hungarian LIX score mean?** ``LixResult.band`` returns ``None``
away from Bjornsson's 6, because the labels were fitted to Swedish prose. So the
calibrated threshold buys a comparable number with no interpretation. The band
mapping here is the same equipercentile argument as the threshold, one level up:
find the Hungarian score that sits where each Swedish band boundary sits.

The mapping uses the Leipzig pair and nothing else, because equipercentile
matching needs both sides treated identically — same project, same sampling,
same window definition. The register panel is what tests whether the answer
survives contact with other kinds of language.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import saphes
from saphes.hungarian import hungarian_letter_count
from saphes.readability import LIX_BANDS
from saphes.segment import sentences as split_sentences

CALIBRATION_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "lix_calibration" / "scripts"
)
sys.path.insert(0, str(CALIBRATION_SCRIPTS))

from registers import (  # noqa: E402
    LOCAL_REGISTERS,
    TIER_LOCAL,
    TIER_PUBLIC,
    available,
)
from running_text import (  # noqa: E402
    CorpusLix,
    corpus_lix,
    describe,
    read_leipzig_sentences,
)
from utils import DATA_DIR, log, require_file  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parents[1] / "results"

LEIPZIG_SWE = "swe_news_2022_1M.tar.gz"
LEIPZIG_HUN = "hun_news_2022_1M.tar.gz"
BJORNSSON = 6
CALIBRATED = 8
WINDOW = 25
# The window length is arbitrary, so the mapping is recomputed across a range of
# it. A boundary that moves with the window is an artefact of the window.
WINDOW_LADDER = (10, 25, 50, 100)
DEFAULT_LIMIT = 300_000

# The policies each Hungarian register is measured under. Swedish needs no
# letter variant: Swedish orthography has no multi-character letters, so its
# character count already is a letter count.
POLICIES = {"chars": "nfc", "letters": hungarian_letter_count}


def sentences_from_texts(texts: Iterable[str]) -> Iterator[str]:
    """Split whole documents into sentences with the bundled splitter.

    Used only for registers that do not carry their own sentence boundaries.
    Every row in the record says which it was, because the sentence count is
    where LIX implementations disagree.
    """
    for text in texts:
        yield from split_sentences(text)


def measure(
    label: str,
    source: Iterable[str],
    *,
    threshold: int,
    policy: str,
    keep_spans: bool = False,
) -> CorpusLix:
    """One register, one threshold, one length policy.

    ``keep_spans`` is set only for the two curves the band mapping re-windows.
    Retaining a span per sentence for every row of the panel is what made an
    earlier full run run out of memory.
    """
    result = corpus_lix(
        source,
        label=f"{label}@{threshold}-{policy}",
        threshold=threshold,
        length_policy=POLICIES[policy],
        window=WINDOW,
        keep_spans=keep_spans,
    )
    log("measure", result.summary())
    return result


def _quantile(values: tuple[float, ...], fraction: float) -> float:
    """The value at a fraction of a distribution, by nearest rank."""
    ordered = sorted(values)
    return ordered[round(fraction * (len(ordered) - 1))]


def band_map(reference: CorpusLix, target: CorpusLix, size: int) -> list[dict]:
    """Map each Swedish band boundary onto the target's distribution.

    For each boundary, find the fraction of reference windows below it, then
    read the target score at that same fraction. That is equipercentile
    equating: it preserves *how much text falls in each band*, which is what the
    labels were fitted to, rather than preserving the literal cut-point.

    Args:
        reference: The Swedish measurement at Bjornsson's threshold.
        target: The Hungarian measurement at the calibrated threshold.
        size: Sentences per window. Both sides are re-windowed at this size, so
            they stay comparable.
    """
    swedish = sorted(reference.windows_at(size))
    hungarian = target.windows_at(size)
    rows = []
    for upper, label in LIX_BANDS:
        if upper == float("inf"):
            continue
        fraction = sum(1 for score in swedish if score < upper) / len(swedish)
        mapped = _quantile(hungarian, fraction)
        rows.append(
            {
                "band": label,
                "swedish_boundary": upper,
                "fraction_below": round(fraction, 4),
                "mapped_boundary": round(mapped, 2),
                "shift": round(mapped - upper, 2),
            }
        )
    return rows


def main() -> None:
    """Run the panel, map the bands, write the artifacts."""
    parser = argparse.ArgumentParser(description="Hungarian LIX register panel")
    parser.add_argument(
        "--corpus-root",
        type=Path,
        default=Path.home() / "projects",
        help="Where the author-local sibling corpora live",
    )
    parser.add_argument(
        "--tier1-only",
        action="store_true",
        help="Skip the author-local registers entirely",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Sentences or documents per register (default {DEFAULT_LIMIT:,})",
    )
    args = parser.parse_args()

    for name in (LEIPZIG_SWE, LEIPZIG_HUN):
        require_file(DATA_DIR / name, "download_data.py")

    rows: list[dict] = []
    distributions: dict[str, CorpusLix] = {}

    def record(key: str, meta: dict, result: CorpusLix, policy: str) -> None:
        distributions[result.label] = result
        rows.append(
            {
                **meta,
                "register": key,
                "threshold": result.threshold,
                "policy": policy,
                "length_policy": result.length_policy,
                "words": result.words,
                "sentences": result.sentences,
                "long_words": result.long_words,
                "mean_sentence_length": round(result.mean_sentence_length, 3),
                "long_word_share": round(result.long_word_share, 4),
                "lix": round(result.score, 2),
                "windows": len(result.windows),
                "p10": round(result.quantile(0.10), 2),
                "p50": round(statistics.median(result.windows), 2),
                "p90": round(result.quantile(0.90), 2),
            }
        )

    # --- tier 1 -------------------------------------------------------------
    log("tier1", "Leipzig news, Swedish reference and Hungarian target")
    swe_meta = {
        "tier": TIER_PUBLIC,
        "description": "Swedish news, 2022 (the reference)",
        "sentence_source": "corpus",
        "language": "sv",
    }
    reference = measure(
        "leipzig-swe-news",
        read_leipzig_sentences(DATA_DIR / LEIPZIG_SWE, limit=args.limit),
        threshold=BJORNSSON,
        policy="chars",
        keep_spans=True,
    )
    record("leipzig-swe-news", swe_meta, reference, "chars")
    log("tier1", f"  {describe(reference)}")

    hun_meta = {
        "tier": TIER_PUBLIC,
        "description": "Hungarian news, 2022",
        "sentence_source": "corpus",
        "language": "hu",
    }
    for threshold, policy in (
        (BJORNSSON, "chars"),
        (CALIBRATED, "chars"),
        (CALIBRATED, "letters"),
    ):
        result = measure(
            "leipzig-hun-news",
            read_leipzig_sentences(DATA_DIR / LEIPZIG_HUN, limit=args.limit),
            threshold=threshold,
            policy=policy,
            keep_spans=threshold == CALIBRATED,
        )
        record("leipzig-hun-news", hun_meta, result, policy)

    # --- tier 2 -------------------------------------------------------------
    if not args.tier1_only:
        present = available(args.corpus_root)
        for key, (description, reader, supplies) in LOCAL_REGISTERS.items():
            if not present[key]:
                log("tier2", f"SKIP {key}: not found under {args.corpus_root}")
                continue
            meta = {
                "tier": TIER_LOCAL,
                "description": description,
                "sentence_source": "corpus" if supplies else "segmented",
                "language": "hu",
            }
            for threshold, policy in (
                (BJORNSSON, "chars"),
                (CALIBRATED, "chars"),
                (CALIBRATED, "letters"),
            ):
                source = reader(args.corpus_root, limit=args.limit)
                stream = source if supplies else sentences_from_texts(source)
                result = measure(key, stream, threshold=threshold, policy=policy)
                record(key, meta, result, policy)

    # --- band mapping -------------------------------------------------------
    log("bands", "Mapping the Swedish boundaries onto Hungarian at the calibrated 8")
    mappings = {}
    stability: dict[str, dict[str, list[float]]] = {}
    for policy in POLICIES:
        target = distributions.get(f"leipzig-hun-news@{CALIBRATED}-{policy}")
        if target is None:  # pragma: no cover - defensive
            continue
        mappings[policy] = band_map(reference, target, WINDOW)
        stability[policy] = {
            str(size): [
                row["mapped_boundary"] for row in band_map(reference, target, size)
            ]
            for size in WINDOW_LADDER
        }
        for row in mappings[policy]:
            log(
                "bands",
                f"  {policy:<8} {row['band']:<15} {row['swedish_boundary']:>5} "
                f"-> {row['mapped_boundary']:>6} (shift {row['shift']:+.2f})",
            )

    generated = datetime.now(tz=UTC).isoformat(timespec="seconds")
    record_out = {
        "schema_version": 1,
        "generated": generated,
        "saphes_version": saphes.__version__,
        "limit": args.limit,
        "window": WINDOW,
        "reference": reference.label,
        "rows": rows,
        "band_mapping": mappings,
        "band_stability": stability,
        "window_ladder": list(WINDOW_LADDER),
        "caveats": list(CAVEATS),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "registers.json"
    out.write_text(json.dumps(record_out, indent=2, sort_keys=True) + "\n")
    log("write", f"{out.stat().st_size:,} bytes -> {out}")
    _write_findings(record_out)


CAVEATS = (
    "Leipzig sentence collections are sampled and deduplicated, so there are "
    "no documents. Both LIX terms are ratios, so the point estimates are "
    "unbiased, but a window of shuffled sentences is more homogeneous than a "
    "real text and its spread is correspondingly too narrow.",
    "The window length of 25 sentences is a choice, not a measurement. It "
    "changes the spread and therefore the mapped boundaries; the stability "
    "check is in the findings.",
    "Registers marked author-local are not redistributable and this panel "
    "cannot be reproduced for them from a clean checkout. Their numbers are "
    "published; their corpora are not.",
    "A register whose sentence count is marked segmented had its B produced "
    "by the bundled splitter rather than by the corpus. LIX implementations "
    "disagree mostly on B, so those rows are not directly comparable with the "
    "corpus-supplied ones.",
)


def _write_findings(record: dict) -> None:
    """Write findings.md from the record."""
    lines = [
        "# Findings: LIX across Hungarian registers",
        "",
        f"Generated: {record['generated']}  ",
        f"saphes version: {record['saphes_version']}  ",
        f"Window: {record['window']} sentences; limit {record['limit']:,} per register",
        "",
        "---",
        "",
        "## 1. The panel",
        "",
        "| register | tier | B from | thr | policy | A/B | C/A | LIX "
        "| p10 | p50 | p90 |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in record["rows"]:
        lines.append(
            f"| `{row['register']}` | {row['tier']} | {row['sentence_source']} | "
            f"{row['threshold']} | {row['policy']} | "
            f"{row['mean_sentence_length']:.2f} | {row['long_word_share']:.4f} | "
            f"**{row['lix']:.2f}** | {row['p10']:.1f} | {row['p50']:.1f} | "
            f"{row['p90']:.1f} |"
        )

    lines += ["", "---", "", "## 2. Band mapping", ""]
    lines += [
        "Each Swedish band boundary, and the Hungarian score that sits at the "
        "same point of the distribution. A small shift means the shipped labels "
        "transfer at the calibrated threshold; a large one means Hungarian "
        "needs its own.",
        "",
    ]
    for policy, mapping in record["band_mapping"].items():
        lines += [
            f"**Length policy: {policy}**",
            "",
            "| band | Swedish boundary | share below | Hungarian boundary | shift |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in mapping:
            lines.append(
                f"| {row['band']} | {row['swedish_boundary']:.0f} | "
                f"{100 * row['fraction_below']:.1f}% | "
                f"{row['mapped_boundary']:.2f} | {row['shift']:+.2f} |"
            )
        lines.append("")

    lines += ["---", "", "## 3. Stability across window lengths", ""]
    lines += [
        "The same mapping recomputed at other window lengths. A boundary that "
        "moves with the window is telling you about the window, not about "
        "Hungarian.",
        "",
    ]
    bands = [label for upper, label in LIX_BANDS if upper != float("inf")]
    for policy, ladder in record["band_stability"].items():
        lines += [
            f"**Length policy: {policy}**",
            "",
            "| window | " + " | ".join(bands) + " |",
            "|---:|" + "---:|" * len(bands),
        ]
        for size in record["window_ladder"]:
            values = ladder[str(size)]
            lines.append(f"| {size} | " + " | ".join(f"{v:.2f}" for v in values) + " |")
        lines.append("")

    lines += ["---", "", "## 4. Caveats", ""]
    lines += [f"- {c}" for c in record["caveats"]]
    lines += [
        "",
        "---",
        "",
        "## 5. Reproducing",
        "",
        "```bash",
        "uv run python experiments/lix_registers/scripts/run.py --tier1-only",
        "uv run python experiments/lix_registers/scripts/run.py",
        "```",
        "",
        "The first form uses only corpora `download_data.py` fetches, and is "
        "what a clean checkout can run.",
    ]
    out = RESULTS_DIR / "findings.md"
    out.write_text("\n".join(lines) + "\n")
    log("write", f"{out.stat().st_size:,} bytes -> {out}")


if __name__ == "__main__":
    main()
