# Review guide — Hungarian iteration

Everything on branch `hungarian-graphemes-and-stemming`, as six commits against `main`.
64 files, +5,504 / −332.

Each commit was verified green on its own — `make ci` and, where it touches `docs/`,
`mkdocs build --strict` — so the branch bisects.

This is the map. `CHANGES_SUMMARY.md` is the full account; this tells you what to look at, in
what order, and what each decision costs to undo.

---

## Step 0 — Confirm it is green (2 minutes)

```bash
git checkout hungarian-graphemes-and-stemming
uv sync --all-extras

make ci                       # ruff format+lint, ty, 342 tests incl. every docstring example
uv run mkdocs build --strict  # every `>>>` in every docs page is executed by the test run
```

Two optional checks, both slow:

```bash
cd experiments/lix_calibration && uv run jupyter nbconvert --to notebook \
    --execute --output /tmp/nb.ipynb lix_calibration.ipynb   # ~1 min
uv run python experiments/lix_registers/scripts/run.py --tier1-only  # ~20 min
```

The second is the one that matters for reproducibility: it must produce a complete result on a
machine with none of your sibling projects. It overwrites `results/registers.json` with a
tier-1-only record, so `git checkout -- experiments/lix_registers/results/` afterwards.

---

## Step 1 — See the shape of it (5 minutes)

```bash
uv run python - <<'EOF'
from saphes import (hungarian_letters, hungarian_letter_count, hungarian_stems,
                    lexical_diversity, lix, recommended_threshold, words)

print(hungarian_letters("kulcsszó"))            # ['k','u','l','cs','sz','ó']
print(hungarian_letter_count("község"))         # 6 — was 5 before this branch
print(hungarian_stems(["ház", "házban", "házak"]))

hu = recommended_threshold("hu-letters")
print(hu.threshold, hu.bracket, sorted({t for _, t in hu.agreement}))
print(hu.interpret(42.11), hu.interpret(50.0))  # 'standard', None
EOF
```

Then read, in this order:

1. `experiments/lix_registers/results/findings.md` — the register panel and band mapping (93 lines)
2. `docs/explanation/what-a-hungarian-lix-score-means.md` — the argument (97 lines)
3. `experiments/lix_calibration/findings.md` §5 — the letter calibration (143 lines total)
4. `CHANGES_SUMMARY.md` — everything else (148 lines)

---

## Step 2 — The decisions that are yours

### A. The boundary table — the one that needs a Hungarian speaker

I mined 121 candidates from the MOKK Webcorpus and filled in the verdicts myself: **70 accept,
51 reject, 38 shipped seams**. Every entry is a linguistic judgement the corpus can support but
not prove. This is the highest-value thing you can check.

Audit trail: `experiments/hungarian_boundaries/results/decisions.tsv` against
`candidates.tsv`. Method and its limits: that directory's `README.md`.

Each seam adds exactly one letter to the count:

