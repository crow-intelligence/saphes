# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Documentation

- The front-facing material was left describing a two-metric package while 0.2.0 shipped
  five. Corrected: the `pyproject` description and keywords (which are what PyPI shows),
  both the README and `docs/index.md` intros, and the data-contract table, which now lists
  all four input contracts rather than the original opposed pair.
- **New tutorial**, `tutorial/measure-syntactic-complexity.md` — builds a parse by hand so
  the counts are visible before the average, reproduces Jing & Liu's 1.17 and 2, then hands
  the job to a real parser. Promised in the plan for 0.2.0 and missed.
- **Glossary** gained the vocabulary the release introduced and had none of: dependency
  distance, head, hierarchical distance, MDD, MHD, macro/micro aggregation, parse,
  punctuation policy, and *idegen szó* against *jövevényszó*.
- `CLAUDE.md` module layout now lists `syntax.py`, `adapters.py` and `loanwords.py`, and
  records the invariants they carry.

### Planned

- The same calibration study for Ancient Greek, for the Homer project. The method transfers
  unchanged; only the corpus differs.
- Dependency motifs (Jing & Liu 2017), extending the MDD/MHD pair. Deferred rather than
  rushed: it produces a distribution of chunk types rather than a score, so it needs a
  corpus study to say anything.

## [0.2.0] - 2026-09-08

The Hungarian iteration and the syntactic-complexity expansion, together.

saphes grows from two metric families to five. **Readability** (LIX/RIX) and **lexical
diversity** (TTR/MATTR) are joined by **dependency distance**, **hierarchical distance** and
the **loan-word ratio**, with zero-dependency adapters for HuSpaCy and CoNLL-U/emtsv. The
core still declares `dependencies = []`, and a fresh interpreter still imports nothing
heavier than the standard library.

Every formula is taken from the paper that defines it and pinned to that paper's own worked
example: LIX = 45.0 from Björnsson's counts, MDD = 1.17 and MHD = 2 from Jing & Liu (2015:
164), MDD = 2.125 from Zhang & Zhou (2023). Neither dependency paper prints the tree behind
its number; both were reconstructed by hand and both close.

This is a 0.x release and the API is not frozen. `length_policy="graphemes"` may still be
renamed, and `parser`, `LoanwordResult` and the adapters have not yet been exercised by
homer, music_networks or kmdb_dashboard.

### Added — the loan-word ratio

- `saphes.loanwords` — `loanword_ratio`, `loan_ratio_from_counts`, `LoanwordResult` and
  `FOREIGN_PATTERNS`. Measures *idegenszó-arány*, the share of a text's lemmas that are
  foreign.

- **saphes ships no lexicon, and the function refuses to run without one.** Supply a set,
  enable the spelling heuristic, or both; asking for neither raises rather than reporting
  that every word is native. What counts as a loan word is a judgement about a particular
  vocabulary, and the package has no business making it silently.

- `LoanwordResult` returns the ratio together with `matches` (the lemmas themselves),
  `matched_by_lexicon` and `matched_by_heuristic` **kept separate**, `pattern_counts`
  naming which spelling rules fired, `lexicon_id`, `lexicon_size` and `excluded`. Dictionary
  evidence and a guess from spelling are different things and are not summed into one
  unaccountable number.

### Removed — the spelling heuristic

