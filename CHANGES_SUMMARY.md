# Changes summary

Branch `hungarian-graphemes-and-stemming`, off `main`. Pushed as a **draft PR**; not
merged, and `main` is untouched.

Six commits, each verified green on its own before it was made:

1. Count Hungarian letters, not characters
2. Add optional Snowball stemming as a third token unit
3. Calibrate the letter policy separately, with its own panel
4. Measure real LIX on running text, across registers
5. Map the LIX interpretation bands to Hungarian
6. Document the Hungarian pipeline end to end

`make ci` green (342 tests including doctests), `mkdocs build --strict` clean, the calibration
notebook executes, both `examples/` scripts run.

Two rounds of work. The first added Hungarian letter counting, optional Snowball stemming and
a second calibration key. The second — this one — made all of it discoverable, and answered
the question the study had left open since it started: **what a Hungarian LIX score actually
means.**

---

## 1. Documentation

Three capabilities had shipped with one inbound link each. Closed:

- **New `how-to/measure-hungarian-text.md`** — threshold, letter count and stemmer in one
  recipe. That combination appeared on no page.
- **New `explanation/what-a-hungarian-lix-score-means.md`** — the argument behind the bands.
- `install.md` documented one of two extras. `index.md`'s token-stream table, the glossary's
  `Unit` entry and the package docstring `reference/index.md` renders were all still
  two-valued after `"stem"` shipped. `reference/index.md` indexed nothing.
- Two cross-references promised coverage their targets did not contain — the letter-policy
  calibration, and calibrating on letters. Both targets now cover it.
- `two-token-streams.md` asserted a theorem that is **false for stems**: a stemmer can give
  one lemma two stems, so nothing follows about stem-TTR against lemma-TTR.
- `why-implementations-disagree.md` claimed every divergence is the sentence count. True for
  English; *C* is a second axis wherever a letter is not a character.
- README, tutorial, `diagnose-a-surprising-result.md`, glossary (*Digraph*, *Geminate*,
  *Morpheme boundary*), `reproduce-the-calibration.md`.

## 2. A published claim was wrong, and is now corrected

`CALIBRATIONS["hu-letters"]` reused the **character-policy** agreement panel, so it asserted
seven concurring curves when one had been measured under the letter policy.

Recomputing the panel under its own policy — the strata, the asterisk-dropped variant and
`leipzig-hun`, all recounted in letters — gives the honest answer, which is weaker:

**Three of five curves choose 8; two choose 7.** The residual on the primary curve is
nonetheless the *better* of the two (0.0124 against 0.0168). `findings.md` now reads the split
rather than only tabling it, and the two records no longer carry byte-identical caveats.

Also fixed: the notebook crashed on the regenerated record (`record["recommendation"]` became
a list); `findings.md` documented only the first of two recommendations, which falsified
`recommended_threshold`'s own claim that `findings.md` cross-checks the shipped literal; the
provenance record stamped one global `length_policy` over three; `validate_b.py`'s transfer
gate was **ten percentage points**, which almost no corpus could fail, and it tracked a
`skipped_no_sentence` bucket it never published.

## 3. Making the number mean something

`LixResult.band` returned `None` at the calibrated threshold, so the headline result had no
interpretation at all.

**No new corpus was needed.** The Leipzig archives already on disk carry a `-sentences.txt`
beside the `-words.txt` the study had always read — a million sentences each. That gives real
*A*, *B* and *C* for **both** languages; until now the Swedish side was only a word-length
curve, so there was nothing to map from.

`recommended_threshold("hu-letters").interpret(42.11)` → `'standard'`.

### Why a retuned threshold was never going to be enough

LIX is `A/B + 100·C/A`. The threshold calibration acts on the second term only — and the first
differs between the languages on its own account. Hungarian news writes sentences three words
longer (18.30 against 15.37), which a frequency list cannot see because it has no sentences in
it. The bands are what absorb that.

### What shipped, and what was withheld

