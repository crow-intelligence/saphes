# Quickstart

## Install

```bash
uv add saphes
```

The core has no dependencies. NLTK's Punkt splitter is available behind an extra:

```bash
uv add 'saphes[punkt]'
```

## Readability

`lix` takes **surface forms** — raw text, or an already-tokenised sequence.

```python
from saphes import lix

result = lix("The cat sat on it. Complicated sentences generally frighten us.")

result.score        # 45.0
result.words        # 10  -> A
result.sentences    # 2   -> B
result.long_words   # 4   -> C
result.band         # 'standard'
```

The formula is `LIX = A/B + (C * 100)/A`. A **long word is longer than the threshold**, so
the default `long_word_threshold=6` counts words of **seven letters or more** — per
Björnsson's "more than six letters". That off-by-one is a known source of disagreement
between implementations, so saphes states it and tests it.

```python
lix(text, long_word_threshold=9)   # for Hungarian, Ancient Greek, Finnish...
```

## Supplying the sentence count

`B` has three sources. Which one you used is recorded on the result.

```python
lix(text)                                  # segmented with the bundled splitter
lix(text, sentencer=my_splitter)           # segmented with yours
lix(text, sentences=["One.", "Two."])      # pre-split
lix(tokens, sentences=24)                  # explicit count
```

The last form is not a corner case. A treebank that drops punctuation, or a spaCy pipeline
loaded with `disable=["parser"]`, cannot give you sentences at all.

```python
lix(tokens)   # TypeError: B cannot be recovered from a token list
```

## Lexical diversity

`lexical_diversity` takes **lemmas**, and `unit` is required — it has no default.

```python
from saphes import lexical_diversity

lexical_diversity(lemmas, unit="lemma")
lexical_diversity(tokens, unit="surface")   # allowed, but you must ask for it
lexical_diversity(lemmas)                   # TypeError: unit is required
```

!!! warning "TTR is not comparable across texts of different lengths"

    TTR falls as a text grows, so a raw TTR over corpora of different sizes mostly ranks
    them by size. For per-decade or per-book work — where lengths always differ — use
    MATTR instead.

```python
result = lexical_diversity(lemmas, unit="lemma", window=100)
result.mattr    # length-robust; comparable across corpora
result.ttr      # still there, still length-sensitive
```

`mattr` is also available as a bare function, for drop-in use:

```python
from saphes import mattr
mattr(tokens, window=100)   # -> float
```

## Word length and Unicode

Decomposed Unicode inflates every word length, which hits polytonic Greek and accented
Hungarian hardest — and would roughly double a LIX score with no error at all. So length is
normalised by default:

```python
from saphes import word_length

word_length("ἐϋκνήμιδες")                        # 10
word_length(nfd_text, policy="codepoints")       # 13 — raw, unnormalised
word_length("ország", policy=lambda w: len(w) - w.count("sz"))   # 5 — orthographic letters
```

Length is normalised; identity is not. saphes will never alter a token to count types —
the one opt-in is `case_fold=True`, which as a side effect merges Greek final sigma `ς`
with `σ`.
