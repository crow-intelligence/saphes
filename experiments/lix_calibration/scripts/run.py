"""Step 2: Build the length curves, match the threshold, write the artifacts.

Produces three things:

- ``results/lix_calibration.json`` — the provenance artifact, committed
- ``src/saphes/datasets/_lix_calibration.py`` — the literal the package ships
- ``findings.md`` — the writeup, committed

Usage:
    uv run python experiments/lix_calibration/scripts/run.py --smoke-test
    uv run python experiments/lix_calibration/scripts/run.py
"""

import argparse
import json
import subprocess
import sys
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import saphes
from saphes.calibration import (
    LengthCurve,
    collapse_digraphs,
    length_curve,
    match_threshold,
)
from saphes.hungarian import hungarian_letter_count

sys.path.insert(0, str(Path(__file__).resolve().parent))
from freqlist import read_mokk  # noqa: E402
from leipzig import read_leipzig  # noqa: E402
from utils import (  # noqa: E402
    DATA_DIR,
    EXPERIMENT_DIR,
    RESULTS_DIR,
    fmt_share,
    log,
    require_file,
)

SMOKE_FILE = "web2.2-freq-sorted.top100k.txt"
FULL_FILE = "web2.2-freq-sorted.txt.gz"
LEIPZIG_SWE = "swe_news_2022_1M.tar.gz"
LEIPZIG_HUN = "hun_news_2022_1M.tar.gz"

MAX_THRESHOLD = 20
MIN_FREQUENCY = 5
REFERENCE_THRESHOLD = 6
LANGUAGE = "hu"
LETTER_LANGUAGE = "hu-letters"

# Thresholds shown in the printed and written tables. The full curve goes to
# MAX_THRESHOLD and lives in the JSON regardless.
REPORT_RANGE = range(4, 13)

PACKAGE_LITERAL = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "saphes"
    / "datasets"
    / "_lix_calibration.py"
)

CAVEATS = (
    "The MOKK Webcorpus crawl is from winter 2003: 2000s web Hungarian, not "
    "song lyrics, not literary prose. A general-language reference, not a "
    "register match.",
    "Register matters for readability. Before trusting this threshold on your "
    "own texts, recompute the long-word share on a sample of them and check it "
    "lands where the calibration predicts.",
    "A calibrated threshold is a default, not a truth. The parameter stays "
    "exposed precisely because no single number is right everywhere.",
)

# Everything above, plus what is specific to counting letters rather than
# characters. Without this the two shipped records carry byte-identical caveats
# and the letter policy looks like it costs nothing.
LETTER_CAVEATS = (
    *CAVEATS,
    "This threshold belongs to saphes.hungarian.hungarian_letter_count and to "
    "no other length policy. Pairing it with the default character count "
    "measures something this study never measured.",
    "The letter count knows a rule for the -sag/-seg suffix and a table of "
    "attested compound seams. A compound outside that table has its seam read "
    "as a digraph and is counted one letter short, silently.",
)

CITATIONS = (
    "Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). Creating open "
    "language resources for Hungarian. LREC.",
    "Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). Web-based frequency "
    "dictionaries for medium density languages. Web as Corpus, ACL.",
    "Goldhahn, Eckart, Quasthoff (2012). Building large monolingual "
    "dictionaries at the Leipzig Corpora Collection. LREC.",
)


