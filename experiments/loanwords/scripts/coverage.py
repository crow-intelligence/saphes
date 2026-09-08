"""Step 2 — measure what each source yields, and write the findings.

This study answers one question and refuses to answer a second.

**Answered:** how many usable Hungarian loan-word lemmas each candidate source
supplies, and therefore whether the CC0 option is viable at all. That is a
counting problem, and counting is what a script can do.

**Not answered:** which of those entries are *idegen szavak* — words still felt
as foreign — as opposed to *jövevényszavak*, assimilated borrowings like `ablak`
or `király` that no speaker hears as foreign. This script reports the donor-
language split, because donor language is the best available proxy, and stops
there. Turning the proxy into a shipped lexicon is a linguistic judgement, and
`../README.md` says so rather than hiding it behind a threshold.

Usage:
    uv run python experiments/loanwords/scripts/download_data.py
    uv run python experiments/loanwords/scripts/coverage.py
"""

import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_DIR, RESULTS_DIR, log, require_file  # noqa: E402

SOURCES = ("borrowed", "derived", "learned", "orthographic", "semantic")

# Donor languages whose borrowings are old enough to be thoroughly assimilated.
# Every one of these contributed before or around the Conquest era, and their
# vocabulary is what a Hungarian speaker would call jövevényszó rather than
# idegen szó: `ablak`, `király`, `pénz` are all Slavic. Listed rather than
# ruled, because there is no rule.
ANCIENT_DONORS = frozenset(
    {
        "Alanic",
        "Avar",
        "Byzantine Greek",
        "Bulgarian",
        "Danube Bulgar",
        "East Slavic languages",
        "Illyrian",
        "Iranian languages",
        "Kipchak",
        "Old Church Slavonic",
        "Old East Slavic",
        "Old Turkic",
        "Ossetian",
        "Pannonian Romance",
        "Proto-Slavic",
        "Serbo-Croatian",
        "Slavic languages",
        "Slovak",
        "Slovene",
        "South Slavic languages",
        "Turkic languages",
        "West Slavic languages",
    }
)

# The international stratum: conscious, mostly post-medieval borrowing, and the
# core of what `idegenszó-arány` is usually taken to mean.
MODERN_DONORS = frozenset(
    {
        "American English",
        "Arabic",
        "British English",
        "Dutch",
        "English",
        "French",
        "German",
        "Italian",
        "Japanese",
        "Late Latin",
        "Latin",
        "Medieval Latin",
        "New Latin",
        "Portuguese",
        "Russian",
        "Spanish",
        "Swedish",
    }
)


def classify(title: str) -> tuple[str | None, str]:
    """Return ``(lemma, verdict)`` for one Wiktionary category member.

    Wiktionary categories are not lists of lemmas. They hold proper nouns,
    affixes, multiword phrases and reconstructions alongside ordinary words, and
    counting those would inflate every figure in this study. Each rejection is
    named so ``findings.md`` can report what was dropped rather than only what
    survived.

    Contract:
        Guarantees:

        - A returned lemma is NFC, case-folded, alphabetic and non-empty.
        - ``verdict`` is ``"lemma"`` when a lemma is returned, and otherwise
          names the reason: ``"multiword"``, ``"affix"``, ``"proper-noun"``,
          ``"reconstruction"`` or ``"non-alphabetic"``.

        Silences:

        - **The proper-noun test is capitalisation**, which is a spelling rule
          rather than a linguistic one. Hungarian common nouns are lower case,
          so it is reliable here, but it also drops acronyms such as ``BMW``
          and ``AIDS`` — which are borrowings, just not ones a lemma lookup
          would ever match.
    """
    if " " in title or ":" in title:
        return None, "multiword"
    if "*" in title or title.startswith("Reconstruction"):
        return None, "reconstruction"
    if title.startswith("-") or title.endswith("-"):
        return None, "affix"
    if title[:1].isupper():
        return None, "proper-noun"
    lemma = unicodedata.normalize("NFC", title).casefold()
    if not lemma or not all(c.isalpha() or c == "-" for c in lemma):
        return None, "non-alphabetic"
    return lemma, "lemma"


def load(source: str) -> dict[str, list[str]]:
    """Read one cached source."""
    path = DATA_DIR / f"wiktionary-{source}.json"
    require_file(path, "download_data.py")
    return json.loads(path.read_text())


