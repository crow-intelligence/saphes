# Stem when you have no lemmatiser

`lexical_diversity` wants lemmas, and saphes cannot produce them. If installing huspacy or
CLTK is not an option, a Snowball stemmer removes most of the inflectional noise for the
price of one small pure-Python dependency and no model download.

Read [Stemming is not lemmatisation](../explanation/stemming-is-not-lemmatisation.md) before
you report a number from this.

## Install the extra

```bash
uv add 'saphes[snowball]'
```

## Stem, then measure

```pycon
>>> from saphes import hungarian_stems, lexical_diversity, words
>>> text = "A ház nagy. A házban lakunk. A házak régiek."
>>> tokens = words(text)
>>> stems = hungarian_stems(tokens)
>>> stems
['a', 'ház', 'nagy', 'a', 'ház', 'lak', 'a', 'ház', 'régi']

```

Pass `unit="stem"` so the result says what it measured:

```pycon
>>> result = lexical_diversity(stems, unit="stem")
>>> result.ttr, result.types, result.tokens, result.unit
(0.5555555555555556, 5, 9, 'stem')

```

The un-stemmed stream scores higher, and the gap is the morphology the stemmer removed:

```pycon
>>> lexical_diversity(tokens, unit="surface", case_fold=True).ttr
0.7777777777777778

```

## Watch out for

**A raw string is refused.** A string is a sequence of characters, so stemming one would
return a stem per letter and no error:

```pycon
>>> hungarian_stems(text)
Traceback (most recent call last):
    ...
TypeError: hungarian_stems() got a raw string....

```

**Tokens are case-folded by default.** The algorithm is defined on lowercase input and
silently under-stems anything else:

```pycon
>>> hungarian_stems(["HÁZBAN"], case_fold=False)
['HÁZBAN']

```

**Do not pass stems as `unit="lemma"`.** The units are not interchangeable, and the whole
point of the required `unit=` is that a serialised table can say which produced each number.

## Related

- [Stemming is not lemmatisation](../explanation/stemming-is-not-lemmatisation.md) — why the
  two results do not belong in the same column.
- [`saphes.stem` reference](../reference/stem.md) — the full contract.
- [Diagnose a surprising result](diagnose-a-surprising-result.md).
