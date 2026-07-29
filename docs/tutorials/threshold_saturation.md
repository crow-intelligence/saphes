# Threshold and saturation

## The problem

```
LIX = A/B + (C * 100)/A
```

The second term is the share of running words that are "long", as a percentage.
Björnsson set the boundary at **more than six letters**, fitted to Swedish. Every Python
implementation hardcodes that 6.

For Swedish it is a reasonable cut. Measured over the Leipzig `swe_news_2022_1M` corpus,
token-weighted, **25.65%** of running Swedish words are longer than six letters — so the
term varies usefully between texts.

For Hungarian it is not. Over the full MOKK Webcorpus frequency list (4% stratum, 560
million running tokens), **44.52%** of running words are longer than six. Nearly half of
everything is "long", so the second term sits high for every text and stops distinguishing
them. Ancient Greek behaves the same way for the same reason.

## The measured curves

Token-weighted share of running words strictly longer than each threshold. Five
independently built curves — two Hungarian corpora nineteen years apart, three sampling
strata of one of them, and the Swedish reference.

| >T | MOKK 4% | MOKK 8% | MOKK full | Leipzig HU | **Leipzig SV** |
|---:|---:|---:|---:|---:|---:|
| 4 | 64.00% | 63.49% | 61.14% | 62.24% | 46.98% |
| 5 | 53.98% | 53.16% | 50.55% | 51.87% | 35.37% |
| **6** | 44.52% | 43.44% | 40.74% | 41.68% | **25.65%** |
| 7 | 35.38% | 34.24% | 31.60% | 31.92% | 18.60% |
| **8** | **27.33%** | 26.20% | 23.75% | 23.43% | 13.00% |
| 9 | 19.83% | 18.88% | 16.87% | 16.34% | 8.78% |
| 10 | 13.85% | 13.05% | 11.50% | 10.84% | 5.97% |
| 12 | 5.79% | 5.39% | 4.63% | 4.02% | 2.70% |

Read across the threshold-6 row: Hungarian sits 15–19 points above Swedish. Read down the
Hungarian column to find 25.65% and you land between 7 and 8, closest to **8** at 27.33%.

The two Hungarian sources are worth dwelling on. MOKK is a winter-2003 web crawl; Leipzig
is 2022 news, built by a different project with a different pipeline. They agree within
about three points at every threshold. The saturation is a property of the language, not an
artifact of one corpus.

## The answer

```python
>>> from saphes import recommended_threshold
>>> hu = recommended_threshold("hu")
>>> hu.threshold
8
```

Chosen by **equipercentile matching**: the Hungarian threshold whose long-word share is
closest to the share Björnsson's 6 picks out in Swedish. That preserves what the term
*means* — the longest quarter or so of running words — rather than the literal number.

Six independently computed curves all choose 8, including the two sensitivity variants:

```python
>>> sorted({t for _, t in hu.agreement})
[8]
>>> hu.is_boundary          # is the runner-up nearly as good?
False
```

`is_boundary` is worth having. On a truncated smoke sample (the 100k-most-frequent words,
covering ~95% of tokens) the 8% and full-corpus columns picked **7** instead, and the
choice really was near-arbitrary. The full list resolved it: the missing 5% is the long
tail, and including it pushed the Hungarian shares up, making 8 unanimous. A single
integer would have hidden that; the bracket and the agreement record do not.

## Using it

`lix` deliberately takes **no** `language=` parameter. Pass the threshold explicitly, so
the choice is visible at the call site:

```python
from saphes import lix, recommended_threshold

result = lix(text, long_word_threshold=int(recommended_threshold("hu")))
```

`kertben` is seven letters — long under Björnsson's Swedish threshold, ordinary under the
Hungarian one:

```python
>>> from saphes import lix
>>> text = "A kutyák megálltak a kertben és vártak."
>>> round(lix(text, sentences=1).long_word_share, 3)
0.286
>>> round(lix(text, sentences=1, long_word_threshold=8).long_word_share, 3)
0.143
```

## Does it survive contact with real text?

The calibration is built from frequency lists, which cannot supply *B*. So it was checked
against a Webcorpus crawl part, which is segmented into sentences as well as words — real
*A*, real *B*, real *C*:

