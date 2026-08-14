# Match another implementation's LIX

If your saphes score differs from `textstat`, an online calculator, or a published figure,
the cause is almost always the sentence count. This is how to reconcile them.

## Reproduce a textstat number exactly

Give saphes textstat's own sentence count:

```python
import textstat
from saphes import lix

assert lix(text, sentences=textstat.sentence_count(text)).score == textstat.lix(text)
```

That equality holds exactly, and is asserted as a test in the saphes suite. The word count
and the long-word count already agree; only *B* differs.

## Find out where they diverge

Compare the three counts side by side:

```python
import textstat
from saphes import lix

ours = lix(text)
print(f"A  saphes {ours.words:>4}   textstat {textstat.lexicon_count(text):>4}")
print(f"B  saphes {ours.sentences:>4}   textstat {textstat.sentence_count(text):>4}")
print(f"C  saphes {ours.long_words:>4}")
```

If *B* differs and *A* does not, you have found it.

## Reproduce a published figure

Published LIX numbers rarely come with their counts, so you usually cannot. What you can do
is bracket it — try both the sentence count you would compute and the one the source implies:

```pycon
>>> from saphes import lix_from_counts
>>> lix_from_counts(words=1000, sentences=50, long_words=250)
45.0
>>> lix_from_counts(words=1000, sentences=40, long_words=250)
50.0

```

Five points of difference from the sentence count alone. If a source gives *A*, *B* and *C*,
`lix_from_counts` will reproduce its score exactly; if it gives only the score, treat any
match as provisional.

## Check the threshold

A source using a non-default threshold will not match at all. LIX is only comparable between
texts measured the same way:

```pycon
>>> from saphes import lix
>>> text = "The cat sat on it. Complicated sentences generally frighten us."
>>> lix(text).score
45.0
>>> lix(text, long_word_threshold=8).score
35.0

```

## Related

- [Why implementations disagree](../explanation/why-implementations-disagree.md) — what
  textstat actually does differently, and why neither is wrong.
- [Supply a sentence count](supply-a-sentence-count.md) — the mechanics of controlling *B*.