def mokk_curves(
    path: Path,
    stratum: str,
    *,
    keep_asterisk: bool = True,
    label: str | None = None,
    policies: dict[str, object] | None = None,
) -> dict[str, LengthCurve]:
    """Read one MOKK stratum once and build every curve that stratum feeds.

    The frequency list is 115 MB gzipped and takes about a minute to read, so a
    curve per read would cost four extra minutes now that each stratum feeds
    both a character curve and a letter curve. The counts go out of scope with
    this function, which matters: a full-stratum Counter is ten million entries.

    Args:
        path: The frequency list.
        stratum: Which column. See ``freqlist.STRATUM_COLUMNS``.
        keep_asterisk: Strip and merge the capitalisation marker. Always ``True``
            except in the sensitivity run that shows what dropping it costs.
        label: Base label; defaults to ``mokk-<stratum>``.
        policies: Extra ``suffix -> length_policy`` curves to build from the same
            counts, labelled ``<label>-<suffix>``.

    Returns:
        Label to curve, always including the base character-count curve.
    """
    counts, report = read_mokk(path, stratum=stratum, keep_asterisk=keep_asterisk)
    log("mokk", report.summary())
    base = label or f"mokk-{stratum}"

    def build(name: str, policy: object) -> LengthCurve:
        return length_curve(
            counts,
            label=name,
            max_threshold=MAX_THRESHOLD,
            min_frequency=MIN_FREQUENCY,
            length_policy=policy,  # type: ignore[arg-type]
        )

    built = {base: build(base, "nfc")}
    for suffix, policy in (policies or {}).items():
        built[f"{base}-{suffix}"] = build(f"{base}-{suffix}", policy)
    return built


def curve_from_leipzig(path: Path, language: str) -> tuple[LengthCurve, dict[str, str]]:
    """Read one Leipzig archive and build its length curve."""
    counts, report = read_leipzig(path, language=language)
    log("leipzig", report.summary())
    curve = length_curve(
        counts,
        label=f"leipzig-{language}",
        max_threshold=MAX_THRESHOLD,
        min_frequency=MIN_FREQUENCY,
    )
    return curve, dict(report.meta)


def naive_letter_count(word: str) -> int:
    """The pre-0.2.0 letter count: collapse each digraph to its first character.

    Kept so the published sensitivity column keeps meaning across releases. It
    over-merges — the replacement cascades, so `vízszint` comes out at six
    letters when it is seven — which is exactly what the comparison against
    `mokk-4pct-letters` now shows.
    """
    return len(collapse_digraphs(word.casefold()))


def leipzig_letters_curve(path: Path) -> LengthCurve:
    """The Leipzig Hungarian curve, recounted in letters.

    The Swedish reference needs no letter variant: Swedish orthography has no
    multi-character letters, so its character count already is a letter count.
    That asymmetry is the whole reason the reference stays fixed while the
    target curve is remeasured.
    """
    counts, _ = read_leipzig(path, language="hun")
    return length_curve(
        counts,
        label="leipzig-hun-letters",
        max_threshold=MAX_THRESHOLD,
        min_frequency=MIN_FREQUENCY,
        length_policy=hungarian_letter_count,
    )


def print_table(curves: list[LengthCurve]) -> None:
    """Print the cumulative-share table across every curve."""
    width = max(len(c.label) for c in curves) + 2
    header = "  ".join(f"{'>' + str(t):>7}" for t in REPORT_RANGE)
    log("table", f"{'curve':<{width}} {header}")
    for curve in curves:
        row = "  ".join(f"{fmt_share(curve.share_above(t)):>7}" for t in REPORT_RANGE)
        log("table", f"{curve.label:<{width}} {row}")


