# The two contracts

The single most important thing in this package: **the two metrics require opposite token
streams.**

| Metric | Required input | Why |
|---|---|---|
| `lexical_diversity` | **lemmas** | Surface variation is *noise* — it measures morphology, not vocabulary. |
| `lix` | **surface forms** | Word length *is* the signal, and lemmatising erases it. |

Feed the same list to both and exactly one of them is silently wrong. No error, no NaN,
just a plausible number.

## Why diversity needs lemmas

Hungarian `ház / házak / házban / házakat` is four surface types and one lemma.

```python
>>> from saphes import lexical_diversity
>>> lexical_diversity(["ház", "házak", "házban", "házakat"], unit="surface").ttr
1.0
>>> lexical_diversity(["ház"] * 4, unit="lemma").ttr
0.25
```

The surface number is not four times richer vocabulary. It is one word, inflected four
ways. An un-lemmatised TTR reports inflectional richness as lexical richness — and inflates
most for exactly the languages this package was built for.

## Why readability needs surface forms

`házakban` is 8 characters. Its lemma `ház` is 3. LIX counts long words, so lemmatising
first destroys the measurement:

```python
>>> from saphes import lix
>>> lix(["házakban", "őrült", "űrhajósok"], sentences=1).long_words
2
>>> lix(["ház", "őrült", "űrhajós"], sentences=1).long_words
1
```

Again: worst in the agglutinative languages the threshold parameter exists to serve.

## How large is the mistake?

Run `examples/two_contracts.py`. On the bundled samples, computing each metric on the wrong
stream costs:

| language | TTR error | LIX error | mean word length, surface vs lemma |
|---|---:|---:|---|
| English | +0.0952 | +9.52 | 4.48 vs 4.05 |
| Hungarian | +0.1429 | +21.43 | 4.36 vs 3.00 |
| Ancient Greek | +0.0682 | +9.09 | 5.02 vs 4.75 |

The error scales with the morphology of the language. These samples are tiny; on a real
corpus the Hungarian LIX gap is the difference between a usable measurement and a
meaningless one.

## What stops you

Four guards, none of them heuristic. saphes never tries to *detect* whether a stream looks
lemmatised — a package whose thesis is auditability should not guess.

**1. `unit` is required and has no default.**

```python
>>> lexical_diversity(["a", "b"])
Traceback (most recent call last):
    ...
TypeError: lexical_diversity() missing 1 required keyword-only argument: 'unit'
```

This catches the highest-probability accident — pasting a `lix(...)` call and changing the
function name — because a `lix` call never carries `unit=`.

**2. The parameter names differ.** `lix(words=...)` and `lexical_diversity(lemmas=...)`.
Crossing them raises `TypeError` immediately.

**3. A raw string is refused where it could only be wrong.**

```python
>>> lexical_diversity("ház házak házban", unit="lemma")
Traceback (most recent call last):
    ...
TypeError: lexical_diversity() got a raw string with unit='lemma'. ...
```

A string can only be split into surface forms. Pass `unit="surface"` if that is genuinely
what you want.

**4. Every result records its unit.** So any serialised table says which stream produced
each number, long after the code that made it is gone.

```python
>>> lix("some text here now").unit
'surface'
>>> lexical_diversity(["a"], unit="lemma").unit
'lemma'
```

## The regression guard

`tests/test_contracts.py` asserts the asymmetry survives refactoring, with a pinned floor
rather than a bare `>`:

```python
assert surface_ttr - lemma_ttr >= 0.05
```

A refactor that wired both metrics to one token stream would produce a gap of exactly
0.0 — and a bare `>` would be the only thing standing between that and a green suite.

It is also proved as a property, not just sampled. Lemmatisation is a function on tokens,
so it can only merge types, never split them. With the token count held equal, the lemma
stream can never have more types than the surface stream, and therefore never the higher
TTR:

```python
@given(inflected_pairs())
def test_lemma_ttr_never_exceeds_surface_ttr(self, pairs):
    ...
    assert lemma <= surface + 1e-12
```

`<=`, not `<`: every suffix in a draw may have come out empty.

## saphes does not lemmatise

Lemmatisation is language-specific and heavy — CLTK or a treebank for Greek, huspacy for
Hungarian, emtsv for other Hungarian pipelines. Bundling one would wreck a deliberately
tiny package and duplicate work already done upstream.

The caller lemmatises. saphes measures, and records what it was given.
