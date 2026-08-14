# Reproduce the calibration study

The Hungarian threshold that ships with saphes came from a study in
`experiments/lix_calibration/`. This is how to run it yourself.

You need the repository, not the installed package — the study is not part of the wheel.

## 1. Smoke test first

The smoke path downloads 2.8 MB instead of 115 MB and finishes in about a minute. Run it
before committing to the full pipeline.

```bash
uv run python experiments/lix_calibration/scripts/download_data.py --smoke-test
uv run python experiments/lix_calibration/scripts/run.py --smoke-test
```

This writes the results JSON but deliberately does **not** regenerate the shipped literal or
`findings.md`, because a truncated word list is not what the package should ship.

## 2. Full run

```bash
uv run python experiments/lix_calibration/scripts/download_data.py
uv run python experiments/lix_calibration/scripts/run.py
```

About four minutes. Outputs:

- `experiments/lix_calibration/results/lix_calibration.json` — full provenance, every curve
- `experiments/lix_calibration/findings.md` — the writeup
- `src/saphes/datasets/_lix_calibration.py` — the literal the package ships

The generator runs `ruff format` on its own output, so re-running reproduces the committed
file byte for byte apart from the timestamp.

## 3. Validate against running text

```bash
uv run python experiments/lix_calibration/scripts/download_data.py --with-corpus-part
uv run python experiments/lix_calibration/scripts/validate_b.py
```

A further 370 MB. This is the only step with real sentence counts, so it is the only one that
can show what the threshold does to an actual LIX score.

## If an anchor fires

`run.py` asserts regression numbers measured before the pipeline existed and exits non-zero
rather than publishing figures that drifted:

```
[anchor] MISMATCH leipzig-swe share>6: expected ~0.2565, got 0.2601
[anchor] The reader is producing different numbers. Stop and find out why.
```

Work out which behaviour is correct before updating the anchor. That mechanism has already
caught one real bug — a minimum-frequency filter applied before merging casing variants
instead of after.

## Downloads

All downloads are cached in `experiments/lix_calibration/data/`, which is gitignored, and
skipped if already present. Sizes and SHA-256 hashes are recorded in `data/manifest.json`.
The corpora are roughly 900 MB in total; the committed artifact is the results JSON, never
the corpus.

## Citation

If you use these figures, cite the corpora:

- Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). *Creating open language resources for
  Hungarian.* LREC.
- Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). *Web-based frequency dictionaries for
  medium density languages.* Web as Corpus, ACL.
- Goldhahn, Eckart, Quasthoff (2012). *Building large monolingual dictionaries at the Leipzig
  Corpora Collection.* LREC.

## Related

- [Calibration data](../reference/calibration-data.md) — the numbers the study produced.
- [Calibrate a new language](calibrate-a-new-language.md) — the same method for your own
  corpus.