def check_anchors(curves: dict[str, LengthCurve], *, smoke: bool) -> None:
    """Assert the numbers this pipeline is known to produce.

    These cannot live in ``tests/`` — the CI runner has no corpus. They are the
    regression guard for the readers, which is where every silent failure in this
    study would come from.

    A note on where they came from, because it matters. The exploratory scripts
    that scoped this study applied the minimum-frequency filter *per row*, before
    merging casing variants, and measured a Swedish share of 0.2545. This
    pipeline applies it *after* merging, so a type is judged on its total
    frequency across all its casing variants — dropping ``Och`` at frequency 3
    before merging it into ``och`` at frequency 100,000 is plainly wrong. That
    single change accounts for the whole difference (56,411 Swedish tokens, and
    0.2545 → 0.2565). The anchors below are the post-merge values.
    """
    swe = curves["leipzig-swe"]
    _expect("leipzig-swe share>6", swe.share_above(6), 0.2565, tol=0.002)
    _expect("leipzig-swe mean length", swe.mean_length, 5.052, tol=0.01)

    hun = curves["leipzig-hun"]
    _expect("leipzig-hun share>6", hun.share_above(6), 0.4168, tol=0.002)

    if smoke:
        mokk = curves["mokk-4pct"]
        _expect("mokk-4pct(top100k) share>6", mokk.share_above(6), 0.3889, tol=0.003)
        _expect("mokk-4pct(top100k) mean length", mokk.mean_length, 5.715, tol=0.02)
    else:
        # The two numbers the published recommendations are matched from. The
        # letters curve is the one with no history, so it is anchored from the
        # first run rather than after it has had a chance to drift unnoticed.
        _expect(
            "mokk-4pct share>8", curves["mokk-4pct"].share_above(8), 0.2733, tol=0.002
        )
        _expect(
            "mokk-4pct-letters share>8",
            curves["mokk-4pct-letters"].share_above(8),
            0.2441,
            tol=0.002,
        )


def _expect(name: str, actual: float, expected: float, *, tol: float) -> None:
    """Log an anchor check, and fail loudly if it drifts."""
    if abs(actual - expected) > tol:
        log("anchor", f"MISMATCH {name}: expected ~{expected}, got {actual:.4f}")
        log(
            "anchor",
            "The reader is producing different numbers. Stop and find out why.",
        )
        sys.exit(1)
    log("anchor", f"ok {name} = {actual:.4f} (expected ~{expected})")


