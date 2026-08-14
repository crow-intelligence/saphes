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
  invalidates the bands.
- [`interpret_lix` reference](readability.md).
