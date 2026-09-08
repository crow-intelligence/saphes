# Measuring syntactic complexity

You have already [taken a first measurement](first-measurement.md) with LIX. This tutorial
adds the two metrics that look at *structure* rather than *form* — how far apart the words
that belong together are, and how deep the sentence nests.

Everything here runs offline with no parser installed. You will build the parses by hand
first, precisely so you can see what the numbers are made of, and only then hand the job to
a real parser.

## What a parse is, to saphes

A parse is a sentence where every token knows which other token it depends on. saphes takes
that as four values per token:

```pycon
>>> from saphes import DepToken
>>> DepToken(2, 3, False, "PROPN")
DepToken(index=2, head=3, is_punct=False, pos='PROPN')

```

`index` is the token's 1-based position, `head` is the position of its **governor** — the
word it hangs off — and `0` means *this is the root*.

## Step 1: build one sentence

Here is the sentence Jing & Liu use in the paper that defines these measures, *"Mr. Nixon
was to leave China today ."* The analysis is `was → to → leave → {China, today}`, and
`was → Nixon → Mr.`

```pycon
>>> parse = [
...     DepToken(1, 2, False, "PROPN"),   # Mr.    -> Nixon
...     DepToken(2, 3, False, "PROPN"),   # Nixon  -> was
...     DepToken(3, 0, False, "AUX"),     # was    -> ROOT
...     DepToken(4, 3, False, "PART"),    # to     -> was
...     DepToken(5, 4, False, "VERB"),    # leave  -> to
...     DepToken(6, 5, False, "PROPN"),   # China  -> leave
...     DepToken(7, 5, False, "NOUN"),    # today  -> leave
...     DepToken(8, 3, True, "PUNCT"),    # .      -> was
... ]

```

## Step 2: look at the distances before the average

```pycon
>>> from saphes import dependency_distances
>>> dependency_distances(parse)
[1, 1, 1, 1, 1, 2]

```

Six numbers for eight tokens. The full stop is punctuation and was dropped; `was` is the
root and has no governor, so it contributes nothing. **That is why the denominator is 6.**

## Step 3: the score

```pycon
>>> from saphes import mean_dependency_distance
>>> result = mean_dependency_distance([parse])
>>> round(result.mdd, 2)
1.17

```

1.17 is the number printed in the paper. Note the argument is `[parse]` — a **list of
sentences**. Passing a bare sentence raises rather than reading it as a list of one-token
sentences.

Every count is on the result, so the arithmetic is checkable:

```pycon
>>> result.total_distance, result.pairs
(7, 6)

```

## Step 4: the vertical dimension

Dependency distance measures how far apart words are *in the string*. Hierarchical distance
measures how deep they are *in the tree*:

```pycon
>>> from saphes import hierarchical_distances, mean_hierarchical_distance
>>> hierarchical_distances(parse)
[2, 1, 1, 2, 3, 3]
>>> mean_hierarchical_distance([parse]).mhd
2.0

```

`Mr.` is two edges below the root, `China` and `today` are three. Again the root's own 0 is
excluded, so it is 12/6 and not 12/7.

The two come apart, which is why both exist:

```pycon
>>> mean_dependency_distance([parse]).mdd < mean_hierarchical_distance([parse]).mhd
True

```

This sentence is flatter than it is deep. Another with the same MDD could be the reverse.

## Step 5: use a real parser

You will not build `DepToken`s by hand in practice. `saphes.adapters` converts what a parser
gives you, and imports neither spaCy nor a CoNLL-U library:

```pycon
>>> from saphes import from_conllu
>>> conllu = (
...     "1\tA\ta\tDET\t_\t_\t2\tdet\t_\t_\n"
...     "2\tkutya\tkutya\tNOUN\t_\t_\t3\tnsubj\t_\t_\n"
...     "3\tugat\tugat\tVERB\t_\t_\t0\troot\t_\t_\n"
...     "4\t.\t.\tPUNCT\t_\t_\t3\tpunct\t_\t_\n"
... )
>>> parses = from_conllu(conllu)
>>> mean_dependency_distance(parses, parser="emtsv tok-dep-conll").mdd
1.0

```

For a spaCy or HuSpaCy `Doc`, use `from_spacy(doc)` instead. See
[how to pass a parse to saphes](../how-to/pass-a-parse-to-saphes.md).

## The one thing to carry away

Notice `parser=` in that last call. **Record it every time.**

A parser carries the annotation convention of the treebank it was trained on, and that
convention decides which word is the head — which is the entire input to a distance measure.
HuSpaCy makes the first conjunct head a coordination; emtsv makes the conjunction do it. On
one sentence of the test corpus that is the difference between MDD 1.600 and 1.500, with
every word identical.

Two MDD scores are comparable only if they came from the same convention. Nothing in the
number tells you, so the field on the result has to.

## Where next

- [What dependency distance measures](../explanation/what-dependency-distance-measures.md) —
  the cognitive argument, and Futrell's objection to the whole approach
- [How to pass a parse to saphes](../how-to/pass-a-parse-to-saphes.md) — HuSpaCy and emtsv
  recipes
- [`syntax` reference](../reference/syntax.md) — the contracts and the formulas
