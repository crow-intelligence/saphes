# Adapter fixtures

Real parser output for `tests/test_adapters.py`, recorded once and committed.

`saphes.adapters` converts HuSpaCy and emtsv output into `DepToken` sequences. Testing that
conversion against hand-written trees would test my idea of what those parsers produce. It
would also have been wrong: writing the adapters against real output changed three things.

## What the real output changed

1. **spaCy marks the root with a self-loop.** `token.head is token`, not `head = 0`. Passed
   through unconverted it reaches `mean_dependency_distance` as a token governing itself,
   which raises — correctly, but for a baffling reason.
2. **emtsv's default output is not CoNLL-U.** `tok-dep` emits a header row and the column
   order `form wsafter anas lemma xpostag upostag feats id deprel head`. The `tok-dep-conll`
   task emits real ten-column CoNLL-U. The plan for this work assumed the default was
   already CoNLL-U; it is not.
3. **`is_punct` and the POS tag disagree.** HuSpaCy tags `(` as `PROPN` while setting
   `is_punct=True`, and hangs other tokens off it. So `from_spacy` reads `is_punct`, and
   `from_conllu` — which has no such column — falls back to UPOS and documents that this is
   a real difference between the two adapters rather than an oversight.

A fourth difference is pinned as a test rather than fixed: **emtsv attaches sentence-final
punctuation to `0`**, giving every sentence two roots, where HuSpaCy attaches it to the main
verb. `require_single_root=True` therefore discards every emtsv sentence and no HuSpaCy one.

## The corpus

`corpus.txt` — fifteen Hungarian sentences chosen for the structures that break adapters,
not for representativeness:

- legalese and a statute reference with nested brackets (`339. § (1) bekezdése`)
- verbless clauses (`Micsoda nap!`, `Hány óra?`)
- separated and negated igekötők (`elment` … `El sem mentem volna`)
- an em-dash aside, coordinated clauses, an embedded question
- a proverb with a comma-separated subordinate clause

## What the two engines produce

Measured on the fifteen sentences, `punctuation="collapse"`:

| engine | MDD (macro) | MDD (micro) | pairs | tokens | roots | punct dropped | orphaned arcs |
|---|---:|---:|---:|---:|---:|---:|---:|
| HuSpaCy | 1.6845 | 1.9355 | 93 | 109 | 15 | 27 | **1** |
| emtsv | 1.5328 | 1.7526 | 97 | 112 | 30 | 23 | 0 |

Read the columns rather than the score. **Roots**: 15 against 30 — one per sentence for
HuSpaCy, two for emtsv, which is the punctuation-attachment difference. **Punct dropped**:
27 against 23 — the engines do not agree on what punctuation *is*, before they disagree
about where it attaches. **Orphaned arcs**: HuSpaCy's single orphan is the statute
reference, where tokens hang off a bracket that `is_punct` marks for removal; that path was
written defensively and turns out to be reachable from one sentence of ordinary legal
Hungarian.

The macro/micro gap — about 0.25 on both engines — is larger than the gap *between* the
engines. Which aggregation you use matters more here than which parser you use, which is
why both are recorded on the result.

These numbers are a fixture check, not a finding. Fifteen sentences establish nothing about
Hungarian.

## Running it

Neither engine can run in CI — HuSpaCy pulls spaCy plus a 110 MB model, emtsv is a 9.9 GB
Docker image that takes about two minutes to start. Both write into `tests/fixtures/`,
the same way `lix_calibration/scripts/run.py` writes into `src/saphes/datasets/`.

```bash
# HuSpaCy — in a throwaway venv, never in the project's own
uv venv /tmp/hus-venv --python 3.12
curl -sL -o /tmp/hu_core_news_md-3.8.0-py3-none-any.whl \
    https://huggingface.co/huspacy/hu_core_news_md/resolve/v3.8.0/hu_core_news_md-any-py3-none-any.whl
uv pip install --python /tmp/hus-venv/bin/python spacy /tmp/hu_core_news_md-3.8.0-py3-none-any.whl
/tmp/hus-venv/bin/python experiments/adapter_fixtures/scripts/run_huspacy.py

# emtsv
docker pull mtaril/emtsv
uv run python experiments/adapter_fixtures/scripts/run_emtsv.py
```

The model wheel is renamed on download because its published filename
(`hu_core_news_md-any-py3-none-any.whl`) is not PEP 440 and `uv` refuses it.

## Outputs

- `tests/fixtures/huspacy.json` — one record per sentence, holding exactly the token
  attributes `from_spacy` reads, plus surface forms so a human can check what was parsed.
  Indices are left **document-global**, as spaCy reports them, so the adapter's renumbering
  is what the test exercises.
- `tests/fixtures/emtsv.conllu` — verbatim `tok-dep-conll` output.

Recorded with HuSpaCy `hu_core_news_md` 3.8.0 on spaCy 3.8.16, and `mtaril/emtsv:latest` as
of 2026-09-08. Re-running with different versions will change the numbers; the parity tests
assert the *shape* of the disagreement rather than exact scores, so they should survive an
upgrade, and `test_punctuation_comes_from_is_punct_not_the_tag` fails loudly if a new model
stops covering the tag mismatch.
