# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

- The same calibration study for Ancient Greek, for the Homer project. The method transfers
  unchanged; only the corpus differs.

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
