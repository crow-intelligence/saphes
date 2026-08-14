# Plug in a sentence splitter

The bundled splitter is a regex that guards common abbreviations. If you need a different
one — because you have a real segmenter, or because your text has structure the regex cannot
see — pass it as `sentencer`.

## The contract

A sentencer takes one string and returns an iterable of strings. Blank entries are dropped
before counting.

```pycon
>>> from saphes import lix
>>> def by_line(text: str) -> list[str]:
...     return [line for line in text.splitlines() if line.strip()]
>>> result = lix("one two three\nfour five six", sentencer=by_line)
>>> result.sentences
2
>>> result.sentencer
'by_line'

```

The name is recorded on the result, so the number says how it was segmented.

## Use NLTK Punkt instead

Install the extra, then:

```python
from saphes import lix, segment

result = lix(text, sentencer=lambda t: segment.sentences(t, punkt=True))
```

The model downloads on first use.

## Use spaCy

```python
import spacy

nlp = spacy.load("en_core_web_sm")

def spacy_sentences(text: str) -> list[str]:
    return [s.text for s in nlp(text).sents]

result = lix(text, sentencer=spacy_sentences)
```

If your pipeline has the parser disabled, this will not work — you have no sentence
boundaries, so use [Supply a sentence count](supply-a-sentence-count.md) instead.

## Watch out for

**A failed Punkt download looks like a missing model.** `nltk.download` runs quietly and its
result is discarded, so a network failure surfaces later as a `LookupError` from
`sent_tokenize` about a missing resource. If you see that, check connectivity before you
check your install.

**The bundled splitter suppresses boundaries silently.** It skips a candidate boundary after
a known abbreviation, after a single capital letter it reads as an initial, and before a
lowercase letter it reads as dialogue attribution. Each is a heuristic that can be wrong, and
none of them tells you:

```pycon
>>> from saphes import sentences
>>> sentences("I work at Acme Inc. They pay well.")
['I work at Acme Inc. They pay well.']
>>> sentences("He left. she stayed.")
['He left. she stayed.']

```

Both should be two sentences. The first ends on `Inc`, which is on the abbreviation list; the
second is followed by a lowercase letter, which the splitter reads as dialogue attribution.
Each returns *B*=1 instead of 2, which inflates the first LIX term by a factor of two, and
nothing signals it.

If *B* matters to you, either supply it directly or use a segmenter suited to your text.

## Related

- [Supply a sentence count](supply-a-sentence-count.md) — when you cannot segment at all.
- [Why implementations disagree](../explanation/why-implementations-disagree.md) — why this
  is the choice that makes LIX scores differ between libraries.
