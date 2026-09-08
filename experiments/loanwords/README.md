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

## Frequency is form-based, and inflates homographs

`candidates.tsv` carries MOKK Webcorpus frequencies so the list can be worked in the order
that matters. **The frequency is for the word *form*, across every sense and every
etymology**, because the MOKK list is a frequency list and not a lemmatised corpus. Where a
borrowing is a homograph of a common native word, the number is wrong by orders of
magnitude:

| lemma | listed freq | what the frequency is actually counting |
|---|---:|---|
| `lett` | 664,066 | the past tense of *lesz*, not the German-derived "Latvian" |
| `von` | 213,369 | Hungarian *von* "to pull", not the Korean won |
| `tag` | 105,537 | Hungarian *tag* "member", not the English *tag* |

Use the ordering to decide **what to review first**, never to weight a published ratio.

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

### A. Which vocabulary counts as *idegen szó* — **decided**

The authority is **Bakos Ferenc, *Idegen szavak és kifejezések szótára*** (Akadémiai
Kiadó). A word is an *idegen szó* for this study if Bakos lists it. That settles the
question no amount of data could: Hungarian distinguishes **jövevényszó** — a borrowing so
assimilated that no speaker hears it as foreign — from **idegen szó**, a word still felt as
foreign, and only a lexicographer draws that line.

**Bakos is in copyright**, and in the EU its headword *selection* carries database right on
top of that. Nothing from it enters this repository: the scan and the pipeline that reads it
live in `data/` and `data_collection_and_verification/`, both gitignored.

Bakos has now been read end to end rather than consulted entry by entry. It is a 745-page
scan with no text layer, so the pipeline OCRs it (tesseract 5.3.4, Hungarian model, 300 dpi)
and recovers entries from the **hanging indent** that separates a headword from its
continuation lines. That yields **22,882 single-word headwords** and 8,387 multiword
phrases, with Webcorpus frequencies attached and 0 where a headword does not occur.

That changes what `candidates.tsv` is for. Bakos answers the *idegen szó* question directly,
so hand-adjudicating a Wiktionary candidate list is no longer the route to the answer — it is
now the route to a **redistributable** one, which is a different problem. See B.

Two findings from the data make the case that this had to be a lexicographic judgement
rather than a rule:

**The donor-era proxy fails on the modern side.** Ranked by corpus frequency, the "modern
donor" stratum opens with `október`, `szeptember`, `november`, `május`, `december`,
`január`, `március`, `augusztus`, `június`, `július`, `február` — every Latin month name —
alongside `iskola`, `autó`, `pont` and `friss`. None is an *idegen szó*. They sit in the
same stratum as `internet`, `absztrakt` and `regisztráció`, and no property of the data
separates them.

**The ancient filter, by contrast, holds.** Its top entries are `egész`, `világ`, `idő`,
`dolog`, `szabad`, `úr`, `törvény`, `szent`, `kormány`, `munka`, `pénz`, `király`, `betű` —
core vocabulary throughout, and correctly excluded.

## The shipped list

`results/idegenszavak.txt` — **15,203 Hungarian lemmas**, with `results/idegenszavak.json`
recording how they were chosen.

**This is not Bakos, and the difference is the selection principle.** Bakos selects for
lexicographic completeness: 22,882 single-word headwords, most of them technical vocabulary
a reader never meets. This list selects by **frequency rank in the MOKK Hungarian
Webcorpus**, and uses Bakos only to *verify* that a candidate is a foreign word at all. The
corpus chooses; the dictionary checks.

Two cuts, both with a linguistic reason:

- **Hapaxes and absent words go.** A word occurring once in 1.8 billion tokens says nothing
  about running Hungarian. That removes 4,471 candidates.
- **The Zipfian head goes**, on the reading that a word the corpus uses that heavily is
  ordinary vocabulary, not an *idegen szó*. `internet` (172 per million), `program` (278)
  and `koncepció` (14) are all in Bakos and none is felt as foreign today. Bakos cannot make
  this call — a dictionary of foreign words keeps a word once it is in. The corpus can.