- **`FOREIGN_PATTERNS`, `HEURISTIC_EXCEPTIONS`, and the `heuristic` / `patterns` /
  `exceptions` parameters are gone**, together with `matched_by_heuristic`,
  `pattern_counts` and `exceptions_applied` on the result. `lexicon` is now a **required**
  argument: there is no fallback, and omitting it is a `TypeError` rather than a number
  computed against no evidence.

  Three measurements, taken against the shipped 15,203-lemma lexicon and the MOKK
  Webcorpus, decided this:

  - **It covered 8.4% of the lexicon.** The words that carry an idegenszó-arány in
    Hungarian prose — *prioritás*, *konszenzus*, *implementáció* — look nothing like
    foreign words. A spelling rule was never a substitute for a list.
  - **Hungarian manufactures the same spellings.** The suffixes `-hat`/`-het` and
    `-hoz`/`-hez`/`-höz` put an `h` after a stem, so any stem ending in `t`, `p` or `c`
    produces the digraph at the seam: *látható*, *kapható*, *állathoz*, *táncház* — 1,187
    word forms and 2.5 million tokens, and productive, so unreachable by any list. Add the
    surnames, where `th` spells a plain `t`: *Tóth*, *Horváth*, *Németh*, *Kossuth*.
  - **It contradicted the lexicon.** The genuinely foreign words it added were
    *technológia*, *abszolút* and *szexuális* — precisely the assimilated internationalisms
    a frequency-selected lexicon excludes on purpose. Enabling it silently reversed the
    caller's own decision.

  A brief intermediate version added a morpheme-seam lookahead and a 39-entry exception
  list of surnames and compounds. Both are removed with the heuristic they existed to
  repair.

### Changed — `parse_source` is now `parser`

- **`parse_source` recorded the file *format*; `parser` records what produced the trees**,
  which is the thing that moves the number. A parser carries the annotation convention of
  the treebank it was trained on, and that convention decides which word is the head — the
  entire input to a distance measure.

  On one sentence of the fixture corpus, HuSpaCy and emtsv agree about every word except
  three: `és` and `kötelezi` swap places in the coordination, and the full stop attaches to
  the verb or to ROOT. MDD 1.600 against 1.500 — 6.7% apart, same words, same formula.
  Across the corpus it is 1.6845 against 1.5328, and the two engines invert on MHD.

  `parser` is free text (`"huspacy hu_core_news_md 3.8.0"`, `"emtsv tok-dep-conll"`) and
  defaults to `None`, so an unlabelled result is visibly unlabelled. The old
  `ParseSource` literal is removed: `"conllu"` was true of emtsv, the Szeged treebank and
  UD Hungarian alike, which do not agree with each other.

  Guidance, now in the module docstring and the how-to: where you have a choice, use the
  spaCy model for the language — HuSpaCy for Hungarian. Choosing emtsv means choosing
  Prague-style coordination and numbers that will not line up with anyone else's.

### Notes on the loan-word ratio

- **The metric needs lemmas, and a surface stream fails silently.** `komputerekkel` misses a
  lexicon containing `komputer`, so the wrong stream produces no error and a plausible
  *lower* ratio. `LoanwordResult.unit` is the literal `"lemma"` rather than `TokenUnit`, the
  same device `LixResult.unit` uses in the opposite direction, and
  `TestLoanwordsNeedLemmas` in `tests/test_contracts.py` pins the asymmetry as a floor.
- **`case_fold` defaults to `True` here and `False` in `lexical_diversity`.** Deliberate:
  a lexicon is a list of dictionary forms and matching it is the whole operation, whereas
  case in a type count is a claim about the text. The divergence is documented in both
  places.
- **The spelling heuristic flags common Hungarian surnames.** `th` survives in surnames as
  an archaic spelling of plain *t*, so **Tóth, Horváth, Németh and Kossuth all match**, as
  do Széchenyi on `ch` and Wesselényi on `w`. This was found by a Hypothesis property that
  claimed native-alphabet words never trip the heuristic — the claim was false, and the
  counter-example arrived in one draw. The heuristic is off by default, `pos_tags` excludes
  proper nouns, the `__repr__` warns when any match came from spelling alone, and
  `PRE-MORTEM.md` records whether `th` should ship at all as a decision for a human.
- **A lexicon measures etymology; *idegenszó-arány* means assimilation.** A list built from
  dictionary etymology fields contains *ablak*, *király* and *pénz* — Slavic borrowings no
  speaker hears as foreign. Both quantities are defensible; publishing one under the
  other's name is not. `lexicon_id` is recorded so the question has an answer.

### Added — hierarchical distance