| threshold | *A* | *B* | long-word share | LIX |
|---|---:|---:|---:|---:|
| Björnsson's 6 | 10,275,343 | 709,274 | 45.89% | **60.38** |
| calibrated 8 | 10,275,343 | 709,274 | 28.93% | **43.41** |

At the Swedish default, ordinary 2000s web Hungarian scores 60.4 — deep into "very
difficult". That is not a description of the text; it is the index saturating. At the
calibrated threshold it scores 43.4.

And the calibration transfers: it predicted a 27.33% long-word share, and this running
text gives 28.93% — 1.59 points apart, across the gap between a frequency list's 4%
stratum and actual running prose.

## Sensitivity

Two variants are computed alongside the main curves, so the cost of each methodological
choice is visible rather than argued.

**The capitalisation marker.** MOKK marks capitalised, mostly sentence-initial forms with
a trailing asterisk — `A*`, `Az*`, `És*`. `A*` alone is 8.9 million tokens. A naive
alphabet filter discards every starred row, and they are overwhelmingly *short* function
words, so the mean length is biased upward:

| >T | 6 | 7 | 8 | 9 |
|---|---:|---:|---:|---:|
| correct (strip and merge) | 44.52% | 35.38% | 27.33% | 19.83% |
| naive (discard starred) | 45.94% | 36.57% | 28.33% | 20.60% |

About 1.4 points across the curve. It happens not to change the answer here — but it is
invisible in the output, which is exactly why it is checked rather than assumed.

**Digraphs.** `cs, dz, gy, ly, ny, sz, ty, zs, dzs` are single *letters* in Hungarian, so
a character count is not a letter count. `saphes.calibration.hungarian_letter_count` is a
length policy that collapses them:

```python
>>> from saphes import hungarian_letter_count
>>> len("ország"), hungarian_letter_count("ország")
(6, 5)
```

Recomputing on letters lowers the curve by about three points and still chooses 8. It is a
**sensitivity check, not better ground truth**, and the function ships with a doctest of
its own failure: `község` is `köz` + `ség`, so its `zs` spans a morpheme boundary and is
not the digraph at all. Character counting stays the default, as in Björnsson's original.

## Bands stop applying

Björnsson's interpretation bands were fitted to Swedish prose at threshold 6. Changing the
threshold rescales `100·C/A` by construction, so the score is no longer on that scale.
saphes makes this structural:

```python
>>> text = "The cat sat on it. Complicated sentences generally frighten us."
>>> lix(text).band
'standard'
>>> lix(text, long_word_threshold=8).band is None
True
```

If you want a label anyway, ask for one deliberately with `interpret_lix(score)`.

## Doing this for your own language or register

A calibrated threshold is a **default, not a truth** — and it is register-specific. The
MOKK crawl is 2000s web Hungarian, not song lyrics and not literary prose. Before trusting
8 on your own texts, recompute the share on a sample of them:

```python
from collections import Counter
from saphes.calibration import length_curve, match_threshold

mine = length_curve(Counter(my_token_frequencies), label="my-corpus")
reference = length_curve(swedish_frequencies, label="swe")
match_threshold(mine, reference, reference_threshold=6)
```

Two things decide whether the answer is right:

**Token-weighted, never type-weighted.** A frequency list is a list of *types*; rare types
are long, so a mean over types runs far above the mean in running text. `length_curve`
takes a `Mapping[str, int]` and never a token list, so there is no way to call it that
forgets the weights — pass all-1 counts and you get a visibly different, wrong curve.

**Report the whole curve.** `ThresholdMatch.table` carries every threshold, so the choice
stays revisable when someone disagrees with the reference.

## Reproducing the study

```bash
uv run python experiments/lix_calibration/scripts/download_data.py --with-corpus-part
uv run python experiments/lix_calibration/scripts/run.py
uv run python experiments/lix_calibration/scripts/validate_b.py
```

The run asserts regression anchors measured before the pipeline existed, and fails rather
than quietly publishing different numbers. Outputs: `findings.md`, `validation.md`,
`results/lix_calibration.json`, and the shipped literal in
`src/saphes/datasets/_lix_calibration.py`.

## Sources

- Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). *Creating open language resources
  for Hungarian.* LREC.
- Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). *Web-based frequency dictionaries
  for medium density languages.* Web as Corpus, ACL.
- Goldhahn, Eckart, Quasthoff (2012). *Building large monolingual dictionaries at the
  Leipzig Corpora Collection.* LREC.
