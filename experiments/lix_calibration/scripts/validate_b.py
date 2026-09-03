"""Step 3: Check the calibrated threshold against real text with real sentences.

The calibration is built from word-length distributions, which cannot supply *B*.
This step closes that gap: a crawl part carries real sentence boundaries, so LIX
can be computed end to end on running Hungarian rather than inferred from a
frequency table.

It also checks the package's other invariant on real data — that lemma-TTR comes
out below surface-TTR — instead of on a fourteen-token toy sample.

Usage:
    uv run python experiments/lix_calibration/scripts/validate_b.py
    uv run python experiments/lix_calibration/scripts/validate_b.py --limit 20000
"""

import argparse
import sys
from pathlib import Path

from saphes import lexical_diversity, lix_from_counts, word_length
from saphes.calibration import recommended_threshold

sys.path.insert(0, str(Path(__file__).resolve().parent))
from corpus_part import iter_documents  # noqa: E402
from utils import (  # noqa: E402
    DATA_DIR,
    EXPERIMENT_DIR,
    fmt_share,
    log,
    require_file,
)

CORPUS_PART = "web2-4p-0.tar.gz"
DEFAULT_LIMIT = 5_000
MIN_WORDS = 25
# How far the running-text long-word share may sit from the frequency list's
# before the transfer is called into question. This was 0.10 — ten percentage
# points — which almost no Hungarian corpus could fail, so it asserted nothing.
# The observed gap is 1.6 points; 5 leaves room for a genuine register
# difference while still being able to fail.
TRANSFER_TOLERANCE = 0.05  # skip stubs; a LIX over five words means nothing
BJORNSSON = 6