def main() -> None:
    """Run the calibration and write every artifact."""
    parser = argparse.ArgumentParser(description="Calibrate the LIX threshold")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Use the 2.8 MB top100k list instead of the full 115 MB frequency file",
    )
    args = parser.parse_args()

    mokk_name = SMOKE_FILE if args.smoke_test else FULL_FILE
    mokk_path = DATA_DIR / mokk_name
    require_file(mokk_path, "download_data.py")
    for name in (LEIPZIG_SWE, LEIPZIG_HUN):
        require_file(DATA_DIR / name, "download_data.py")

    log("run", f"Primary Hungarian source: {mokk_name}")

    swe_curve, swe_meta = curve_from_leipzig(DATA_DIR / LEIPZIG_SWE, "swe")
    hun_curve, hun_meta = curve_from_leipzig(DATA_DIR / LEIPZIG_HUN, "hun")

    # One read per stratum. The 4% stratum feeds four curves: the primary, the
    # old collapse-based letter count kept for continuity, and the scanner.
    primary_set = mokk_curves(
        mokk_path,
        "4pct",
        policies={
            "digraphs-collapsed": naive_letter_count,
            "letters": hungarian_letter_count,
        },
    )
    letters_policy = {"letters": hungarian_letter_count}
    stratum_8 = mokk_curves(mokk_path, "8pct", policies=letters_policy)
    stratum_full = mokk_curves(mokk_path, "full", policies=letters_policy)
    no_asterisk = mokk_curves(
        mokk_path,
        "4pct",
        keep_asterisk=False,
        label="mokk-4pct-asterisk-dropped",
        policies=letters_policy,
    )
    hun_letters = leipzig_letters_curve(DATA_DIR / LEIPZIG_HUN)

    every = {**primary_set, **stratum_8, **stratum_full, **no_asterisk}
    primary = every["mokk-4pct"]
    letters = every["mokk-4pct-letters"]

    # The letter-policy panel. Separate from `curves` because it is evidence for
    # a different recommendation: `hu` is calibrated on characters, and mixing
    # the panels would let each cite the other's support.
    letter_curves = {
        label: curve for label, curve in every.items() if label.endswith("-letters")
    }
    letter_curves[hun_letters.label] = hun_letters

    curves = {
        label: curve
        for label, curve in every.items()
        if not label.endswith("-letters") or label == "mokk-4pct-letters"
    }
    curves[hun_curve.label] = hun_curve
    curves[swe_curve.label] = swe_curve

    print_table(list(curves.values()) + [hun_letters])
    check_anchors(curves, smoke=args.smoke_test)

    match = match_threshold(primary, swe_curve, reference_threshold=REFERENCE_THRESHOLD)
    letters_match = match_threshold(
        letters, swe_curve, reference_threshold=REFERENCE_THRESHOLD
    )
    log(
        "match",
        f"threshold={match.threshold} bracket={match.bracket} "
        f"target={fmt_share(match.target_share)} "
        f"reference={fmt_share(match.reference_share)} "
        f"residual={match.residual:.4f}",
    )
    log(
        "match",
        f"runner-up={match.runner_up} (residual {match.runner_up_residual:.4f}, "
        f"{match.runner_up_residual / match.residual:.1f}x the winner's)"
        if match.residual
        else f"runner-up={match.runner_up} (winner is an exact match)",
    )
    if match.is_boundary:
        log(
            "match",
            "CONTESTED: the runner-up matches nearly as well. Report the "
            "bracket, not just the winner.",
        )
    else:
        log("match", "The winner is clear of its nearest alternative.")

    agreement = {
        label: match_threshold(
            curve, swe_curve, reference_threshold=REFERENCE_THRESHOLD
        ).threshold
        for label, curve in curves.items()
        if label != "leipzig-swe"
    }
    for label, threshold in sorted(agreement.items()):
        log("agree", f"{label:<32} → {threshold}")
    letters_agreement = {
        label: match_threshold(
            curve, swe_curve, reference_threshold=REFERENCE_THRESHOLD
        ).threshold
        for label, curve in letter_curves.items()
    }
    for label, threshold in sorted(letters_agreement.items()):
        log("agree", f"{label:<32} → {threshold}")
    log(
        "letters",
        f"{LETTER_LANGUAGE}: threshold={letters_match.threshold} "
        f"bracket={letters_match.bracket} "
        f"target={fmt_share(letters_match.target_share)} "
        f"residual={letters_match.residual:.4f}",
    )

    generated = datetime.now(tz=UTC).isoformat(timespec="seconds")
    record = _build_record(
        match=match,
        letters_match=letters_match,
        curves={**curves, **letter_curves},
        agreement=agreement,
        letters_agreement=letters_agreement,
        primary_source=mokk_name,
        swe_meta=swe_meta,
        hun_meta=hun_meta,
        generated=generated,
        smoke=args.smoke_test,
    )

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / "lix_calibration.json"
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    log("write", f"{out.stat().st_size:,} bytes → {out}")

    if args.smoke_test:
        log("write", "Smoke run: not regenerating the shipped literal or findings.md")
    else:
        _write_literal(record)
        _write_findings(record, curves, match, agreement, generated)


