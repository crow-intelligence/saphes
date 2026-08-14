# Why implementations disagree

A 2022 evaluation of five Python readability libraries found they rank the same texts
differently. LIX is four arithmetic operations, so the disagreement is not in the formula. It
is in what gets counted.

This is one of the two reasons saphes exists, and it is worth being concrete about, because
the usual response — assuming one library is buggy — is almost never right.

## Where saphes and textstat part company

Compared against `textstat` 0.7.13:

| text | textstat | saphes | textstat *B* | saphes *B* | *A* | *C* |
|---|---:|---:|---:|---:|---:|---:|
| ordinary prose | 27.50 | 27.50 | 2 | 2 | 15 | 3 |
| short sentences | 53.44 | **47.44** | **1** | **3** | 9 | 4 |
| abbreviation | 14.59 | 14.59 | 2 | 2 | 11 | 1 |

*A* and *C* agree everywhere. The arithmetic is identical. Given the same *B*, the scores
match to floating-point exactness — that equality is asserted as a test in the saphes suite.

Every divergence is the sentence count.

## What textstat does differently

`textstat.sentence_count` splits on `\b[^.!?]+[.!?]*` and then **discards any sentence of two
words or fewer**, flooring the result at one. So:

> He ran. She sang. The committee deliberated extensively yesterday.

has three sentences. textstat counts one, because "He ran." and "She sang." are each two
words and get dropped. That collapses *A/B* from 3.0 to 9.0 and inflates LIX by six points.

## Neither of them is wrong

This is the part worth sitting with. Björnsson's original *B* was "the number of periods —
period, colon, or capital first letter", which is not what any modern sentence splitter does.
There is no canonical *B* to be right about.

A rule that drops very short sentences is defensible: it guards against a heading or a list
item being counted as a sentence and dragging the average down. saphes keeps them, on the
grounds that "He ran." is a sentence and discarding it silently changes the measurement. Both
are choices. Only one of them is documented by the library that makes it.

That is the actual complaint — not that textstat chose differently, but that a caller cannot
see that a choice was made.

## saphes makes the same kind of choice

It would be comfortable to stop there, but the bundled splitter suppresses sentence
boundaries too, in three cases: after a known abbreviation, after a single capital letter it
reads as an initial, and before a lowercase letter it reads as dialogue attribution. Each is
a heuristic and each can be wrong. "I work at Acme Inc. They pay well." comes back as one
sentence, not two.

The difference is not that saphes is more careful. It is that the choice is documented, the
splitter is replaceable, and the result records which one ran. `sentence_source` says whether
*B* was segmented, pre-split or supplied; `sentencer` names the splitter. A number that
disagrees with another library can be traced rather than argued about.

## A footnote on trusting documentation

`textstat`'s own docstring states the formula as `LIX = A/B + A*100/C` — the last term
transposed. The code is correct; the documentation is not.

It is a small thing, and easy to be smug about. The useful lesson is the opposite: published
readability numbers almost never come with the counts that produced them, so this kind of
error is invisible from the outside. It is why every saphes result carries *A*, *B* and *C*,
and why a score alone should be treated as a claim rather than a measurement.

## See also

- [Match another implementation's LIX](../how-to/match-another-implementation.md) — how to
  reconcile a specific number.
- [Supply a sentence count](../how-to/supply-a-sentence-count.md) — how to control *B*.
- [Why every result carries its counts](what-gets-recorded.md).