- `mean_hierarchical_distance`, `hierarchical_distances` and `mhd_from_counts` in
  `saphes.syntax`, implementing equation (2) of Jing & Liu (2015: 164) and their equation
  (4) for the text level. The paper's worked example is pinned as a doctest and reproduces
  exactly: *"Mr. Nixon was to leave China today ."* gives depths 2, 1, 1, 2, 3, 3 and
  MHD = 12/6 = 2.

  MHD is the vertical companion to MDD. Where dependency distance measures how far apart
  related words sit **in the string**, hierarchical distance measures how deep they sit
  **in the tree**. Jing & Liu propose it because the two come apart: a sentence can be flat
  and long-range, or deep and locally packed.

- `MhdResult` carries `total_depth`, `nodes`, `max_depth`, `punct_ancestors` and the same
  provenance fields as `MddResult`, so the score is recomputable from the record.

### Notes on hierarchical distance

- **The root leaves the denominator here too.** Its `HD` of 0 is not averaged in; the
  worked example is 12/6, not 12/7. `mhd_from_counts` refuses a `nodes` larger than
  `total_depth` for exactly that reason, since every counted token sits at depth 1 or more.
- **Hierarchical distance has no index space**, so the punctuation policies that re-index
  for MDD are equivalent for MHD. Only `"keep"` differs, by counting punctuation at all.
  The parameter is retained so one call site can serve both metrics.
- **Cycle detection lives here**, because this is the first function that walks the tree.
  `mean_dependency_distance` is a function of positions alone and cannot see a cycle; a
  test pins that difference rather than treating it as a defect in either.
- A punctuation token sitting *inside* the tree adds one to the depth of everything beneath
  it, and dropping it from the average does not undo that. `punct_ancestors` counts the
  affected tokens rather than leaving the inflation invisible.
- **The two engines invert.** Over the same fifteen sentences, HuSpaCy gives the higher MDD
  (1.6845 against 1.5328) and the *lower* MHD (1.5492 against 1.8128), with emtsv building
  trees two levels deeper. Neither parser is wrong; the annotation schemes trade flatness
  against depth. This is the case MHD exists to expose, and it is pinned as a test.

Dependency motifs (Jing & Liu 2017) are **not** included, and remain on the README roadmap.

### Added — parser adapters

- `saphes.adapters` — `from_spacy` and `from_conllu`, converting a parser's output into the
  `DepToken` sequences `saphes.syntax` measures. **Neither imports spaCy, HuSpaCy, emtsv or
  a CoNLL-U library.** `from_spacy` is duck-typed: it reads `doc.sents` and, per token, `i`,
  `head`, `is_punct` and `pos_`, so it works on a spaCy `Doc`, a HuSpaCy `Doc`, or anything
  presenting those attributes. `from_conllu` is a plain text reader over the specification,
  and takes any CoNLL-U file, treebank or otherwise.

- `experiments/adapter_fixtures/` — the benchmark corpus and the two generator scripts.
  Fifteen Hungarian sentences chosen for the structures that break adapters: legalese, a
  statute reference with nested brackets, verbless clauses, separated and negated igekötők,
  an em-dash aside, an embedded question. The scripts write into `tests/fixtures/`, the same
  way `lix_calibration/scripts/run.py` writes into `src/saphes/datasets/`.

### Notes on the adapters

The adapters were written against **real** HuSpaCy and emtsv output rather than hand-made
trees, and that changed three things:

- **spaCy marks the root with a self-loop** — `token.head is token`, not `head = 0`. Passed
  through unconverted it reaches `mean_dependency_distance` as a token governing itself,
  which raises correctly but for a baffling reason. `from_spacy` translates it.
- **emtsv's default output is not CoNLL-U.** `tok-dep` emits a header row and the column
  order `form wsafter anas lemma xpostag upostag feats id deprel head`; the `tok-dep-conll`
  task emits real ten-column CoNLL-U. `from_conllu` rejects the former with a message
  naming the task to use instead, rather than reading the wrong columns.