Before either cut, five structural filters remove things that are not words of running
Hungarian: `röv` entries (abbreviations and chemical symbols — Bakos's `k` for *kilo-*
inherits 150 million hits from the Hungarian letter), affixes, headwords under four
characters, capitalised proper nouns, and continuation lines misread as headwords.

### Why the head fraction is 2%, not Pareto's 20%

Pareto describes a whole vocabulary. This ranking is not one — it is already filtered to
Bakos's foreign words, so its distribution is shifted far down before any cut. Taking 20% of
*it* removes `konszenzus`, `prioritás` and `implementáció`, and scores a sentence full of
them at **zero**. At 2% the cut falls where it was meant to.

| head dropped | lemmas | keeps |
|---:|---:|---|
| 2% | 15,203 | konszenzus, prioritás, implementáció, alkohol |
| 5% | 14,738 | prioritás, implementáció |
| 10% | 13,962 | implementáció |
| 20% | 12,411 | none of them |

### Two known limits

- **The boundary is arbitrary**, because frequencies tie. `historizmus` and `konszenzus`
  both occur 711 times; only one can fall above the line.
- **The corpus is web text containing English.** `guide`, `speed`, `museum`, `offer` and
  `band` are all genuine Bakos headwords, but their counts are earned by English prose
  rather than Hungarian usage.

### Attribution

Verified against **Bakos Ferenc, *Idegen szavak és kifejezések szótára*** (Akadémiai Kiadó).
Bakos is copyrighted and is **not** redistributed here, in whole or in part: it is consulted
as the criterion for what counts as a foreign word. Frequencies are from the **MOKK Hungarian
Webcorpus 2.2** (BME MOKK), 1,782,720,285 tokens.

The pipeline that reads the dictionary lives in `data_collection_and_verification/` and is
gitignored, as is the scan in `data/`.

---

### B. What may actually be shipped — sharper now, not easier

Three sources, three licences, and they trade quality against redistributability:

| source | entries | licence | shippable? |
|---|---:|---|---|
| Wikidata lexemes | 17 | CC0 | yes, and useless |
| en.wiktionary *borrowed* | 2,492 | CC BY-SA 4.0 | yes, with attribution; non-MIT asset |
| **Bakos** | **22,882** | **© Akadémiai Kiadó** | **no** |

Bakos is nine times the size of the Wiktionary list and is the actual authority — and it is
the one thing that cannot be redistributed at all. So the best list and the shippable list
are not the same list.

What Bakos *can* do without being copied is **adjudicate**. Measured against it, the
Wiktionary borrowed set splits sharply:

| stratum | confirmed by Bakos |
|---|---:|
| ancient donors (Slavic, Turkic, Iranian…) | **2.9%** (13/444) |
| modern donors (Latin, German, English…) | 60.8% (1,082/1,779) |
| unclassified | 34.2% |

The ancient figure is the striking one: Bakos independently rejects 97% of exactly the
stratum the donor-era proxy predicted it would, which is about as good a cross-validation as
this study can get. And it rejects `iskola`, `október` and `autó` while accepting `internet`
and `abbé` — the cases no rule could separate.

So a fourth option exists, and it is the one worth a decision:

- ship the **Wiktionary-derived subset that Bakos confirms** — CC BY-SA material, with the
  *selection* informed by Bakos. Roughly 1,100 lemmas of the modern stratum. Better than
  Wiktionary alone; a fraction of Bakos; and legally grey, because a selection made by
  applying a copyrighted work's selection is not obviously a new one. **That greyness is
  the decision, and it is not mine to make.**

The other options remain: ship the CC BY-SA list unfiltered with attribution; keep any list
out of the repository and have users build it, as `lix_calibration/` handles its corpora; or
ship nothing and leave `loanword_ratio` lexicon-agnostic. **The last is the current state and
costs nothing to keep.**

## What this study does not do

It does not build a lexicon, publish a threshold, or ship anything into `src/`. There is no
generated literal, because there is nothing to generate until A and B are answered.
