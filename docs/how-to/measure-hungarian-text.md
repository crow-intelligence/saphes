# Measure Hungarian text

Hungarian needs three things that English does not: a retuned long-word threshold, a letter
count that knows `sz` is one letter, and something to stand in for a lemmatiser. This is the
whole recipe in one place.

If you want to know *why* any of it is necessary, read
[Why the threshold moves](../explanation/why-the-threshold-moves.md) — this page only tells
you what to type.

## Install

```bash
uv add 'saphes[snowball]'
```

The stemmer is only needed for the diversity half. Readability works on the bare install.

## Readability

Count letters rather than characters, and take the threshold calibrated for that policy:

```pycon
>>> from saphes import hungarian_letter_count, lix, recommended_threshold
>>> hu = recommended_threshold("hu-letters")
>>> text = ("A gyermekek a településeken található nevezetességeket látogatták meg. "
...         "A gyermekeknek a településekről és a nevezetességekről is beszéltek.")
>>> result = lix(text,
...              length_policy=hungarian_letter_count,
...              long_word_threshold=int(hu))
>>> result.words, result.sentences, result.long_words
(17, 2, 7)
>>> round(result.score, 2)
49.68

```

At Björnsson's Swedish default the same text scores far higher, because the second term
saturates — most Hungarian words are longer than six letters:

```pycon
>>> round(lix(text).score, 2)
61.44

```

### Reading the score

The recommendation also carries the interpretation bands, mapped for this threshold and this
length policy. Ordinary Hungarian news measures 42.11 on this scale:

```pycon
>>> hu.interpret(42.11)
'standard'

```

Above the `standard` band it returns `None` instead of guessing — the Swedish reference corpus
has too little hard text to place the top boundary, and the sample above is in that range:

```pycon
>>> hu.interpret(result.score) is None
True

```

So this text is harder than ordinary news, and how much harder is not something the study can
say. See [LIX bands](../reference/lix-bands.md#the-hungarian-mapping).

## Diversity

Diversity wants lemmas. If you have a lemmatiser — huspacy, emtsv, a treebank — use it and
pass `unit="lemma"`. If you do not, stem:

```pycon
>>> from saphes import hungarian_stems, lexical_diversity, words
>>> tokens = words(text)
>>> stems = hungarian_stems(tokens)
>>> result = lexical_diversity(stems, unit="stem")
>>> result.types, result.tokens, round(result.ttr, 3)
(10, 17, 0.588)

```

The un-stemmed stream scores higher, and the difference is morphology rather than vocabulary:

```pycon
>>> round(lexical_diversity(tokens, unit="surface", case_fold=True).ttr, 3)
0.765

```

For texts of different lengths, pass `window=` and compare MATTR instead — see
[Compare texts of different lengths](compare-different-lengths.md).

## Watch out for

**Do not cross the streams.** `lix` gets surface forms, `lexical_diversity` gets stems or
lemmas. Both accept the wrong stream without complaint and return a plausible wrong number.

**Pair the threshold with the policy.** `hu` is calibrated for the default character count,
`hu-letters` for `hungarian_letter_count`. Both are 8, but the share of running words behind
that 8 differs, so mixing them measures something the study never measured.

**A compound outside the boundary table counts one letter short.** Silently. See
[Count letters rather than characters](count-letters-not-characters.md#watch-out-for).

**A stem is not a lemma.** Stem-based numbers are comparable only to other stem-based numbers
from the same stemmer version — see
[Stemming is not lemmatisation](../explanation/stemming-is-not-lemmatisation.md).

**`LixResult.band` is still `None`.** It returns a label only at Björnsson's 6. Use
`recommendation.interpret(score)`, which knows the threshold and the policy the bands were
mapped for.

## Related

- [Count letters rather than characters](count-letters-not-characters.md)
- [Stem when you have no lemmatiser](stem-without-a-lemmatiser.md)
- [Use a calibrated threshold](use-a-calibrated-threshold.md)
- [Supply a sentence count](supply-a-sentence-count.md) — when your corpus already knows *B*.
