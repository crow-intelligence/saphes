# Why every result carries its counts

`lix` could return a float. It returns an object carrying *A*, *B*, *C*, the threshold, the
length policy, where the sentence count came from, how many empty tokens were dropped, and
the version of saphes that produced it. This is a deliberate cost, and worth explaining.

## A bare float is unauditable

A 2022 evaluation of five Python readability libraries found they rank the same texts
differently. Not because any of them computes the formula wrongly — the arithmetic is four
operations — but because they disagree about what a word is, what a sentence is, and what
counts as long.

Given only a score, none of that is recoverable. You cannot tell whether a published LIX of
47 differs from yours because the text differs, because the segmenter differs, or because
someone used a different threshold. Given *A*, *B* and *C*, you can tell immediately.

This is why the reference documentation for a saphes result reads like a lab notebook rather
than a return value. The score is the least interesting thing in it.

## Provenance survives the code that produced it

Analyses outlive their scripts. A table of per-decade LIX scores in a paper draft, six months
old, is uninterpretable if the only thing in the table is the score — was that Hungarian at
the calibrated threshold, or at Björnsson's default? Was diversity measured on lemmas?

Because `unit`, `long_word_threshold`, `length_policy` and `sentence_source` are on every
row, the table answers its own questions. `to_dict()` exists so that this survives
serialisation to JSON or a dataframe.

## The version is part of the record

Every result carries `saphes_version`. Methods change: a segmenter improves, a default is
reconsidered, a bug is fixed. A number computed under 0.1.0 and a number computed under 0.4.0
may not be comparable, and the only way to know is if each says which produced it.

This has one visible consequence: result reprs deliberately **omit** the version, because
otherwise every release would break every doctest that prints a result. The version is in
`to_dict()`, where machines look, not in the repr, where humans do.

## What is not recorded

The text itself. saphes measures and forgets; it never retains what it was given. That keeps
results small enough to sit in a dataframe and avoids a package quietly holding onto a corpus.

Nor is the *identity* of anything recorded beyond a label. `sentencer` records a function's
qualified name, not the function. `length_policy` records `custom:my_counter`, not the
counter. This is enough to know what was done and not enough to redo it automatically — a
deliberate limit, since serialising callables would make the record unreadable and the
package much larger than two metrics deserve.

## The same principle, one level down

The calibration study works this way too. `ThresholdRecommendation` does not return the
number 8; it returns 8 together with the share it matched, the reference it matched against,
the runner-up, and which of seven independently computed curves agreed. That was not
over-engineering: on a truncated sample the answer really was contested between 7 and 8, and
a bare integer would have hidden it.

The rule that falls out of all of this: **if a choice changed the number, the number should
say so.**

## See also

- [The two token streams](two-token-streams.md) — the choice this principle exists to make
  visible.
- [Calibration data](../reference/calibration-data.md) — the same idea applied to a study
  rather than a measurement.
