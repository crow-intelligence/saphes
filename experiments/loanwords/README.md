# Loan-word lexicon study

**Status: a measurement, not a lexicon.** This study asks how much usable material each
candidate source holds, and stops before deciding what to ship. Two decisions block that,
and both belong to a human — they are at the bottom of this page.

## Why measure first

The specification for this work named two sources and called them public domain. Neither
claim survived contact:

| specified | reality (verified 2026-09-08) |
|---|---|
| `Category:Hungarian_loanwords` on en.wiktionary | **empty**; the real tree is `Category:Hungarian terms borrowed from <language>`, one category per donor |
| `Kategória:Magyar nyelvű idegen szavak` on hu.wiktionary | **does not exist**; hu.wiktionary has no etymology categories at all, only bilingual dictionaries (`magyar-X szótár`) |
| "public domain sources" | en and hu Wiktionary are **CC BY-SA 4.0**, which is share-alike. Only Wikidata is CC0 |

So the licence choice was posed as free when it is not, and the sources were named as
existing when they do not. Measuring came first for that reason.

## What to run

```bash
uv run python experiments/loanwords/scripts/download_data.py   # ~2 minutes, polite rate
uv run python experiments/loanwords/scripts/coverage.py
```

`download_data.py` caches into `data/` (gitignored — the material is CC BY-SA and
re-fetchable, so it does not belong in an MIT repository). `coverage.py` writes
`results/coverage.json` and `results/findings.md`, both committed.

## Scripts

- `wiktionary.py` — a minimal MediaWiki category reader. Stdlib only, one request at a
  time, 0.2 s apart, with a descriptive User-Agent, per Wikimedia API etiquette.
- `download_data.py` — step 1, fetches and caches. Decides nothing.
- `coverage.py` — step 2, counts and reports. Also decides nothing.
- `utils.py` — paths and logging, mirroring `lix_calibration/scripts/utils.py`.

## The three things that decide whether this study is right

**1. Normalisation drops more than it looks.** `normalise()` rejects multiword entries,
anything with a digit or punctuation, and reconstructions. Wiktionary category members
include phrases and affixes, and counting those as lemmas would inflate every figure. The
counts in `findings.md` are post-filter.

**2. "Borrowed" and "derived" are different claims.** Wiktionary's *borrowed from* means a
conscious borrowing; *derived from* includes inherited vocabulary and indirect descent, and
is roughly four times larger. Using the wider set would sweep in words that are not
borrowings at all.

**3. The donor-era split is a proxy.** `ANCIENT_DONORS` and `MODERN_DONORS` in
`coverage.py` are lists, not rules, and they only approximate the thing that matters.
`iskola` is Latin and completely assimilated; a recent English borrowing may be entrenched
enough that no speaker flags it. The split is reported so a human can look at it, not so a
threshold can be applied to it.

## Decisions that are not mine to make

### A. Which vocabulary counts as *idegen szó*

Hungarian distinguishes **jövevényszó** — a borrowing so assimilated that no speaker hears
it as foreign — from **idegen szó**, a word still felt as foreign. *Ablak*, *király*,
*pénz* and *asztal* are all Slavic borrowings and all firmly in the first category.

A lexicon built from etymology fields contains both, and a ratio computed against it
measures **etymological origin**, not *idegenszó-arány*. Both are publishable numbers; they
are not the same number.

Nothing in the data distinguishes them. This wants a Hungarian speaker deciding, with the
donor split in `findings.md` as the starting point and an audit trail like
`hungarian_boundaries/results/decisions.tsv` as the output.

### B. Whether a CC BY-SA asset belongs in an MIT repository

The numbers make this concrete rather than theoretical: the CC0 option yields **20**
entries. Any usable lexicon is CC BY-SA 4.0. The options are

- ship the derived lexicon with an attribution block and a stated licence for that file,
  accepting a non-MIT asset in the tree;
- keep the lexicon out of the repository and have users run these scripts, as the corpora
  in `lix_calibration/` are handled;
- ship nothing and leave `loanword_ratio` lexicon-agnostic, which is what it does today.

The third is the current state and costs nothing to keep.

## What this study does not do

It does not build a lexicon, publish a threshold, or ship anything into `src/`. There is no
generated literal, because there is nothing to generate until A and B are answered.
