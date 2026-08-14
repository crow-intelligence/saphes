# Use a calibrated threshold

saphes ships one empirically calibrated long-word threshold, for Hungarian. This is how to
use it.

## Look it up

```pycon
>>> from saphes import recommended_threshold
>>> hu = recommended_threshold("hu")
>>> hu.threshold
8

```

## Pass it to `lix`

`lix` takes no `language=` parameter. Pass the number, so the choice is visible where the
measurement happens:

```pycon
>>> from saphes import lix
>>> text = "A kutyák megálltak a kertben és vártak."
>>> result = lix(text, sentences=1, long_word_threshold=int(hu))
>>> result.long_word_threshold
8

```

`int(hu)` works because the recommendation coerces to its threshold. Use `hu.threshold` if
you prefer to be explicit.

## Check what you are relying on

The recommendation carries its own provenance:

```pycon
>>> round(hu.matched_share, 3), round(hu.reference_share, 3)
(0.273, 0.257)
>>> hu.reference_id
'leipzig-swe_news_2022_1M'
>>> sorted({t for _, t in hu.agreement})
[8]
>>> hu.is_boundary
False

```

`agreement` lists what every independently computed curve chose; `is_boundary` is `False`
when the runner-up is clearly worse. Unanimous and uncontested is why 8 ships.

## Read the caveats before trusting it

```pycon
>>> len(hu.caveats)
3
>>> print(hu.caveats[1])
Register matters for readability. Before trusting this threshold on your own texts, recompute the long-word share on a sample of them and check it lands where the calibration predicts.

```

That second one is the operative instruction: see
[Calibrate a new language](calibrate-a-new-language.md), which works for a new *register* as
much as a new language.

## For an uncalibrated language

It raises rather than falling back to 6, which would be silently wrong for exactly the
languages this matters for:

```pycon
>>> recommended_threshold("grc")
Traceback (most recent call last):
    ...
KeyError: "no calibration for 'grc'; calibrated languages: hu"

```

To produce one, see [Calibrate a new language](calibrate-a-new-language.md).

## Note on bands

`LixResult.band` returns `None` at any threshold other than 6, so a calibrated result has no
label:

```pycon
>>> result.band is None
True

```

If you want one anyway, ask for it deliberately with `interpret_lix(result.score)` — and
read [Why the threshold moves](../explanation/why-the-threshold-moves.md) first, because the
label will be on the wrong scale.
