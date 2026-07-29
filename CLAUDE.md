# saphes — project notes for Claude

Readability (LIX) and lexical diversity (TTR/MATTR). Deliberately small: two metrics, with
the parameters other implementations hardcode. Fifth member of the corpus-lx family
(chronowords, kenon, keyflux, lexograph).

## Tech stack

- **pyenv** (3.12, see `.python-version`), **uv** (deps + lock), **ruff** (format + lint),
  **ty** (type check)
- **pytest** with `--doctest-modules` over `src` and `tests`, **Hypothesis**, **mutmut**
- **mkdocs-material** + **mkdocstrings**, published on ReadTheDocs
- **The core has no runtime dependencies.** `dependencies = []` in `pyproject.toml`, and
  `tests/test_package.py::TestDependencyFreedom` enforces it in a fresh interpreter. NLTK is
  optional (`punkt` extra); `textstat` is dev-only, for the cross-check.

## Module layout (src/saphes/)

- `_types.py` — shared aliases. `TokenUnit` is the central one.
- `segment.py` — dependency-free word/sentence splitter, ported from
  `lexograph/src/lexograph/segment/units.py`. **Named `segment`, not `tokenize`**, because
  `tokenize` shadows a stdlib module that `doctest` imports transitively.
- `readability.py` — `lix`, `lix_from_counts`, `rix`, `word_length`, `interpret_lix`,
  `LIX_BANDS`, `LixResult`.
- `diversity.py` — `lexical_diversity`, `ttr_from_counts`, `mattr`, `DiversityResult`.
- `calibration.py` — `length_curve`, `match_threshold`, `recommended_threshold`,
  `collapse_digraphs`, `hungarian_letter_count`. **Pure and data-free**, because
  `--doctest-modules` runs everything under `src/` on a CI runner with no corpus.
- `datasets/` — inline EN/HU/GRC samples with parallel `(form, lemma)` annotation, plus
  `_lix_calibration.py`, which is **generated** by the calibration study.

Tests are flat in `tests/`, one file per module, plus `tests/test_contracts.py` — the one
deliberate exception, because what it tests spans two modules.

## The invariant that matters most

**The two metrics require opposite token streams.** `lexical_diversity` wants lemmas;
`lix` wants surface forms. Feeding one stream to both produces no error and no NaN — just a
plausible wrong number.

If you touch either module, `tests/test_contracts.py` is the guard. Do not "simplify" it by
wiring both metrics to a single token stream, and do not relax the pinned gap floors to bare
`>` — a gap of exactly 0.0 is precisely the failure being guarded against.

Related invariants, all deliberate:

- `unit` on `lexical_diversity` is keyword-only with **no default**. Do not add one.
- `lix` accepts no `unit=` parameter at all. That is what makes the guard work.
- A raw string into `lexical_diversity` raises unless `unit="surface"`.
- `mattr` keeps its bare-float signature `mattr(tokens, window=100) -> float`, unlike
  everything else here, so `music_networks` and `kmdb_dashboard` can drop their duplicate
  copies by changing only an import line. Do not "harmonise" it into a result object.
- Result `__repr__`s omit `saphes_version`; otherwise every release breaks every doctest
  that prints a result.
- `LixResult.band` returns `None` off `long_word_threshold=6`.
- `calibration.length_curve` takes a **frequency mapping, never a token list**. That is what
  makes type-weighting — the calibration study's likeliest silent failure — impossible to
  express. Do not add a token-list convenience overload.
- `lix` takes **no** `language=` parameter. The calibrated threshold is passed explicitly.

## The calibration study

`src/saphes/datasets/_lix_calibration.py` is **generated** — regenerate it with
`uv run python experiments/lix_calibration/scripts/run.py`, never edit it by hand. The
generator runs `ruff format` on its own output, so re-running reproduces the committed file
byte for byte apart from the timestamp.

`run.py` asserts regression anchors and exits non-zero rather than publishing numbers that
drifted. If you change a reader and an anchor fires, work out which behaviour is correct
before updating it — that mechanism has already caught one real filter-ordering bug.

Hungarian ships at `long_word_threshold=8`. See `experiments/lix_calibration/README.md` for
the four things that decide whether the study is right (token weighting, the 4% stratum, the
trailing-asterisk marker, and ISO-8859-2 decoding).

## Dev commands

```bash
make ci          # format check, lint, typecheck, test — everything CI runs
make test        # pytest with doctests and coverage
uv run mkdocs build --strict
uv run mkdocs serve
SAPHES_MUTATION=1 uv run mutmut run    # dev-only, not in CI
uv run python examples/lix_quickstart.py
```

## Local dev setup

```bash
pyenv local 3.12
uv sync --all-extras
```

## Release process

1. Bump `version` in `pyproject.toml`.
2. Add a `CHANGELOG.md` entry under a new `## [x.y.z] - YYYY-MM-DD` heading.
3. Commit `Release <version>`.
4. Tag `v<version>`.
5. `gh release create` — `publish.yml` builds and publishes to PyPI via OIDC.

## Conventions

- Result objects are `@dataclass(frozen=True, slots=True)` with a Google `Attributes:`
  block per field and a `to_dict()` carrying a doctest. Never NamedTuple.
- Docstring sections in order: summary, prose, `Args:`, `Returns:`, `Raises:`, `Contract:`,
  `Examples:`. `Contract:` lists the invariants the property tests must cover.
- Errors bind the message first: `msg = "..."` then `raise ValueError(msg)`.
- Hypothesis strategies live in `tests/strategies.py`, constrained to **named alphabets** —
  arbitrary `st.text()` generates lone combining marks under which "word length" is
  genuinely ambiguous.
- `@settings(...)` goes above `@given(...)`.
- Every public function needs an `Examples:` block; doctests run in CI by default.

## Downstream consumers

- **homer** — `data/processed/gold_lemmas.parquet`: `form` → `lix`, `lemma` →
  `lexical_diversity`. The treebank drops punctuation, so *B* must be supplied explicitly.
- **music_networks** — `SongDoc.text` → `lix`, `SongDoc.tokens` → `lexical_diversity`.
  Never the reverse: `.tokens` is content-lemmas-only, lowercased, stop-word-stripped, with
  glued n-grams.
- **kmdb_dashboard** — has `sent_idx`, so it is the one corpus here that can supply real
  sentence counts.

## Known follow-ups

- The same calibration study for **Ancient Greek**, for the Homer project. The method
  transfers unchanged; only the corpus differs. Note Greek needs the NFC length policy to
  be honoured end to end, and the treebank cannot supply *B*.
- No logo yet; the README and mkdocs theme have no banner.
- `segment.sentences(punkt=True)` is untested — exercising it would download an NLTK model
  in CI.
