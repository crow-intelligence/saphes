# Diagnose a surprising result

Symptom-first recipes. If saphes raised, find the message below; if it returned a number you
did not expect, start at the bottom.

## `TypeError: missing 1 required keyword-only argument: 'unit'`

`lexical_diversity` will not guess what your tokens are. Say so:

```pycon
>>> from saphes import lexical_diversity
>>> lexical_diversity(["ház", "kutya"], unit="lemma").ttr
1.0

```

Use `unit="lemma"` if they are lemmas, `unit="surface"` if they are words as written. The
choice changes the answer, which is why it has no default.

## `TypeError: ... got a raw string with unit='lemma'`

A string can only be split into surface forms. Either declare that:

```pycon
>>> lexical_diversity("ház házak házban", unit="surface").tokens
3

```

or lemmatise upstream — with huspacy, CLTK, emtsv or a treebank — and pass the result.

## `TypeError: lix() got tokens but no sentences`

*B* cannot be recovered from a bag of tokens. See
[Supply a sentence count](supply-a-sentence-count.md).

## `TypeError: '>' not supported between instances of 'str' and 'int'`

Your custom `length_policy` returned something that is not an int. See
[Count letters rather than characters](count-letters-not-characters.md).

## `ZeroDivisionError` or `IndexError` from `mattr`

`window` was zero or negative. The bare `mattr` does not validate it; `lexical_diversity`
does:

```pycon
>>> lexical_diversity(["a", "b"], unit="lemma", window=0)
Traceback (most recent call last):
    ...
ValueError: window must be positive, got 0

```

## `KeyError: "no calibration for ..."`

That language has no shipped threshold. Pass one explicitly, or produce it with
[Calibrate a new language](calibrate-a-new-language.md).

## `LookupError` about a missing NLTK resource

The Punkt model is absent and the download did not produce it. Check connectivity — a failed
download is silent and surfaces as this. Or drop `punkt=True` and use the bundled splitter.

## The score is much higher than expected

Check the threshold and the language. At the Swedish default of 6, agglutinative and heavily
inflected languages saturate — 44.5% of running Hungarian tokens are "long" against 25.7% in
Swedish, so the second term sits near its ceiling for everything:

```pycon
>>> from saphes import lix
>>> hu = "A gyermekeknek megmutatták a településeken található nevezetességeket. Elutaztak."
>>> round(lix(hu).long_word_share, 2)
0.75
>>> round(lix(hu, long_word_threshold=9).long_word_share, 2)
0.5

```

See [Use a calibrated threshold](use-a-calibrated-threshold.md).

## Every text scores about the same

Same cause as above — the index has saturated and stopped discriminating. Raise the
threshold.

## `band` is `None`

Expected at any threshold other than 6. Björnsson's bands were fitted there, so saphes will
not label a score that is no longer on that scale. `interpret_lix(score)` gives you one
anyway if you want it.

## The number changed after I normalised my text differently

`length_policy` defaults to `"nfc"` so that it should not. If you passed
`length_policy="codepoints"`, decomposed input inflates every word by two or three
characters:

```pycon
>>> import unicodedata
>>> from saphes import word_length
>>> nfd = unicodedata.normalize("NFD", "ἐϋκνήμιδες")
>>> word_length(nfd), word_length(nfd, policy="codepoints")
(10, 13)

```

## The diversity number looks too high

You may be measuring surface forms rather than lemmas. Check what the result says it did:

```pycon
>>> lexical_diversity(["ház", "házak"], unit="surface").unit
'surface'

```

See [Why the two metrics need opposite token streams](../explanation/two-token-streams.md).

## MATTR differs between runs

You passed a set, or something else unordered. MATTR reads windows in sequence, so order is
part of the input. Pass a list or tuple in document order — see
[Compare texts of different lengths](compare-different-lengths.md).