| seam | marked as | corpus tokens | letters |
|---|---|---:|---|
| `alvászavar` | `alvás-zavar` | 596 | 9 → 10 |
| `beszédzavar` | `beszéd-zavar` | 124 | 9 → 10 |
| `identitászavar` | `identitás-zavar` | 113 | 13 → 14 |
| `magatartászavar` | `magatartás-zavar` | 92 | 14 → 15 |
| `rendzavar` | `rend-zavar` | 91 | 8 → 9 |
| `látászavar` | `látás-zavar` | 93 | 9 → 10 |
| `evészavar` | `evés-zavar` | 87 | 8 → 9 |
| `ritmuszavar` | `ritmus-zavar` | 79 | 10 → 11 |
| `működészavar` | `működés-zavar` | 65 | 11 → 12 |
| `vérzészavar` | `vérzés-zavar` | 65 | 10 → 11 |
| `légzészavar` | `légzés-zavar` | 57 | 10 → 11 |
| `kékeszöld` | `kékes-zöld` | 343 | 8 → 9 |
| `világoszöld` | `világos-zöld` | 341 | 10 → 11 |
| `sárgászöld` | `sárgás-zöld` | 226 | 9 → 10 |
| `szürkészöld` | `szürkés-zöld` | 193 | 9 → 10 |
| `smaragdzöld` | `smaragd-zöld` | 155 | 10 → 11 |
| `haragoszöld` | `haragos-zöld` | 102 | 10 → 11 |
| `zöldzón` | `zöld-zón` | 262 | 7 → 8 |
| `leveszöldség` | `leves-zöldség` | 51 | 11 → 12 |
| `nyílászár` | `nyílás-zár` | 862 | 7 → 8 |
| `évadzár` | `évad-zár` | 389 | 6 → 7 |
| `rövidzár` | `rövid-zár` | 329 | 7 → 8 |
| `honvédzászló` | `honvéd-zászló` | 193 | 10 → 11 |
| `védzáradék` | `véd-záradék` | 163 | 9 → 10 |
| `vízsug` | `víz-sug` | 832 | 5 → 6 |
| `gázspray` | `gáz-spray` | 318 | 7 → 8 |
| `gázsütő` | `gáz-sütő` | 75 | 6 → 7 |
| `házsor` | `ház-sor` | 280 | 5 → 6 |
| `eszközsor` | `eszköz-sor` | 116 | 7 → 8 |
| `pénzsóvár` | `pénz-sóvár` | 105 | 8 → 9 |
| `pénzsegély` | `pénz-segély` | 54 | 8 → 9 |
| `nehézsúly` | `nehéz-súly` | 327 | 7 → 8 |
| `nehézsors` | `nehéz-sors` | 63 | 8 → 9 |
| `táncsport` | `tánc-sport` | 140 | 8 → 9 |
| `táncstúdió` | `tánc-stúdió` | 69 | 9 → 10 |
| `fúvószen` | `fúvós-zen` | 1,102 | 8 → 9 |
| `vonószen` | `vonós-zen` | 130 | 8 → 9 |
| `kiszombor` | `kis-zombor` | 190 | 8 → 9 |

Ones I would look at first: `kiszombor` (a toponym, kept only because attested),
`ritmuszavar` (chosen over listing `szívritmuszavar` separately, since substring matching
covers both), `vízsug` and `fúvószen` (fragments rather than words — deliberate, so they
cover the paradigm, and unlike the `vízsu`/`földzó` I rejected they are backed by attested
forms).

A seam must stop before anything that can alternate, because substring matching only follows
the key rightward. `fúvós-zene` looks like the tidier entry and is the wrong one: Hungarian
lengthens the stem-final vowel, so `zene` becomes `zené` and the key misses `fúvószenét`
entirely. `fúvószenét` (53) and `zöldzónában` (71) were curated as rejects on that basis
before it was understood, and both are now accepted.

Rejects I read as **real** digraphs, not seams: `mozsár`, `bizsereg`, `macsó`, `rácsokat`
(`rács` + `okat`, not `rác` + `sokat`), `leszen`, `estélyen`, `versenyes`, and the `-szám`
family (`motorszám`, `kilószám`).

**To undo:** the table is a plain dict in `src/saphes/hungarian.py`. Deleting an entry changes
one number and breaks no test. It is also a parameter — `hungarian_letter_count(word,
boundaries={...})` — so a caller can override it entirely.

### B. Should `c(?=s[áé]g)` ship at all?

The `-ság`/`-ség` suffix is handled by rule rather than a list, because a list would be endless
(`egyezség`, `hitközség`, `nagyközség`, `ínyencség`, `féligazság`…). The `z` half is safe. The
`c` half cannot tell `malacság` (`malac` + `ság`) from `kavicságy` (`kavics` + `ágy`).

The full corpus yields exactly one such word above the frequency floor — `kavicságy`, 55 tokens
— now in `BOUNDARY_EXCEPTIONS`. Dropping the `c` half costs `malacság`, `bohócság`,
`ínyencség`, all rare.

**To undo:** one regex in `src/saphes/hungarian.py` (`_SUFFIX_RULE`), or
`suffix_rule=False` per call.