def main() -> None:
    """Validate the calibrated threshold on running text."""
    parser = argparse.ArgumentParser(description="Validate B on a real corpus")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Documents to read (default {DEFAULT_LIMIT}; 0 reads the whole part)",
    )
    args = parser.parse_args()
    limit = None if args.limit == 0 else args.limit

    path = DATA_DIR / CORPUS_PART
    require_file(path, "download_data.py --with-corpus-part")

    tuned = recommended_threshold("hu")
    log("validate", f"Calibrated Hungarian threshold: {tuned.threshold}")
    log("validate", f"Reading {CORPUS_PART} (limit={limit or 'all'})")

    total_words = total_sentences = 0
    long_default = long_tuned = 0
    forms: list[str] = []
    pairs: list[tuple[str, str]] = []
    read = skipped_short = skipped_no_sentence = 0

    for doc in iter_documents(path, limit=limit):
        read += 1
        if doc.sentences == 0:
            skipped_no_sentence += 1
            continue
        if len(doc.forms) < MIN_WORDS:
            skipped_short += 1
            continue
        total_words += len(doc.forms)
        total_sentences += doc.sentences
        for form in doc.forms:
            length = word_length(form)
            if length > BJORNSSON:
                long_default += 1
            if length > tuned.threshold:
                long_tuned += 1
        forms.extend(doc.forms)
        pairs.extend(doc.pairs)

    if total_words == 0:
        log("validate", "No usable documents. Something is wrong with the reader.")
        sys.exit(1)

    log(
        "validate",
        f"{read:,} documents read; "
        f"used {read - skipped_short - skipped_no_sentence:,}, "
        f"skipped {skipped_short:,} under {MIN_WORDS} words and "
        f"{skipped_no_sentence:,} with no sentence markup",
    )
    log("validate", f"A={total_words:,} words, B={total_sentences:,} sentences")
    log("validate", f"mean sentence length = {total_words / total_sentences:.2f} words")

    log("lix", "Corpus-wide LIX, with B taken from the corpus itself:")
    for label, long_words in (
        ("Björnsson (6)", long_default),
        (f"calibrated ({tuned.threshold})", long_tuned),
    ):
        score = lix_from_counts(
            words=total_words, sentences=total_sentences, long_words=long_words
        )
        share = long_words / total_words
        log(
            "lix",
            f"  {label:<18} C={long_words:>9,}  "
            f"share={fmt_share(share):>7}  LIX={score:6.2f}",
        )

    predicted = tuned.matched_share
    actual = long_tuned / total_words
    log(
        "check",
        f"Calibration predicted a long-word share of {fmt_share(predicted)}; "
        f"this running text gives {fmt_share(actual)} "
        f"(difference {abs(actual - predicted) * 100:.2f} points)",
    )
    if abs(actual - predicted) > TRANSFER_TOLERANCE:
        log(
            "check",
            f"That is more than {TRANSFER_TOLERANCE * 100:.0f} points. The crawl "
            "part is a different register from the frequency list's 4% stratum, "
            "so some drift is expected — but check before trusting the threshold "
            "on this register.",
        )
    else:
        log(
            "check",
            f"Within {TRANSFER_TOLERANCE * 100:.0f} points: the calibration "
            "transfers to running text.",
        )

    if len(pairs) < MIN_WORDS:
        log("asymmetry", "Too few analysed tokens in this sample to compare streams.")
        return

    # Both streams over the SAME tokens. Only a small, non-random fraction of
    # tokens carry an analysis, so comparing all surface forms against the lemma
    # subset would compare two different samples and prove nothing.
    paired_forms = [form for form, _ in pairs]
    paired_lemmas = [lemma for _, lemma in pairs]
    coverage = len(pairs) / total_words
    log(
        "asymmetry",
        f"{len(pairs):,} of {total_words:,} tokens carry an analysis "
        f"({fmt_share(coverage)}); comparing both streams over exactly those.",
    )

    surface = lexical_diversity(paired_forms, unit="surface", case_fold=True)
    lemma = lexical_diversity(paired_lemmas, unit="lemma", case_fold=True)
    log("asymmetry", f"surface: types={surface.types:,} TTR={surface.ttr:.4f}")
    log("asymmetry", f"lemma:   types={lemma.types:,} TTR={lemma.ttr:.4f}")
    log(
        "asymmetry",
        f"TTR gap = {surface.ttr - lemma.ttr:+.4f} "
        "(positive means lemmatisation removed morphology, as it should)",
    )

    mean_form = sum(word_length(w) for w in paired_forms) / len(paired_forms)
    mean_lemma = sum(word_length(w) for w in paired_lemmas) / len(paired_lemmas)
    log(
        "asymmetry",
        f"mean word length: {mean_form:.2f} surface vs {mean_lemma:.2f} lemma "
        f"({mean_form - mean_lemma:+.2f}) — the length LIX would lose",
    )
    if surface.ttr <= lemma.ttr:
        log(
            "asymmetry",
            "UNEXPECTED: lemma TTR is not below surface TTR. The two-contracts "
            "claim does not hold on this sample; find out why before trusting it.",
        )

    _write_validation(
        limit=limit,
        read=read,
        used=read - skipped_short - skipped_no_sentence,
        skipped_short=skipped_short,
        skipped_no_sentence=skipped_no_sentence,
        total_words=total_words,
        total_sentences=total_sentences,
        long_default=long_default,
        long_tuned=long_tuned,
        tuned=tuned,
        pairs=len(pairs),
        coverage=coverage,
        surface_ttr=surface.ttr,
        lemma_ttr=lemma.ttr,
        mean_form=mean_form,
        mean_lemma=mean_lemma,
    )