def lemmas_by_donor(
    record: dict[str, list[str]],
) -> tuple[dict[str, set[str]], Counter]:
    """Classify every entry, returning the lemmas and a tally of what was dropped."""
    out: dict[str, set[str]] = {}
    verdicts: Counter = Counter()
    for donor, titles in record.items():
        kept: set[str] = set()
        for title in titles:
            lemma, verdict = classify(title)
            verdicts[verdict] += 1
            if lemma:
                kept.add(lemma)
        if kept:
            out[donor] = kept
    return out, verdicts


def main() -> None:
    """Measure every source and write findings.md and coverage.json."""
    per_source: dict[str, dict[str, set[str]]] = {}
    verdicts: Counter = Counter()
    for source in SOURCES:
        per_source[source], source_verdicts = lemmas_by_donor(load(source))
        verdicts.update(source_verdicts)
        total = len({lemma for s in per_source[source].values() for lemma in s})
        log("load", f"{source}: {total} unique lemmas")
    log("filter", f"verdicts across all sources: {dict(verdicts.most_common())}")

    wikidata_path = DATA_DIR / "wikidata-lexemes.json"
    require_file(wikidata_path, "download_data.py")
    wikidata_rows = json.loads(wikidata_path.read_text())
    wikidata = {
        lemma
        for row in wikidata_rows
        if row.get("source") and (lemma := classify(row["lemma"])[0])
    }
    wikidata_all = {
        lemma for row in wikidata_rows if (lemma := classify(row["lemma"])[0])
    }
    log(
        "load",
        f"wikidata: {len(wikidata_all)} lexemes, {len(wikidata)} with etymology",
    )

    borrowed = per_source["borrowed"]
    borrowed_all = {lemma for s in borrowed.values() for lemma in s}
    derived_all = {lemma for s in per_source["derived"].values() for lemma in s}
    extras = {
        lemma
        for key in ("learned", "orthographic", "semantic")
        for s in per_source[key].values()
        for lemma in s
    }

    ancient = {
        lemma for donor, s in borrowed.items() if donor in ANCIENT_DONORS for lemma in s
    }
    modern = {
        lemma for donor, s in borrowed.items() if donor in MODERN_DONORS for lemma in s
    }
    unclassified = borrowed_all - ancient - modern
    donor_sizes = Counter({donor: len(s) for donor, s in borrowed.items()}).most_common(
        15
    )

    record = {
        "generated": __import__("datetime")
        .datetime.now(__import__("datetime").UTC)
        .isoformat(timespec="seconds"),
        "sources": {
            "wiktionary-borrowed": {
                "licence": "CC BY-SA 4.0",
                "categories": len(borrowed),
                "unique_lemmas": len(borrowed_all),
            },
            "wiktionary-derived": {
                "licence": "CC BY-SA 4.0",
                "categories": len(per_source["derived"]),
                "unique_lemmas": len(derived_all),
            },
            "wiktionary-other": {
                "licence": "CC BY-SA 4.0",
                "unique_lemmas": len(extras),
            },
            "wikidata": {
                "licence": "CC0",
                "lexemes": len(wikidata_all),
                "with_etymology": len(wikidata),
            },
        },
        "overlap": {
            "borrowed_in_derived": len(borrowed_all & derived_all),
            "borrowed_only": len(borrowed_all - derived_all),
            "wikidata_in_borrowed": len(wikidata & borrowed_all),
        },
        "strata": {
            "ancient_donors": len(ancient),
            "modern_donors": len(modern),
            "unclassified": len(unclassified),
        },
        "top_donors": donor_sizes,
        "filtered_out": dict(verdicts.most_common()),
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "coverage.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2)
    )
    _write_findings(record, ancient, modern)
    log("done", f"{RESULTS_DIR / 'coverage.json'}")