- **`is_punct` and the POS tag disagree.** HuSpaCy tags `(` as `PROPN` while setting
  `is_punct=True`, and hangs other tokens off it — which also makes the `orphaned_arcs` path
  a real case rather than a hypothetical. `from_spacy` reads `is_punct`; `from_conllu`, which
  has no such column, falls back to UPOS and documents the difference. `punct_tags` is a
  parameter, because the choice changes the score.

A fourth difference is pinned as a test rather than smoothed over: **emtsv attaches
sentence-final punctuation to `0`**, giving every sentence two roots, where HuSpaCy attaches
it to the main verb. `require_single_root=True` therefore discards the entire emtsv corpus
and none of the HuSpaCy one, from the same fifteen sentences. The default
`punctuation="collapse"` removes the punctuation before this matters, which is why it is the
default.

The two engines do not agree on MDD for the same sentences, and are not expected to. They
are different annotation schemes, not two attempts at one answer.

### Added — syntactic complexity

- `saphes.syntax` — mean dependency distance, the first metric here that measures
  structure rather than form. `mean_dependency_distance` takes parsed sentences and
  returns an `MddResult`; `dependency_distances` exposes the individual arcs;
  `mdd_from_counts` is the keyword-only arithmetic kernel. `DepToken` is the input
  contract — a `NamedTuple` of `(index, head, is_punct, pos)`, so any parser's output can
  be adapted without importing anything from saphes.

  The implementation follows equation (1) of Jing & Liu (2015: 163), which attributes the
  metric to Liu (2008: 170). Both of the worked examples in the literature are pinned as
  doctests and reproduce exactly: Jing & Liu's *"Mr. Nixon was to leave China today ."*
  at 1.17, and Zhang & Zhou's (2023) *"The quick brown fox jumped over the lazy dog."* at
  2.125.

- Three conventions are parameterised rather than hardcoded, because each is a place where
  published implementations silently disagree:

  - **`punctuation`** — `"collapse"` (the default) removes punctuation and **re-indexes**,
    which is what all three MDD papers do. `"ignore"` keeps the original index space and
    reports a larger number for any sentence with medial punctuation; no paper describes
    it, but software produces it, so it is available for diagnosing a disagreement.
    `"keep"` counts everything.
  - **`aggregation`** — `"macro"` (the default) averages per-sentence means, per Jing &
    Liu equations (3) and (4). `"micro"` pools every pair. They are different numbers; a
    naive implementation produces `"micro"` by accident.
  - **`min_sentence_length`** and **`require_single_root`** — the sentence filters used by
    Jing & Liu and by Futrell et al. respectively. Both default to off, because they are
    corpus-preparation choices rather than properties of the metric, and both are recorded
    on the result when used.

### Notes on dependency distance

- **The root is excluded from the denominator**, not just from the sum: *n* is the number
  of dependency **pairs**, so seven words give six. Dividing by the word count instead is
  a systematic deflation, and `TestPublishedAnchors` pins it.
- **A parse is a third stream, not a third token list.** `tests/test_contracts.py` gained
  `TestParseIsAThirdStream` to guard it: `lix(parses=...)` and
  `lexical_diversity(parses=...)` are `TypeError`s, and a token index sequence with gaps —
  punctuation removed without renumbering — raises rather than reporting inflated
  distances.
- **Futrell et al. (2015) argue against MDD**, preferring summed dependency length
  regressed on sentence length. They are cited for the arc-length definition, and their
  objection is stated in the explanation page rather than omitted.
- Non-projective sentences are measured normally, which Jing & Liu (2015: 164) explicitly
  license. There is no projectivity filter, and Hungarian needs there not to be one.

### Added

