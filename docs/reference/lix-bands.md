# LIX interpretation bands

Björnsson's bands, as shipped in `saphes.readability.LIX_BANDS`. Each entry is an
**exclusive** upper bound: a score of exactly 30.0 is `"easy"`, not `"very easy"`.

| Score | Band |
|---|---|
| below 30 | `very easy` |
| 30 to below 40 | `easy` |
| 40 to below 50 | `standard` |
| 50 to below 60 | `difficult` |
| 60 and above | `very difficult` |

```pycon
>>> from saphes import interpret_lix
>>> interpret_lix(29.9), interpret_lix(30.0)
('very easy', 'easy')
>>> interpret_lix(59.9), interpret_lix(60.0)
('difficult', 'very difficult')

```

## Validity

These are calibrated for **Swedish and Germanic prose at `long_word_threshold=6`**. At any
other threshold the score is not on this scale, and `LixResult.band` returns `None`:

```pycon
>>> from saphes import lix
>>> text = "The cat sat on it. Complicated sentences generally frighten us."
>>> lix(text).band
'standard'
>>> lix(text, long_word_threshold=8).band is None
True

```

`interpret_lix` itself does not refuse — it will label any float, including a negative one,
and returns `"very difficult"` for `NaN`.

## The Hungarian mapping

The bands have been carried across to the calibrated Hungarian thresholds by equipercentile
mapping — for each Swedish boundary, the Hungarian score below which the same share of running
text falls. Ask the recommendation, which knows both the threshold and the length policy:

```pycon
>>> from saphes import recommended_threshold
>>> hu = recommended_threshold("hu-letters")
>>> hu.interpret(42.11)
'standard'

```

| Swedish boundary | `hu` (characters) | `hu-letters` | supporting windows |
|---:|---:|---:|---:|
| 30 | 35.45 | 32.63 | 402 |
| 40 | 42.95 | 40.18 | 4,063 |
| 50 | 51.16 | 48.19 | 1,300 |
| 60 | *not placed* | *not placed* | 5 |

Under the letter policy the boundaries land within 2.6 points of the Swedish ones; under the
character policy they sit up to 5.5 points higher, mostly because Hungarian news writes longer
sentences (18.3 words against 15.4) and the threshold calibration only rescales the *second*
LIX term.

**The top boundary is not published.** Swedish news puts about 0.04% of its text above LIX 60,
so that boundary rests on five windows. Above the `standard` band `interpret` returns `None`
rather than guessing:

```pycon
>>> hu.interpret(50.0) is None
True

```

A score there is harder than ordinary news; whether it is `difficult` or `very difficult` is a
distinction this reference corpus cannot support.

The mapping preserves **how much text falls in each band**. It carries across no claim about
how hard Hungarian readers find those texts, because none was measured.

## Substituting your own

Published versions of this table differ in their boundaries. `LIX_BANDS` is a module-level
constant of `(exclusive upper bound, label)` pairs, exposed so it can be replaced:

```pycon
>>> from saphes.readability import LIX_BANDS
>>> LIX_BANDS[0]
(30.0, 'very easy')
>>> len(LIX_BANDS)
5

```

Rebinding it changes `interpret_lix` process-wide.

## See also

- [Why the threshold moves](../explanation/why-the-threshold-moves.md) — why re-calibrating
  invalidates the bands, and how they were earned back.
- [`interpret_lix` reference](readability.md).
- `experiments/lix_registers/` — the measurement behind the mapping.