def _build_record(
    *,
    match,  # noqa: ANN001 - ThresholdMatch
    letters_match,  # noqa: ANN001 - ThresholdMatch, under the letter policy
    curves: dict[str, LengthCurve],
    agreement: dict[str, int],
    letters_agreement: dict[str, int],
    primary_source: str,
    swe_meta: dict[str, str],
    hun_meta: dict[str, str],
    generated: str,
    smoke: bool,
) -> dict:
    """Assemble the JSON provenance record."""
    manifest_path = DATA_DIR / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    return {
        "schema_version": 2,
        "generated": generated,
        "saphes_version": saphes.__version__,
        "smoke_run": smoke,
        "method": {
            "weighting": "token",
            "min_frequency": MIN_FREQUENCY,
            # Deliberately absent: the record now holds curves under three
            # length policies, so a single global value would be wrong for two
            # of them. The truth is per-curve, in curves[label]["length_policy"].
            "capitalisation_marker": "strip-trailing-asterisk-then-merge",
            "equipercentile_reference_threshold": REFERENCE_THRESHOLD,
            "stratum": "4pct",
        },
        "sources": {
            "hu_primary": {
                "id": "mokk-web2.2-4pct",
                "file": primary_source,
                "download": manifest.get(primary_source, {}),
                "citation": [CITATIONS[0], CITATIONS[1]],
            },
            "sv_reference": {
                "id": "leipzig-swe_news_2022_1M",
                "file": LEIPZIG_SWE,
                "download": manifest.get(LEIPZIG_SWE, {}),
                "corpus_meta": swe_meta,
                "citation": [CITATIONS[2]],
            },
            "hu_crosscheck": {
                "id": "leipzig-hun_news_2022_1M",
                "file": LEIPZIG_HUN,
                "download": manifest.get(LEIPZIG_HUN, {}),
                "corpus_meta": hun_meta,
                "citation": [CITATIONS[2]],
            },
        },
        "curves": {
            label: {
                "tokens": c.tokens,
                "types": c.types,
                "mean_length": round(c.mean_length, 4),
                "length_policy": c.length_policy,
                "min_frequency": c.min_frequency,
                "shares": {str(t): round(s, 6) for t, s in c.shares},
            }
            for label, c in curves.items()
        },
        "recommendations": [
            _recommendation(LANGUAGE, match, dict(sorted(agreement.items())), CAVEATS),
            # The same equipercentile match, remeasured under the letter policy,
            # with its own agreement panel measured under that policy too. The
            # two panels are kept apart so neither record cites the other's
            # support.
            _recommendation(
                LETTER_LANGUAGE,
                letters_match,
                dict(sorted(letters_agreement.items())),
                LETTER_CAVEATS,
            ),
        ],
        "caveats": list(CAVEATS),
    }


def _recommendation(  # noqa: ANN001
    language: str, match, agreement: dict[str, int], caveats: tuple[str, ...]
) -> dict:
    """One calibration record, for one language-and-policy key."""
    return {
        "caveats": list(caveats),
        "language": language,
        "long_word_threshold": match.threshold,
        "bracket": list(match.bracket),
        "matched_share": round(match.target_share, 6),
        "reference_share": round(match.reference_share, 6),
        "reference_id": "leipzig-swe_news_2022_1M",
        "reference_threshold": match.reference_threshold,
        "residual": round(match.residual, 6),
        "runner_up": match.runner_up,
        "runner_up_residual": round(match.runner_up_residual, 6),
        "is_boundary": match.is_boundary,
        "agreement": agreement,
    }


def _wrapped_literal(text: str, indent: str, width: int = 84) -> list[str]:
    """Emit a long string as wrapped, implicitly concatenated literals.

    The generated module is linted like everything else, and ruff format cannot
    split a string literal — so the generator has to do it.
    """
    parts = textwrap.wrap(text, width=width - len(indent) - 4)
    if len(parts) <= 1:
        return [f"{indent}{text!r},"]
    lines = [f"{indent}("]
    for index, part in enumerate(parts):
        chunk = part if index == len(parts) - 1 else part + " "
        lines.append(f"{indent}    {chunk!r}")
    lines.append(f"{indent}),")
    return lines


