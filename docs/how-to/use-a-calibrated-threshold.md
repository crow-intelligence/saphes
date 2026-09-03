# Use a calibrated threshold

saphes ships empirically calibrated long-word thresholds for Hungarian. This is how to use
them.

There are two keys, because a threshold is calibrated against a way of counting letters:

| Key | Counts letters with | Use when |
|---|---|---|
| `hu` | the default character count | you pass no `length_policy` |
| `hu-letters` | `hungarian_letter_count` | you count Hungarian letters |

Both come out at 8. What differs is the share of running words behind that 8 — 27.3% against
24.4% — so pairing a threshold with the wrong policy measures something the study never
measured.

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
KeyError: "no calibration for 'grc'; calibrated languages: hu, hu-letters"

```

To produce one, see [Calibrate a new language](calibrate-a-new-language.md).

## With the Hungarian letter count

If you count letters rather than characters, take the threshold calibrated for that policy
and pass both together:

```pycon
>>> from saphes import hungarian_letter_count
>>> letters = recommended_threshold("hu-letters")
>>> result = lix(text, sentences=1,
...              length_policy=hungarian_letter_count,
...              long_word_threshold=int(letters))
>>> result.long_word_threshold, result.length_policy
(8, 'custom:hungarian_letter_count')

```

Both choices are recorded on the result, so a table of scores says how its lengths were
counted as well as where the boundary was. See
[Count letters rather than characters](count-letters-not-characters.md).

## Note on bands

`LixResult.band` returns `None` at any threshold other than 6, so a calibrated result has no
label:

```pycon
>>> result.band is None
True

```

Ask the recommendation instead. It knows the threshold and the length policy, so it can apply
the bands that were mapped for that combination:

```pycon
>>> hu.interpret(result.score)
'very easy'

```

Do not reach for `interpret_lix(result.score)`: that applies Björnsson's Swedish boundaries to
a score that is not on his scale.

Above the `standard` band the mapping returns `None` rather than guessing, because the Swedish
reference has too little hard text to place the top boundary. See
[LIX bands](../reference/lix-bands.md).