- `saphes.hungarian` — a phonotactically aware Hungarian letter counter. `hungarian_letters`
  returns the segmentation, `hungarian_letter_count` its length. It scans left to right
  taking the longest letter available rather than rewriting the string, reads doubled
  spellings (`ssz`, `ggy`, `ddzs`) as two letters, handles the productive `-ság`/`-ség`
  suffix by rule, and carries a table of 38 attested compound seams mined from the
  Webcorpus. Seams are stored as the shortest substring spanning the junction, so one
  entry covers a paradigm — and so a stem-final vowel that lengthens under suffixation
  (`zene` → `zené`) cannot walk out of the key. Both the boundary table and the suffix
  rule are parameters, because both change the number.
- `saphes.stem.hungarian_stems` — optional Snowball stemming behind a new `snowball` extra,
  for callers with no lemmatiser. Pure Python, no transitive dependencies, no model
  download. Refuses a raw string, and case-folds by default because the algorithm silently
  under-stems anything else.
- `TokenUnit` gains **`"stem"`**, so a stem stream can never be recorded as a lemma stream.
  Widening a `Literal` is backwards-compatible for existing callers.
- `recommended_threshold("hu-letters")` — the same equipercentile match remeasured under the
  letter policy. **The threshold is still 8**; what changes is the share behind it, 24.41%
  against 25.65% for Swedish rather than 27.33%.
- `experiments/hungarian_boundaries/` — the mining study behind the boundary table, with a
  committed review queue and the curation decisions. Its headline finding is negative: the
  crawl part's lemma annotations cannot supply boundary evidence, because they cover under
  1% of tokens and are emitted mostly where the analyser failed.

### Added — interpreting a Hungarian score

- **`ThresholdRecommendation.interpret(score)`** — the LIX bands, carried across to the
  calibrated Hungarian thresholds by equipercentile mapping. `LixResult.band` still returns
  `None` away from Björnsson's 6 and `lix` still takes no `language=`; the label lives on the
  object that knows both the threshold and the length policy.
- `src/saphes/datasets/_lix_bands.py` — generated by
  `experiments/lix_registers/scripts/publish_bands.py`.
- **New study `experiments/lix_registers/`** — LIX across four Hungarian registers, and the
  band mapping. Two tiers: Leipzig news is reproducible by anyone, while parliamentary
  speeches, corruption journalism and song lyrics come from sibling projects and are opt-in
  via `--corpus-root`. Every result row carries its tier and where its *B* came from.
- `experiments/lix_calibration/scripts/running_text.py` — reader for the Leipzig
  `-sentences.txt` member, which the study had never opened. It gives real *A*, *B* and *C*
  for **both** languages; until now the Swedish reference was only a word-length curve, so
  there was nothing to map bands from. No new download.

### Notes on the band mapping

- **Three of four boundaries are published; the top one is not.** Swedish news puts about
  0.04% of its text above LIX 60, so that boundary is read off five windows out of twelve
  thousand. Above the `standard` band `interpret` returns `None` rather than guess. The
  published boundaries hold to under a point across a tenfold change in window length.
- Under the letter policy the boundaries land within 2.63 points of the Swedish ones (30 →
  32.63, 40 → 40.18, 50 → 48.19); under the character policy, up to 5.45.
- **Retuning the threshold could never have made the score interpretable.** The calibration
  rescales the second LIX term only, and Hungarian news writes sentences three words longer
  than Swedish (18.30 against 15.37). The bands are what absorb the first term.
- The mapping preserves *how much text falls in each band*. **Nobody checked whether Hungarian
  readers find those texts correspondingly hard** — that needs a graded corpus, and none was
  used.
- **LIX separates prose from non-prose, not prose from prose.** Song lyrics come out at 23.56
  and the three prose registers sit within six points of one another, all in the same band,
  though one is spoken oratory and another dense investigative writing.

### Documentation

- **New: [Measure Hungarian text](docs/how-to/measure-hungarian-text.md)** — the calibrated
  threshold, the letter count and the stemmer in one recipe. That combination previously
  appeared on no page.
- `install.md` documented one of the two extras. It now documents both, with a table.
- `index.md`'s token-stream table, the glossary's `Unit` entry, and the package docstring
  that `reference/index.md` renders were all still two-valued after `"stem"` shipped.
- The reference index now lists the modules instead of rendering five sentences about two
  functions.
