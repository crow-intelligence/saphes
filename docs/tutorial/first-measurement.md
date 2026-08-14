# Your first measurement

In this lesson you will measure a piece of text twice — once for how hard it is to read, once
for how varied its vocabulary is — and see why saphes insists those two measurements are fed
different things.

You need Python 3.11 or newer and about ten minutes. Everything runs offline: the samples are
bundled with the package, so nothing is downloaded and no result depends on your machine.

## 1. Install saphes

```bash
uv add saphes
```

The core has no dependencies, so this is quick.

## 2. Load a sample

saphes ships a few short annotated texts. Start an interactive Python session and load the
English one:

```pycon
>>> from saphes.datasets import load_english
>>> sample = load_english()
>>> sample.text
'The cat sat on it. Complicated sentences generally frighten us. The cats sat on the mats, and the sitting cat watched.'

```

## 3. Measure how hard it is to read

```pycon
>>> from saphes import lix
>>> result = lix(sample.text)
>>> result.score
35.57142857142857

```

That number is LIX. Now look at what produced it:

```pycon
>>> result.words
21
>>> result.sentences
3
>>> result.long_words
6

```

Those three counts are the whole formula. LIX is the average sentence length plus the
percentage of long words:

```pycon
>>> result.avg_sentence_length
7.0
>>> result.long_word_share
0.2857142857142857

```

Add them — 7.0 plus 28.57 — and you have 35.57. Every saphes result carries the numbers
it was built from, so you can always check it by hand.

## 4. Find out what "long" means

A long word is one *longer than* the threshold, which defaults to six. So six means seven
letters or more:

```pycon
>>> result.long_word_threshold
6

```

Change it and watch the score move:

```pycon
>>> lix(sample.text, long_word_threshold=9).score
11.761904761904763

```

Far fewer words are now long, so the second term shrinks. Nothing about the text changed —
only what you asked to count.

## 5. Notice that the label disappears

Your first result came with a plain-language band:

```pycon
>>> result.band
'easy'

```

Ask for the band on the re-measured text and you get nothing:

```pycon
>>> lix(sample.text, long_word_threshold=9).band is None
True

```

That is deliberate. The bands were fitted to Swedish at threshold six; once you move the
threshold the score is no longer on that scale, so saphes declines to label it.

## 6. Measure vocabulary variety

Now the other metric. This one needs a *lemma* — the dictionary form of a word — for every
token. The sample carries them already:

```pycon
>>> sample.lemmas[:6]
['the', 'cat', 'sit', 'on', 'it', 'complicated']

```

Compare that with the words as they actually appear:

```pycon
>>> sample.forms[:6]
['The', 'cat', 'sat', 'on', 'it', 'Complicated']

```

`sat` became `sit`. Now measure:

```pycon
>>> from saphes import lexical_diversity
>>> diversity = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True)
>>> diversity.ttr
0.6190476190476191

```

Roughly 62% of the tokens are distinct. `unit="lemma"` is not optional — try leaving it out:

```pycon
>>> lexical_diversity(sample.lemmas)
Traceback (most recent call last):
    ...
TypeError: lexical_diversity() missing 1 required keyword-only argument: 'unit'

```

## 7. See why the two metrics need different input

Measure diversity again, this time on the words as they appear rather than their lemmas:

```pycon
>>> surface = lexical_diversity(sample.forms, unit="surface", case_fold=True)
>>> surface.ttr
0.7142857142857143

```

Higher — 71% against 62%. But the vocabulary did not get richer. `sat`, `sitting` and `sits`
are one word wearing three coats, and counting them separately measures grammar, not
vocabulary.

```pycon
>>> round(surface.ttr - diversity.ttr, 4)
0.0952

```

That gap is the morphology the lemmas removed. In English it is small. In Hungarian it is
not:

```pycon
>>> from saphes.datasets import load_hungarian
>>> hu = load_hungarian()
>>> hu_surface = lexical_diversity(hu.forms, unit="surface", case_fold=True)
>>> hu_lemma = lexical_diversity(hu.lemmas, unit="lemma", case_fold=True)
>>> round(hu_surface.ttr - hu_lemma.ttr, 4)
0.1429

```

The same mistake costs half as much again.

Now run the reverse mistake — readability on lemmas instead of on the words as written:

```pycon
>>> lix(hu.forms, sentences=3).score
26.095238095238095
>>> lix(hu.lemmas, sentences=3).score
4.666666666666667

```

The second number is not an error. It is what happens when you measure word length after
throwing the word endings away. Nothing warned you, because nothing could: both numbers are
perfectly plausible.

## 8. Read the record

Every result knows what it measured:

```pycon
>>> result.unit
'surface'
>>> diversity.unit
'lemma'

```

So a table of scores written months ago can still be interpreted, because each row says which
stream produced it.

## What you have learned

- LIX comes from three counts, and saphes always hands them back with the score.
- The long-word threshold is a parameter, and the interpretation band is only valid at its
  default.
- Diversity is measured on lemmas; readability is measured on the words as written.
- Feeding either one the wrong stream produces no error — only a wrong number.

## Where to go next

- [Why the two metrics need opposite token streams](../explanation/two-token-streams.md) —
  the reasoning behind step 7, and the four guards that make the mistake loud.
- [Compare texts of different lengths](../how-to/compare-different-lengths.md) — the TTR you
  computed above is not comparable between texts of different sizes. This is how to fix that.
- [Supply a sentence count](../how-to/supply-a-sentence-count.md) — for the common case where
  your pipeline has no sentence boundaries at all.