| Swedish boundary | `hu` (chars) | `hu-letters` | supporting windows |
|---:|---:|---:|---:|
| 30 | 35.45 | 32.63 | 402 |
| 40 | 42.95 | 40.18 | 4,063 |
| 50 | 51.16 | 48.19 | 1,300 |
| 60 | *not placed* | *not placed* | **5** |

The published boundaries move by under a point across a tenfold change in window length. The
top one is withheld because **Swedish news puts about 0.04% of its text above LIX 60**, so it
rests on five windows out of twelve thousand. That is a property of the reference corpus, not
of Hungarian: a corpus of harder writing would place it. Above the `standard` band `interpret`
returns `None`.

The publication rule is support, not drift — a quantile needs text on both sides of it. Drift
is reported alongside as the symptom, and the boundary short of support is exactly the one
whose drift is large.

## 4. The register panel

Every caveat saphes ships tells users to recompute on their own register. The study had never
done it: every corpus in it was web or news.

| register | tier | *B* from | A/B | LIX @8 letters | band |
|---|---|---|---:|---:|---|
| song lyrics | author-local | segmented | 17.56 | 23.56 | `very easy` |
| parliamentary speech | author-local | corpus | 18.21 | 41.09 | `standard` |
| news | public | corpus | 18.30 | 42.11 | `standard` |
| investigative journalism | author-local | segmented | 22.63 | 46.71 | `standard` |

**LIX separates prose from non-prose, not prose from prose.** The three prose registers sit
within six points and all land in the same band, though one is spoken oratory and another is
dense writing about public procurement. Worth knowing before reading anything into a few
points between two Hungarian corpora.

## Decisions that change the numbers

| decision | default | effect |
|---|---|---|
| `MIN_SUPPORT` for publishing a boundary | 200 reference windows | The inner boundaries clear it by 2× or more; the outermost misses by two orders of magnitude, so the value is not load-bearing |
| band-mapping window | 25 sentences | Changes the spread; the ladder 10/25/50/100 is published |
| `TRANSFER_TOLERANCE` in `validate_b.py` | 0.05 | Was 0.10, which asserted nothing against an observed gap of 0.016 |
| `corpus_lix(keep_spans=)` | `False` | Retaining a span per sentence for every panel row exhausted memory on the first full run |
| register panel `--limit` | 300,000 | Below roughly 100k the tail quantiles stop being estimable |

## Needs a human call

**1. Does the band mapping claim enough to be worth shipping?** It preserves how much text
falls in each band. It says nothing about whether Hungarian readers find those texts
correspondingly hard, and nothing here could. If you would rather that claim not ship at all,
`interpret` and `_lix_bands.py` are self-contained and removable.

**2. Tier-2 registers are not externally reproducible.** They read sibling repos on this
machine. Marked in every row, in the experiment README and in the findings, but it does mean
`experiments/lix_registers/results/` cannot be regenerated from a clean checkout. The
`--tier1-only` path can, and is verified.

**3. `hu-letters` has a split panel.** Three of five curves at 8, two at 7, bracket `(7, 8)`.
The primary residual is the better of the two calibrations, so I left the winner at 8 — but
someone reading `.agreement` should see the split, and now does.

**4. The boundary table from the previous round** still wants your eyes; unchanged since,
audit trail in `experiments/hungarian_boundaries/results/decisions.tsv`.

## Deliberately left alone

- **`LixResult.band` still returns `None`** away from threshold 6, and `lix` still takes no
  `language=`. The mapped labels live on the recommendation object, which knows the length
  policy too. Adding language dispatch to `lix` would undo a deliberate design.
- **`collapse_digraphs` keeps its cascade**, documented, as the naive primitive.
- **The `kmdb` register is read from SQLite, not its token Parquet**, so its *B* is segmented
  rather than corpus-supplied. Reading the Parquet would need pyarrow — a large dependency for
  one row of a panel. Stated in the table rather than hidden.
- Two pre-existing lint errors in `download_data.py` and `leipzig.py`, untouched by this work.
- **Ancient Greek**, still the next study. The `running_text.py` reader and the band machinery
  transfer unchanged; only the corpus differs.