- Two cross-references promised coverage their targets did not contain: the letter-policy
  calibration in `use-a-calibrated-threshold.md`, and calibrating on letters in
  `calibrate-a-new-language.md`. Both targets now cover it.
- `two-token-streams.md` claimed a theorem that is **false for stems** — a stemmer can give
  one lemma two stems, so nothing follows about stem-TTR against lemma-TTR. Bounded, with
  the reason.
- `why-implementations-disagree.md` said every divergence is the sentence count. True for
  English; *C* is a second axis wherever a letter is not a character.
- `diagnose-a-surprising-result.md` gained the missing `snowballstemmer` `ImportError`, the
  third unit, and the "my Hungarian count is one letter short" symptom.
- The glossary gained *Digraph*, *Geminate* and *Morpheme boundary*.

### Fixed

- **`CALIBRATIONS["hu-letters"]` no longer borrows the character policy's agreement panel.**
  It claimed seven concurring curves when one had been measured under the letter policy. Its
  panel is now measured under that policy — `mokk-{4pct,8pct,full,4pct-asterisk-dropped}` and
  `leipzig-hun`, all recounted in letters — and the honest answer is weaker than the borrowed
  one: **three of five choose 8, two choose 7**. The residual on the primary curve is
  nonetheless smaller than the character policy's (0.0124 against 0.0168). The two records
  also no longer carry byte-identical caveats.
- `experiments/lix_calibration/lix_calibration.ipynb` crashed on the regenerated record —
  `record["recommendation"]` became a list under `"recommendations"` when the second key
  shipped. It now reports both and plots the boundary-aware letters curve.
- `findings.md` documented only the first recommendation, so the shipped `hu-letters` numbers
  appeared in the JSON and the package literal but in no writeup — which also falsified
  `recommended_threshold`'s own claim that `findings.md` is the cross-check on the literal.
- The provenance record stamped `method.length_policy = "nfc"` globally while holding curves
  under three policies. Dropped; the truth is per-curve and always was.
- `experiments/lix_calibration/scripts/utils.py` — `log()` now flushes. These scripts run for
  minutes and are usually watched through a redirect, where a buffered stdout showed nothing
  at all until the process exited.
- `hungarian_letter_count` no longer miscounts a digraph that spans a morpheme boundary.
  `község` is now 6 letters, not 5.
- `hungarian_letter_count` no longer manufactures digraphs. The old implementation replaced
  each digraph with its first character, so `sz` after a `z` created a fresh `zs` that was
  then collapsed too: `közszolgálati` came out at 11 letters instead of 12. This second
  failure had never been documented. It affects 0.014% of Webcorpus tokens.

### Changed

- **Breaking:** `hungarian_letter_count` moved from `saphes.calibration` to
  `saphes.hungarian`. The top-level `from saphes import hungarian_letter_count` is
  unchanged; only `from saphes.calibration import ...` breaks.
- `collapse_digraphs` stays in `saphes.calibration` as the naive primitive it always was,
  now with both known failures pinned in its doctests rather than one.
- The calibration study gains a `mokk-4pct-letters` curve; `mokk-4pct-digraphs-collapsed`
  keeps its old collapse-based meaning so the published sensitivity column stays comparable.
- `_lix_calibration.py` `SCHEMA_VERSION` 1 → 2: `CALIBRATIONS` keys now name a language
  *and* a length policy.

### Notes

- **The recalibration changed nothing, and that is the result.** Boundary-aware counting
  moves the corpus-level long-word share by 0.01 percentage points across the full
  560-million-token stratum, and every letter-aware curve still chooses 8. It could not have
  moved far: a correct letter count is trapped between the naive collapse, which over-merges,
  and the raw character count, which under-merges, and both already chose 8.
- Two of the thirteen `false_digraph_roots` proposed for this work were not shipped.
  `földzó` matches nothing in a 560-million-token corpus and `vízsu` matches nothing as a
  type; both are invented substring fragments rather than attested words.

