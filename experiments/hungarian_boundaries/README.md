# Hungarian morpheme boundaries

Nine Hungarian letters are written with more than one character. A compound seam
can put those characters side by side without them being that letter: `község` is
`köz` + `ség`, so its `zs` is two letters and not the `zs` digraph. Nothing in the
string says so, and nothing raises — the letter count just comes out one too low.

This experiment proposes candidate boundaries from the corpus. It does not decide
them. The decisions are committed separately, by hand.

## How to run

From the repo root. The corpus is the one the LIX calibration already downloads;
nothing new is fetched.

```bash
uv run python experiments/hungarian_boundaries/scripts/mine.py --smoke-test  # top-100k, seconds
uv run python experiments/hungarian_boundaries/scripts/mine.py               # full list, ~90s
```

## Outputs

| file | status |
|---|---|
| `results/candidates.tsv` | **generated** by `mine.py`; `decision` column deliberately blank |
| `results/decisions.tsv` | **hand-curated**; the verdict on each candidate and the seam that shipped |
| `src/saphes/hungarian.py` | `MORPHEME_BOUNDARIES` and `BOUNDARY_EXCEPTIONS`, transcribed from the decisions |

## What the corpus can and cannot establish

**It can** attest that a string occurs, at what token frequency, and that both
halves of a proposed split occur as free-standing words. That is real evidence,
and the ranking is built on it.

**It cannot** establish that a boundary is there. `kincsásó` (`kincs` + `ásó`, a
real `cs`) and `gerincsérv` (`gerinc` + `sérv`, a false one) are structurally
identical strings. Only a morphological analyser separates them, and taking that
dependency is the thing saphes declines to do. Nor can it distinguish a live
derivation from a frozen lexicalised noun.

**The lemma annotations do not help, and it is worth recording why.** The Webcorpus
crawl part carries `<lemma>` inside `<ana>` blocks, which looks like exactly the
evidence wanted — `form == lemma + "ság"` with a lemma ending in `z` would be
proof of a seam. It is not usable: coverage is well under 1% of tokens, and it is
not a random sample. The analyser emits an analysis mostly where it *failed* —
hyphen-final compound fragments, list markers, numerals, URLs. Searching for the
`-ság`/`-ség` pattern in it returns nothing at all. Attested hyphenated spellings
(`gáz-számla` attesting the seam in `gázszámla`) are likewise empty: the
hyphenated types in the frequency list are acronyms and foreign names.

So the evidence is co-occurrence plus frequency, and the last step is a person.

## The two detectors

**Compound seams.** For each type above 50 tokens, enumerate splits into two
halves of at least three characters that are themselves free-standing types at
100 tokens or more, and keep the split only if reading the seam as a boundary
*changes the letter count*. Rank by the rarer half's frequency.

One filter does most of the work: **a compound is rarer than either of its
parts.** Without it the queue fills with monomorphemic words carrying a real
digraph — `hiszen` outranks `his` two thousand to one and is plainly not `his` +
`zen`. It took the smoke run from 20 candidates to 5, of which 4 were right.

The filter is not free, and the cost is stated rather than tuned away: it drops
true positives where the compound is about as frequent as its rarer half.
`fúvószenekar` (734) loses to `fúvós` (661) and only reaches the queue through
its inflected forms.

**Suffix-rule false positives.** `saphes.hungarian` handles the productive
`-ság`/`-ség` suffix by rule rather than by list, because a list would be endless
— the corpus has `egyezség`, `hitközség`, `nagyközség`, `ínyencség` and
`féligazság` alongside the obvious `igazság`. The `c` half of that rule cannot see
that `kavicságy` is `kavics` + `ágy`. The detector: the prefix ending in the
*digraph* is an attested word while the prefix ending one character earlier is
not, and the remainder is a word too.

The full corpus yields exactly one such word above the frequency floor:
`kavicságy`, 55 tokens.

## What was decided

121 candidates, 72 accepted, 49 rejected, covered by 38 shipped seams — one seam
covers a whole paradigm, since matching is by substring, so `alvás-zavar` also
fixes `alvászavarok`, `alvászavarnak` and `alvászavarral`.

**A seam only covers what extends it rightward, so it must stop before anything
that can alternate.** Hungarian lengthens a stem-final low vowel under
suffixation — `zene` becomes `zené`, `zóna` becomes `zóná` — and that happens
*inside* the key, where substring matching cannot follow. A seam spelled
`fúvós-zene` misses `fúvószenét` entirely and counts it one letter short, in
silence. Two candidates were rejected on that basis before it was understood
(`fúvószenét`, 53; `zöldzónában`, 71), both from families whose every other
member was accepted. The seams are now truncated to the shortest span that still
covers the junction: `fúvós-zen`, `vonós-zen`, `zöld-zón`, and `víz-sug` from
the start. When adding an entry, check it against an inflected form of the
*second* element, not only against a longer compound.

Precision is low by construction, which is the reason for the review step. The
rejected classes, all of which are real digraphs the detector could not see:

- inflected forms read as compounds — `rácsokat` is `rács` + `okat`, not `rác` +
  `sokat`; `estélyen` is `estély` + `en`; `versenyes` is `verseny` + `es`
- monomorphemic words — `mozsár`, `bizsereg`, `macsó`, `lucsok`
- `-szám` compounds, where the `sz` is real — `motorszám`, `kilószám`,
  `fordulószám`, `milliószám`
- corpus typos — `roszak`, `eroszak`, `rosszab`, `magyaroszágon`
- foreign words and names — `milosevicset`, `gázsik`, `zenészeit`

## What this does not fix

A compound outside the table is still counted one letter short, silently. The
table bounds the failure; it does not remove it. What can be said for it is that
the size of the residue is now measured rather than guessed: across the full
560-million-token 4% stratum the boundary handling moves the corpus-level
long-word share by 0.01 percentage points, and it does not move the calibrated
LIX threshold.

## Data source

Hungarian Webcorpus (MOKK/BME) — <http://mokk.bme.hu/resources/webcorpus/>.
Permissive Open Content, but **citation is required**: Halácsy et al. (LREC 2004)
and Kornai et al. (Web as Corpus, ACL 2006). The download and the reader belong to
`experiments/lix_calibration/`; this experiment reuses both.