def _write_findings(record: dict, ancient: set[str], modern: set[str]) -> None:
    """Write the human-readable account of the numbers."""
    sources = record["sources"]
    lines = [
        "# Loan-word source coverage",
        "",
        f"GENERATED by `scripts/coverage.py` on {record['generated']}.",
        "",
        "## 1. What each source yields",
        "",
        "| source | licence | unique lemmas |",
        "|---|---|---:|",
        f"| en.wiktionary *terms borrowed from* | CC BY-SA 4.0 | "
        f"{sources['wiktionary-borrowed']['unique_lemmas']:,} |",
        f"| en.wiktionary *terms derived from* | CC BY-SA 4.0 | "
        f"{sources['wiktionary-derived']['unique_lemmas']:,} |",
        f"| en.wiktionary learned/orthographic/semantic | CC BY-SA 4.0 | "
        f"{sources['wiktionary-other']['unique_lemmas']:,} |",
        f"| **Wikidata lexemes with etymology** | **CC0** | "
        f"**{sources['wikidata']['with_etymology']:,}** |",
        "",
        "Wikidata holds "
        f"{sources['wikidata']['lexemes']:,} Hungarian lexemes in total.",
        "",
        "## 2. The licence question is settled by the numbers",
        "",
        "The only genuinely public-domain source yields "
        f"{sources['wikidata']['with_etymology']} entries. That is not a",
        "lexicon; it is a handful of examples. Any usable list is CC BY-SA 4.0,",
        "which is share-alike, and saphes is MIT — so a bundled lexicon means a",
        "non-MIT asset in the repository, with attribution, or no bundled lexicon",
        "at all.",
        "",
        "## 3. The two sources the specification named do not exist",
        "",
        "- `Category:Hungarian_loanwords` on en.wiktionary is **empty**. The real",
        "  structure is `Category:Hungarian terms borrowed from <language>`, one per",
        f"  donor, {sources['wiktionary-borrowed']['categories']} of them non-empty.",
        "- hu.wiktionary has **no etymology categories at all**. Its category tree is",
        "  bilingual dictionaries (`magyar-X szótár`).",
        "",
        "## 4. What was filtered out, and why",
        "",
        "Wiktionary categories are not lists of lemmas. Every figure above is",
        "post-filter; this is what the filter removed, across all sources:",
        "",
        "| verdict | entries |",
        "|---|---:|",
        *(
            f"| {verdict} | {count:,} |"
            for verdict, count in record["filtered_out"].items()
        ),
        "",
        "`proper-noun` is decided by capitalisation, which is reliable for Hungarian",
        "common nouns but also drops acronyms (`BMW`, `AIDS`). Without it the lexicon",
        "would contain `aachen`, `beethoven`, `arizona` and `buda`: the",
        "categories are full of place and person names.",
        "",
        "## 5. Donor languages, and the stratum problem",
        "",
        "| donor | lemmas |",
        "|---|---:|",
    ]
    for donor, size in record["top_donors"]:
        lines.append(f"| {donor} | {size:,} |")
    strata = record["strata"]
    lines += [
        "",
        "Splitting the *borrowed* set by donor era:",
        "",
        "| stratum | lemmas |",
        "|---|---:|",
        f"| ancient donors (Slavic, Turkic, Iranian…) | {strata['ancient_donors']:,} |",
        f"| modern donors (Latin, German, English, French…) | "
        f"{strata['modern_donors']:,} |",
        f"| unclassified | {strata['unclassified']:,} |",
        "",
        "**This split is a proxy, not an answer.** Donor era correlates with",
        "assimilation but does not determine it: `iskola` is Latin and utterly",
        "assimilated, while a recent English borrowing may be so entrenched that no",
        "speaker flags it. The ancient stratum is where the *jövevényszó* problem is",
        "concentrated — the `ablak`, `király`, `pénz` cases — but excluding it",
        "wholesale would be its own error.",
        "",
        "Examples from each stratum, for a human to judge:",
        "",
        f"- ancient: {', '.join(sorted(ancient)[:12])}",
        f"- modern: {', '.join(sorted(modern)[:12])}",
        "",
        "## 6. What decides it, and what is still open",
        "",
        "**The criterion is Bakos Ferenc, *Idegen szavak és kifejezések szótára***",
        "(Akadémiai Kiadó): a word is an idegen szó if Bakos lists it. The tables",
        "above are why that had to be a lexicographic judgement rather than a rule —",
        "the modern stratum holds every Latin month name alongside `internet`, and no",
        "property of the data separates them.",
        "",
        "Bakos is in copyright, so it is used as a **criterion, never as a source**.",
        "`candidates.tsv` is adjudicated against it by hand and `decisions.tsv` — the",
        "verdicts — is the work product, as in `../hungarian_boundaries/`.",
        "",
        "Still open: whether a lexicon derived from CC BY-SA material may be",
        "committed to an MIT repository at all. See `../README.md`.",
        "",
        "Nothing is shipped into `src/`, and no generated literal exists.",
    ]
    (RESULTS_DIR / "findings.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
