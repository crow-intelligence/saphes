# Supply a sentence count

LIX needs *B*, the number of sentences. Many real pipelines cannot give you one: a treebank
that drops punctuation has no sentence boundaries left, and a spaCy pipeline loaded with
`disable=["parser"]` never computed any. This is how to supply *B* yourself.

## If you have raw text

Do nothing — saphes segments it:

```pycon
>>> from saphes import lix
>>> result = lix("The cat sat on it. Complicated sentences frighten us.")
>>> result.sentences
2
>>> result.sentence_source
'segmented'

```

## If you already have sentences

Pass them and they are counted; blank entries are dropped.

```pycon
>>> result = lix("some text", sentences=["The cat sat.", "It slept."])
>>> result.sentences
2
>>> result.sentence_source
'presegmented'

```

## If you only have a number

Pass the integer. This is the path for treebanks and parser-less pipelines.

```pycon
>>> result = lix(["Complicated", "sentences", "frighten", "us"], sentences=1)
>>> result.sentences
1
>>> result.sentence_source
'explicit'

```

## If you have neither

Passing tokens without `sentences` is refused rather than guessed:

```pycon
>>> lix(["some", "tokens"])
Traceback (most recent call last):
    ...
TypeError: lix() got tokens but no sentences. The number of sentences (B) cannot be recovered from a token list — pass sentences= as a count, or as the list of sentence strings, or pass raw text so saphes can segment it.

```

## Choosing what counts as a sentence

For a verse corpus, the line is usually the unit:

```pycon
>>> lines = ["μῆνιν ἄειδε θεά", "οὐλομένην ἣ μυρί Ἀχαιοῖς ἄλγε ἔθηκε"]
>>> tokens = [word for line in lines for word in line.split()]
>>> lix(tokens, sentences=len(lines)).sentences
2

```

That is comparable *within* the corpus but not against prose, because a verse line is not a
sentence. Whichever you choose, `sentence_source` on the result records the route, so the
decision travels with the number.

## Watch out for

`sentences=True` is rejected. `bool` is a subclass of `int`, so it would otherwise be read as
*B*=1:

```pycon
>>> lix("some text here", sentences=True)
Traceback (most recent call last):
    ...
TypeError: sentences must be a count or a sequence of sentences, got True

```

A bare string is rejected too, since it would count as one sentence per character:

```pycon
>>> lix("some text here", sentences="One sentence.")
Traceback (most recent call last):
    ...
TypeError: sentences got a single string, which is ambiguous. Pass a count, or a list of sentence strings such as ['One.', 'Two.'].

```

## Related

- [Plug in a sentence splitter](plug-in-a-sentence-splitter.md) — if you want to segment, but
  differently.
- [Why implementations disagree](../explanation/why-implementations-disagree.md) — why *B* is
  where LIX implementations part company.
