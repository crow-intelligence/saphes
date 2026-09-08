# What dependency distance measures

LIX asks how long the words are. Mean dependency distance asks how far apart the words
that belong together are. It is a claim about working memory, not about vocabulary, and
it is the first metric in saphes that cannot be computed from a token stream at all.

## The idea

When you hear *the report the committee commissioned last spring is late*, you must hold
*report* open across seven words before *is* arrives to discharge it. Gibson's
dependency-locality theory makes that concrete: storage and integration cost rise with
the distance between a word and the word it depends on. Liu (2008) turned it into a
single number by averaging those distances over a sentence, and Jing & Liu (2015) give
the formulation saphes implements.

The metric is deliberately crude. It counts positions, not structures; it knows nothing
about what kind of dependency an arc is, and treats a determiner three words from its
noun exactly like a subject three words from its verb. What it buys for that crudeness
is comparability: any treebank in any language yields the number, which is why it has
been used across dozens of languages where no shared readability formula exists.

## Three conventions that are easy to get wrong

Almost every disagreement between MDD implementations comes from one of three places,
and none of them announces itself — each produces a plausible number.

**The root is excluded.** It has no governor, so it contributes no distance. Crucially
it also leaves the denominator: Jing & Liu's *n* is "the total number of dependency
**pairs**", so a seven-word sentence has six. Dividing by seven instead is a quiet
systematic deflation of every score you publish.

**Punctuation is removed before distances are measured.** That means the surviving
tokens are renumbered. Filtering the punctuation out of a list of already-computed
distances is a different operation, because it leaves the commas occupying positions and
inflates every arc that spans one. saphes calls the first `punctuation="collapse"` and
the second `punctuation="ignore"`, defaults to the first, and will show you the gap:

```pycon
>>> from saphes import DepToken, dependency_distances
>>> clause = [
...     DepToken(1, 3, False, "PRON"),
...     DepToken(2, 1, True, "PUNCT"),
...     DepToken(3, 0, False, "VERB"),
... ]
>>> dependency_distances(clause, punctuation="collapse")
[1]
>>> dependency_distances(clause, punctuation="ignore")
[2]

```

Only `collapse` has support in the literature. `ignore` exists so that a disagreement
with another tool can be diagnosed rather than argued about.

**Adjacent words are at distance 1, not 0.** Hudson's original phrasing — "measured in
terms of intervening words" — suggests 0, and Jing & Liu quote it, but their own
arithmetic uses the difference of positions. Futrell et al. (2015) state the operational
rule without ambiguity: the number of words between head and dependent, *including the
dependent*.

## A text is not a long sentence

Once you move from one sentence to a corpus there is a second fork, and it is the one
most likely to be taken by accident. Jing & Liu's equations (3) and (4) average the
per-sentence means — every sentence counts once, however long it is. Pooling all the
arcs in the text and dividing once instead lets long sentences dominate. Both are
defensible; they are simply different quantities:

```pycon
>>> from saphes import mean_dependency_distance
>>> short = [DepToken(1, 2, False, "DET"), DepToken(2, 0, False, "NOUN")]
>>> longer = [
...     DepToken(1, 4, False, "DET"),
...     DepToken(2, 4, False, "ADJ"),
...     DepToken(3, 4, False, "ADJ"),
...     DepToken(4, 5, False, "NOUN"),
...     DepToken(5, 0, False, "VERB"),
...     DepToken(6, 9, False, "ADP"),
...     DepToken(7, 9, False, "DET"),
...     DepToken(8, 9, False, "ADJ"),
...     DepToken(9, 5, False, "NOUN"),
...     DepToken(10, 5, True, "PUNCT"),
... ]
>>> mean_dependency_distance([short, longer]).mdd
1.5625
>>> mean_dependency_distance([short, longer], aggregation="micro").mdd
2.0

```

Writing a single number without saying which one you computed is how two honest
analyses of the same corpus come to disagree by a quarter of a point. The choice is
recorded on the result for exactly that reason.

## The strongest objection

Futrell, Mahowald & Gibson (2015) — the largest study of dependency length there is —
decline to use a mean at all. They sum the dependency lengths of a sentence and model
how that sum grows with sentence length, on the grounds that "summary measures that are
not a function of length fall prey to inaccuracy due to mixing dependencies of different
lengths". Their objection is real: MDD compresses a length-dependent distribution into
its first moment, and two corpora with different sentence-length profiles can produce
the same MDD for different reasons.

saphes implements MDD anyway, because it is what the Hungarian and Chinese quantitative
literature uses and because comparability with that literature is worth something. But
the objection is why `dependency_distances` is public. If you want the distribution
rather than its mean, take it; the mean is a convenience, not the measurement.

## Why this needs a parse, and cannot fake one

The other two metrics in saphes take token streams — surface forms for LIX, lemmas for
lexical diversity. This one takes head indices, and there is no tokeniser, stemmer or
heuristic that can produce them. That is a hard boundary, not a missing feature: saphes
is a calculation engine, and the parse comes from HuSpaCy, emtsv, a treebank or nothing.

The consequence worth internalising is that **the parse is the measurement**. Two
parsers disagreeing about whether a Hungarian preverb attaches to its verb will
disagree about MDD, and no amount of care inside saphes can repair that. Which annotation
scheme produced your trees belongs in your methods section next to the score.

## See also

- [Two token streams](two-token-streams.md) — the same argument for LIX and diversity
- [`syntax` reference](../reference/syntax.md) — the contracts and the formulas

## References

Futrell, R., Mahowald, K. & Gibson, E. (2015). Large-scale evidence of dependency length
minimization in 37 languages. *PNAS* 112(33), 10336–10341.

Jing, Y. & Liu, H. (2015). Mean Hierarchical Distance: Augmenting Mean Dependency
Distance. *Proceedings of the Third International Conference on Dependency Linguistics*,
161–170.

Liu, H. (2008). Dependency Distance as a Metric of Language Comprehension Difficulty.
*Journal of Cognitive Science* 9(2), 159–191.

Zhang, R. & Zhou, G. (2023). An investigation of the diachronic trend of dependency
distance minimization in magazines and news. *PLoS ONE* 18(1), e0279836.