## [0.1.0] - 2026-07-29

### Added

- `lix()` — the LIX readability index with `long_word_threshold` as a first-class parameter.
  A long word is `len(word) > threshold`, so the default 6 means seven letters or more.
- Three ways to supply the sentence count *B*: segmented from raw text with a pluggable
  splitter, pre-split, or an explicit integer. The source is recorded on the result.
- `LixResult` — score plus *A*, *B*, *C*, every parameter used, and the saphes version.
  `band` returns `None` off `long_word_threshold=6`, where Björnsson's Swedish bands no
  longer apply.
- `rix()` and `LixResult.rix` — long words per sentence.
- `interpret_lix()` and the overridable `LIX_BANDS` constant.
- `word_length()` with an explicit `length_policy`: NFC normalisation by default, plus
  grapheme, raw-codepoint, and caller-supplied callable options. Decomposed Unicode would
  otherwise inflate every length, which hits polytonic Greek and accented Hungarian hardest.
- `lexical_diversity()` — TTR with a **required** `unit` (`"lemma"` or `"surface"`), opt-in
  case folding, and an optional MATTR window.
- `mattr()` — the moving-average TTR, absorbed verbatim from the duplicate implementations
  in `music_networks` and `kmdb_dashboard`, with its bare-float signature preserved so those
  call sites change only their import line.
- `DiversityResult`, whose repr carries the length-comparability warning.
- `segment.words()` and `segment.sentences()` — a dependency-free, abbreviation-aware
  splitter ported from `lexograph`. NLTK Punkt is available behind the optional `punkt`
  extra.
- Bundled English, Hungarian and Ancient Greek samples with parallel surface/lemma
  annotation, so the two-contracts asymmetry is demonstrable from one source of truth.
- `tests/test_contracts.py` — the regression guard against wiring both metrics to a single
  token stream, including a Hypothesis property proving lemma-TTR can never exceed
  surface-TTR.
- `saphes.calibration` — pure, data-free machinery for calibrating the LIX long-word
  threshold from a token-weighted word-length distribution.
  - `length_curve(counts, ...)` takes a **frequency mapping, never a token list**, so
    type-weighting — the study's most likely silent failure — is structurally impossible.
  - `match_threshold(target, reference, ...)` does equipercentile matching, and carries the
    whole curve plus the runner-up, so a contested answer is visible as one.
  - `collapse_digraphs` / `hungarian_letter_count` — a Hungarian letter count for the
    digraph sensitivity check, shipping with a doctest of its own failure case.
- `recommended_threshold(language)` → `ThresholdRecommendation`, carrying the threshold, the
  matched and reference shares, the bracket, the runner-up, which curves agreed, the sources
  and the caveats. `int(rec)` gives the bare threshold.
- **Hungarian ships calibrated at `long_word_threshold=8`**, matching Swedish's 25.65%
  long-word share at Björnsson's 6. Six independently computed curves agree — two Hungarian
  corpora nineteen years apart, three sampling strata, and a digraph-aware variant.
- `experiments/lix_calibration/` — the full study: streaming readers for the MOKK Webcorpus
  frequency lists and Leipzig word lists, the sensitivity panel, and end-to-end validation
  against a crawl part with real sentence counts. Committed artifacts: `findings.md`,
  `validation.md`, `results/lix_calibration.json`.

### Notes

- The core has no runtime dependencies.
- `lix` deliberately takes **no** `language=` parameter. Pass the threshold explicitly so
  the choice is visible at the call site.
- Verified against `textstat` 0.7.13: given the same sentence count, LIX scores match
  exactly. Free-running divergence is entirely sentence segmentation — `textstat` silently
  discards sentences of two words or fewer.
- The calibration was validated end to end on 10.3M words and 709k real sentences of
  Hungarian web text: at Björnsson's 6 the corpus scores LIX 60.4 ("very difficult"); at the
  calibrated 8 it scores 43.4. The calibration predicted a 27.33% long-word share and the
  running text gives 28.93%.
