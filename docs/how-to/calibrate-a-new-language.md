# Calibrate a threshold for a new language or register

A calibrated threshold is a default, not a truth, and it is specific to the register it was
measured on. This is how to produce one for your own language or corpus.

You need a **frequency list**: a mapping of word to how often it occurs in running text. Not
a token list, and not a word list without counts.

## 1. Build a curve for your corpus

```pycon
>>> from saphes.calibration import length_curve
>>> counts = {"a": 500, "kertben": 400, "megvizsgálták": 100}
>>> mine = length_curve(counts, label="my-corpus", min_frequency=1)
>>> mine.share_above(6)
0.5

```

Half of all running tokens are longer than six letters.

## 2. Build a curve for a reference language

Use a Germanic corpus, built the same way — same length policy, same minimum frequency. The
shipped Hungarian calibration used Leipzig's `swe_news_2022_1M`.

```pycon
>>> reference = {"och": 500, "att": 400, "utveckling": 100}
>>> swedish = length_curve(reference, label="swe", min_frequency=1)
>>> swedish.share_above(6)
0.1

```

## 3. Match

```pycon
>>> from saphes.calibration import match_threshold
>>> match = match_threshold(mine, swedish, reference_threshold=6)
>>> match.threshold
7

```

Björnsson's 6 selects a tenth of running Swedish words. In this corpus it would have selected
half — a different statistic wearing the same name. Threshold 7 selects a tenth here, which
is what the second LIX term is supposed to mean.

## 4. Check whether the answer is settled

```pycon
>>> match.is_boundary
True
>>> match.runner_up
8

```

`is_boundary` is `True` here, meaning the runner-up matches nearly as well and the choice
between 7 and 8 is close to arbitrary. On a toy corpus that is expected; on real data it is
the signal to report the bracket rather than a single number.

## 5. Report the whole curve

```pycon
>>> for threshold, share in match.table[4:9]:
...     print(threshold, round(share, 3))
4 0.5
5 0.5
6 0.5
7 0.1
8 0.1

```

The deliverable is the curve plus the reason for the choice, not the winner alone. That is
what keeps the decision revisable when someone disagrees with your reference.

## Getting real frequency lists

- **Leipzig Corpora Collection** — `https://downloads.wortschatz-leipzig.de/corpora/` has
  matched `<lang>_news_2022_1M` archives for many languages, built with identical
  methodology, which is what makes a cross-language comparison honest.
- For a register check, count your own target texts. A `collections.Counter` over your
  tokens is exactly the input `length_curve` wants.

## Watch out for

**Token-weighted, never type-weighted.** A frequency list is a list of *types*, and rare
types are long. Passing all-1 counts is valid input and gives a completely different, wrong
answer that still looks plausible:

```pycon
>>> flat = length_curve(dict.fromkeys(counts, 1), label="wrong", min_frequency=1)
>>> round(flat.share_above(6), 3)
0.667

```

Two thirds, against the correct half. `length_curve` takes a mapping precisely so you cannot
forget the weights, but it cannot stop you passing the wrong ones.

**Match on the same policy.** Both curves must use the same `length_policy` and
`min_frequency`, or you are comparing different statistics. Nothing checks this; both values
are recorded on each curve so the mismatch is at least auditable afterwards.

## Related

- [Reproduce the calibration study](reproduce-the-calibration.md) — the full Hungarian
  pipeline, end to end.
- [Calibration data](../reference/calibration-data.md) — the measured curves the shipped
  threshold came from.
- [Why the threshold moves](../explanation/why-the-threshold-moves.md) — the reasoning
  behind equipercentile matching.