### C. Does the band mapping claim enough to ship?

`recommended_threshold("hu-letters").interpret(42.11)` → `'standard'`.

What it claims: a mapped band holds **the share of running text its Swedish original held**.
That is checkable and it is the whole of the claim.

What it does not claim: that Hungarian readers find those texts correspondingly hard. Nobody
measured that; it needs a graded corpus and there is not one here. The docstring, the reference
page and the explanation page all say so explicitly — worth checking you are comfortable with
how loudly.

Three of four boundaries published; the top one withheld because Swedish news puts ~0.04% of
its text above LIX 60, so it rests on 5 windows out of 12,000.

**To undo:** `interpret()` in `src/saphes/calibration.py` and
`src/saphes/datasets/_lix_bands.py` are self-contained. Removing both leaves everything else
working; `LixResult.band` was never touched.

### D. `hu-letters` has a split panel

Three of five curves choose 8, two choose 7, bracket `(7, 8)`. The primary curve's residual is
the *better* of the two calibrations (0.0124 against `hu`'s 0.0168), so I left the winner at 8.
The previous record claimed seven concurring curves; that was borrowed from the character
policy and was wrong.

**To undo:** the winner comes from the data, not a choice. If you want 7, that is a change to
`match_threshold`'s tie-breaking, not a constant.

### E. Tier-2 registers are not externally reproducible

`parlamonitor`, `kmdb` and `lyrics` read your sibling repos. Marked in every result row, in the
experiment README and in the findings. `--tier1-only` is the path a clean checkout can run.

`kmdb` is read from SQLite rather than its token Parquet, so its *B* is **segmented**, not
corpus-supplied. Reading the Parquet needs pyarrow — a large dependency for one panel row.
Stated in the table rather than hidden.

---

## Step 3 — API changes worth a glance

| change | reversible? |
|---|---|
| `TokenUnit` gains `"stem"` | Widening a `Literal`; backwards-compatible for homer, music_networks, kmdb_dashboard |
| `hungarian_letter_count` moved `saphes.calibration` → `saphes.hungarian` | **Breaking** for `from saphes.calibration import ...`; the top-level import is unchanged |
| `interpret()` on `ThresholdRecommendation` | New method; `lix` still takes no `language=`, `LixResult.band` still returns `None` off 6 |
| `hungarian_letter_count("község")` 5 → 6 | The old value was a documented bug |
| `_lix_calibration.SCHEMA_VERSION` 1 → 2 | Keys now name a language *and* a length policy |
| new `snowball` extra | `snowballstemmer` 3.1.1, pure Python, zero transitive deps (verified) |

---

## Step 4 — Three corrections to the original spec

Worth confirming you agree, since everything downstream assumes them:

1. **`dzsungel` → 7 was wrong.** `dzs·u·n·g·e·l` is six letters.
2. **The `$` sentinel was fixing a real bug in shipped code** — the old counter rewrote rather
   than consumed, so `sz` after a `z` manufactured a `zs`: `közszolgálati` came out at 11
   letters instead of 12. Undocumented anywhere.
3. **The spec's own pipeline had a third bug** — geminates before digraphs let `ssz` beat `cs`,
   so `kulcsszó` came out at 7 instead of 6. A maximal-munch scanner avoids all three.

Also: `földzó` matches **nothing** in a 560M-token corpus and `vízsu` matches nothing as a
type. Neither shipped.

---

## What I deliberately did not touch

- `LixResult.band` still returns `None` away from threshold 6, and `lix` still takes no
  `language=`. Adding dispatch there would undo a deliberate design.
- `collapse_digraphs` keeps its cascade, now with both known failures pinned in its doctests.
- Two pre-existing lint errors in `download_data.py` and `leipzig.py`, outside this work.
- Ancient Greek. The `running_text.py` reader and the band machinery transfer unchanged.

---

## If you want changes

Everything is staged and uncommitted, so `git diff --cached <path>` shows any file in
isolation and `git restore --staged --worktree <path>` reverts one. Nothing has been pushed and
no PR exists yet.