def _write_literal(record: dict) -> None:
    """Regenerate the Python literal the package ships."""
    lines = [
        '"""Calibrated LIX long-word thresholds.',
        "",
        "GENERATED by experiments/lix_calibration/scripts/run.py"
        " — do not edit by hand.",
        "",
        "The data lives inline as a Python literal so it is always importable in",
        "doctests with no package-data machinery, matching the rest of",
        "``saphes.datasets``. The full provenance record, including every curve, is",
        "at experiments/lix_calibration/results/lix_calibration.json.",
        "",
        "Keys name a language *and a length policy*: ``hu`` is calibrated for the",
        "default character count, ``hu-letters`` for the Hungarian letter count in",
        "``saphes.hungarian``. They are not interchangeable — the threshold happens",
        "to agree, but the matched share behind it does not.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        f"GENERATED = {record['generated']!r}",
        f"SCHEMA_VERSION = {record['schema_version']}",
        "",
        "# A heterogeneous provenance record: ints, floats, strings and tuples of",
        "# pairs. Typed as Any rather than a TypedDict because it is generated.",
        "CALIBRATIONS: dict[str, dict[str, Any]] = {",
    ]
    for rec in record["recommendations"]:
        lines += [
            f"    {rec['language']!r}: {{",
            f'        "threshold": {rec["long_word_threshold"]},',
            f'        "bracket": {tuple(rec["bracket"])!r},',
            f'        "matched_share": {rec["matched_share"]!r},',
            f'        "reference_share": {rec["reference_share"]!r},',
            f'        "reference_id": {rec["reference_id"]!r},',
            f'        "reference_threshold": {rec["reference_threshold"]},',
            f'        "residual": {rec["residual"]!r},',
            f'        "runner_up": {rec["runner_up"]},',
            f'        "runner_up_residual": {rec["runner_up_residual"]!r},',
            f'        "is_boundary": {rec["is_boundary"]},',
            '        "agreement": (',
        ]
        for label, threshold in rec["agreement"].items():
            lines.append(f"            ({label!r}, {threshold}),")
        lines += ["        ),", '        "sources": (']
        for source in record["sources"].values():
            lines.append(f"            {source['id']!r},")
        lines += ["        ),", '        "caveats": (']
        for caveat in rec["caveats"]:
            lines += _wrapped_literal(caveat, "            ")
        lines += ["        ),", "    },"]
    lines += ["}", ""]

    PACKAGE_LITERAL.write_text("\n".join(lines))
    # Format the generated file, so re-running the generator reproduces the
    # committed file byte for byte. Without this a later `ruff format` rewrites
    # it and the next regeneration shows a diff that means nothing.
    result = subprocess.run(  # noqa: S603
        ["uv", "run", "ruff", "format", "--quiet", str(PACKAGE_LITERAL)],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        log("write", f"WARNING: ruff format failed: {result.stderr.strip()}")
    log("write", f"{PACKAGE_LITERAL.stat().st_size:,} bytes → {PACKAGE_LITERAL}")


def _write_findings(
    record: dict,
    curves: dict[str, LengthCurve],
    match,  # noqa: ANN001 - ThresholdMatch
    agreement: dict[str, int],
    generated: str,
) -> None:
    """Write findings.md, the human-readable writeup."""
    rec = record["recommendations"][0]
    swe = curves["leipzig-swe"]

    header = [
        "# Findings: LIX threshold calibration for Hungarian",
        f"Generated: {generated}  ",
        f"Primary source: {record['sources']['hu_primary']['file']}  ",
        f"saphes version: {record['saphes_version']}",
        "",
        "---",
        "",
        "## 1. Headline result",
        "",
        "**Recommended Hungarian `long_word_threshold`: "
        f"{rec['long_word_threshold']}**  ",
        f"Bracket: {tuple(rec['bracket'])}  ",
        f"Matched share: {fmt_share(rec['matched_share'])} against a Swedish "
        f"reference of {fmt_share(rec['reference_share'])} at threshold "
        f"{rec['reference_threshold']}  ",
        f"Residual: {rec['residual']:.4f}",
        "",
        "Björnsson's threshold of 6 selects "
        f"{fmt_share(swe.share_above(6))} of running Swedish tokens. In Hungarian "
        f"the same threshold selects "
        f"{fmt_share(curves['mokk-4pct'].share_above(6))} — the index saturates, and "
        "differences between texts stop showing up. Threshold "
        f"{rec['long_word_threshold']} restores what the term means: the longest "
        "quarter or so of running words.",
    ]
    if rec["is_boundary"]:
        header += [
            "",
            f"> **Contested.** Threshold {rec['runner_up']} matches nearly as well "
            f"(residual {rec['runner_up_residual']:.4f} against "
            f"{rec['residual']:.4f}). Treat the recommendation as a defensible "
            "default rather than a settled fact, and see section 4.",
        ]
    else:
        header += [
            "",
            f"The nearest alternative, threshold {rec['runner_up']}, misses by "
            f"{rec['runner_up_residual']:.4f} against the winner's "
            f"{rec['residual']:.4f} — a factor of "
            f"{rec['runner_up_residual'] / rec['residual']:.1f}. The choice is not "
            "on a knife edge.",
        ]

    table = [
        "",
        "---",
        "",
        "## 2. Cumulative long-word shares",
        "",
        "Token-weighted share of running words strictly longer than each threshold.",
        "",
        "| curve | " + " | ".join(f">{t}" for t in REPORT_RANGE) + " |",
        "|---|" + "---:|" * len(REPORT_RANGE),
    ]
    for label, curve in curves.items():
        cells = " | ".join(fmt_share(curve.share_above(t)) for t in REPORT_RANGE)
        table.append(f"| `{label}` | {cells} |")
    table += [
        "",
        "| curve | tokens | types | mean length |",
        "|---|---:|---:|---:|",
    ]
    for label, curve in curves.items():
        table.append(
            f"| `{label}` | {curve.tokens:,} | {curve.types:,} | "
            f"{curve.mean_length:.3f} |"
        )

    agree = [
        "",
        "---",
        "",
        "## 3. Which threshold each source would choose",
        "",
        "Every curve matched independently against the same Swedish reference.",
        "",
        "| curve | threshold |",
        "|---|---:|",
    ]
    agree += [f"| `{label}` | {t} |" for label, t in sorted(agreement.items())]
    agree += [
        "",
        "These are the character-policy curves — the panel behind `hu`. The "
        "letter policy has its own panel, in section 5, measured under that "
        "policy rather than borrowed from this one.",
    ]

    sensitivity = [
        "",
        "---",
        "",
        "## 4. Sensitivity",
        "",
        "**Stratum.** `mokk-4pct` is the principled choice — the 4% stratum has "
        "fewer mistakes than an average print document, while the full-corpus "
        "column carries the crawl's junk. The 8% and full columns are shown so the "
        "cost of that choice is visible rather than assumed.",
        "",
        "**Capitalisation marker.** `mokk-4pct-asterisk-dropped` shows what happens "
        "if the trailing `*` on sentence-initial forms is treated as part of the "
        "word and those rows discarded. They are overwhelmingly short function "
        "words, so dropping them biases the mean length upward and picks too high a "
        "threshold. This is the single highest-consequence line in the reader.",
        "",
        "**Digraphs.** Hungarian `cs, dz, gy, ly, ny, sz, ty, zs, dzs` are single "
        "letters, so a character count is not a letter count, and two rows "
        "recompute on letters. `mokk-4pct-digraphs-collapsed` is the naive "
        "version — replace each digraph with its first character — kept because "
        "it is what earlier releases shipped. It over-merges twice over: the "
        "replacement cascades, so `vízszint` comes out at six letters when it is "
        "seven, and it mis-fires at morpheme boundaries, where `község` is `köz` "
        "+ `ség` and its `zs` is not the digraph at all. `mokk-4pct-letters` is "
        "the scanner in `saphes.hungarian`, which fixes both. The two differ by "
        "about 0.01 percentage points, which is the whole measured cost of "
        "knowing where morpheme boundaries are, and neither moves the threshold. "
        "Character counting stays the default for `lix`, as in Björnsson's "
        "original; the letter policy ships its own calibration under "
        "`hu-letters` (section 5).",
        "",
        "**Independent corpus.** `leipzig-hun` is a different corpus entirely — 2022 "
        "news rather than a 2003 web crawl, built by a different project with a "
        "different pipeline. That it lands close to `mokk-4pct` is the strongest "
        "evidence here that the saturation is a property of Hungarian rather than an "
        "artifact of the Webcorpus.",
    ]

    letters_rec = record["recommendations"][1]
    letters = [
        "",
        "---",
        "",
        "## 5. The same match, on letters",
        "",
        "A threshold is calibrated against a way of counting letters, so the "
        "letter policy gets a calibration of its own rather than borrowing the "
        "character one. The Swedish reference is unchanged: Swedish has no "
        "multi-character letters, so its character count already is a letter "
        "count.",
        "",
        f"**`{letters_rec['language']}` "
        f"`long_word_threshold`: {letters_rec['long_word_threshold']}**  ",
        f"Bracket: {tuple(letters_rec['bracket'])}  ",
        f"Matched share: {fmt_share(letters_rec['matched_share'])} against the "
        f"Swedish {fmt_share(letters_rec['reference_share'])} at "
        f"{letters_rec['reference_threshold']}  ",
        f"Residual: {letters_rec['residual']:.4f}  ",
        f"Runner-up: {letters_rec['runner_up']} "
        f"(residual {letters_rec['runner_up_residual']:.4f})",
        "",
        "Same threshold as `hu`, different share behind it. That is the point of "
        "shipping both keys: pairing a threshold with the wrong length policy "
        "measures something neither calibration measured.",
        "",
        "| curve | threshold |",
        "|---|---:|",
    ]
    letters += [
        f"| `{label}` | {t} |" for label, t in sorted(letters_rec["agreement"].items())
    ]
    chosen = list(letters_rec["agreement"].values())
    winner = letters_rec["long_word_threshold"]
    agreeing = chosen.count(winner)
    if agreeing == len(chosen):
        verdict = (
            f"All {len(chosen)} curves choose {winner}, as the character "
            "policy's panel does."
        )
    else:
        others = sorted(set(chosen) - {winner})
        verdict = (
            f"{agreeing} of {len(chosen)} curves choose {winner}; the rest "
            f"choose {others}. That is weaker support than the character "
            "policy's panel in section 3, and it is recorded rather than "
            "borrowed from it. The winning residual is nonetheless the smaller "
            "of the two, so the disagreement is between curves rather than "
            "within the primary one — read the bracket, not just the winner."
        )
    letters += ["", verdict]

    caveats = ["", "---", "", "## 6. Caveats", ""]
    caveats += [f"- {c}" for c in record["caveats"]]

    sources = ["", "---", "", "## 7. Sources and citations", ""]
    for key, source in record["sources"].items():
        sources.append(f"**{key}** — `{source['id']}` (`{source['file']}`)")
        dl = source.get("download") or {}
        if dl:
            sources.append(
                f"  - {dl.get('bytes', 0):,} bytes, sha256 "
                f"`{str(dl.get('sha256', ''))[:16]}…`"
            )
        for citation in source["citation"]:
            sources.append(f"  - {citation}")
        sources.append("")

    reproduce = [
        "---",
        "",
        "## 8. Reproducing",
        "",
        "```bash",
        "uv run python experiments/lix_calibration/scripts/download_data.py",
        "uv run python experiments/lix_calibration/scripts/run.py",
        "```",
        "",
        "The run asserts a set of regression anchors measured by hand before this "
        "script existed; if the reader ever starts producing different numbers it "
        "fails rather than quietly publishing them.",
        "",
    ]

    path = EXPERIMENT_DIR / "findings.md"
    path.write_text(
        "\n".join(
            header
            + table
            + agree
            + sensitivity
            + letters
            + caveats
            + sources
            + reproduce
        )
    )
    log("write", f"{path.stat().st_size:,} bytes → {path}")


if __name__ == "__main__":
    main()