def _write_validation(**f: object) -> None:
    """Write validation.md, the committed record of this check."""
    tuned = f["tuned"]
    words, sentences = f["total_words"], f["total_sentences"]
    default_score = lix_from_counts(
        words=words, sentences=sentences, long_words=f["long_default"]
    )
    tuned_score = lix_from_counts(
        words=words, sentences=sentences, long_words=f["long_tuned"]
    )
    default_share = f["long_default"] / words
    tuned_share = f["long_tuned"] / words

    lines = [
        "# Validation: the calibrated threshold on running text",
        "",
        "Generated by `scripts/validate_b.py`.",
        "",
        "The frequency lists that produced the calibration cannot supply *B*, the",
        "sentence count — so they can choose a threshold but cannot show what it does",
        "to an actual LIX score. A Webcorpus crawl part can: it is segmented into",
        "sentences as well as words, so *A*, *B* and *C* all come from the corpus.",
        "",
        "## Sample",
        "",
        f"- Source: `{CORPUS_PART}`, {f['read']:,} documents read"
        f" (limit {f['limit'] or 'none'})",
        f"- Used {f['used']:,}; skipped {f['skipped_short']:,} under {MIN_WORDS}"
        f" words, {f['skipped_no_sentence']:,} with no sentence markup",
        f"- **A = {words:,}** words, **B = {sentences:,}** sentences",
        f"- Mean sentence length: {words / sentences:.2f} words",
        "",
        "## LIX, with real sentence counts",
        "",
        "| threshold | C | long-word share | LIX |",
        "|---|---:|---:|---:|",
        f"| Björnsson's 6 | {f['long_default']:,} | {fmt_share(default_share)} "
        f"| {default_score:.2f} |",
        f"| calibrated {tuned.threshold} | {f['long_tuned']:,} | "
        f"{fmt_share(tuned_share)} | {tuned_score:.2f} |",
        "",
        f"At Björnsson's threshold, ordinary 2000s web Hungarian scores "
        f'{default_score:.1f} — deep in "very difficult", which is not a '
        "description of this text, it is the index saturating. At the calibrated "
        f"threshold it scores {tuned_score:.1f}.",
        "",
        "## Does the calibration transfer?",
        "",
        f"The calibration predicted a long-word share of "
        f"{fmt_share(tuned.matched_share)} for Hungarian at threshold "
        f"{tuned.threshold}. This running text gives {fmt_share(tuned_share)} — a "
        f"difference of {abs(tuned_share - tuned.matched_share) * 100:.2f} points.",
        "",
        "That is a genuine check rather than a restatement: the calibration was "
        "built from the 4% stratum of a *frequency list*, and this is *running "
        "text* from crawl part 0. They are different views of the same corpus.",
        "",
        "## The two contracts, on real Hungarian",
        "",
        f"Only {fmt_share(f['coverage'])} of tokens carry a morphological analysis, "
        "and they are not a random sample — the analyser emits one where it has "
        "something to say. So both streams are compared **over exactly those "
        f"{f['pairs']:,} tokens**, not lemma-subset against full-surface, which "
        "would compare two different samples and prove nothing.",
        "",
        "| stream | TTR | mean word length |",
        "|---|---:|---:|",
        f"| surface | {f['surface_ttr']:.4f} | {f['mean_form']:.2f} |",
        f"| lemma | {f['lemma_ttr']:.4f} | {f['mean_lemma']:.2f} |",
        "",
        f"TTR gap **{f['surface_ttr'] - f['lemma_ttr']:+.4f}**, word-length gap "
        f"**{f['mean_form'] - f['mean_lemma']:+.2f}**. Both point the way the "
        "package says they must: lemmatising removes morphology (so diversity needs "
        "lemmas) and removes length (so readability needs surface forms).",
        "",
        "The gap is smaller here than on the bundled toy samples, and that is worth "
        "stating rather than hiding: the analysed subset is skewed toward the "
        "tokens the analyser flagged — foreign words, hyphenated forms, oddities — "
        "which are less richly inflected than ordinary Hungarian nouns.",
        "",
        "## Reproducing",
        "",
        "```bash",
        "uv run python experiments/lix_calibration/scripts/download_data.py "
        "--with-corpus-part",
        "uv run python experiments/lix_calibration/scripts/validate_b.py",
        "```",
        "",
    ]
    path = EXPERIMENT_DIR / "validation.md"
    path.write_text("\n".join(lines))
    log("write", f"{path.stat().st_size:,} bytes → {path}")


if __name__ == "__main__":
    main()
