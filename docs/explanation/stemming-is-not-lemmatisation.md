# Stemming is not lemmatisation

saphes offers `unit="stem"` as a fallback for callers with no lemmatiser. It is a real
improvement on measuring surface forms, and it is not a cheap lemmatiser. This page is about
the difference, because the two produce numbers that look alike and are not comparable.

## What a stemmer actually does

A lemmatiser maps a form to its dictionary form, using a lexicon: `házakat` → `ház`. Snowball
has no lexicon. It strips suffixes by rule, left to right, and returns whatever is left —
which is frequently not a word:

| form | stem | lemma |
|---|---|---|
| `fánál` | `fá` | `fa` |
| `adtam` | `adt` | `ad` |
| `enni` | `enn` | `eszik` |

`fá` and `adt` are not Hungarian words and never were. They are addresses in a space of
truncated strings, useful because two forms of the same word usually land on the same one.

## It fails in both directions at once

This is the part that makes a stem count incomparable to a lemma count, rather than merely
noisier than one.

**It over-merges.** Two distinct lemmas that share a truncated prefix collapse into one type,
pushing the diversity down.

**It under-merges.** One lemma can reach two different stems, pushing the diversity up. The
bare form and the inflected forms of the same word take different paths through the rules:

```pycon
>>> from saphes import hungarian_stems
>>> hungarian_stems(["kutya", "kutyák", "kutyáknak"])
['kuty', 'kutya', 'kutya']

```

All three are the lemma `kutya`. A lemmatiser gives one type; the stemmer gives two.

Because the two errors push opposite ways, you cannot even say whether a stem-based TTR runs
above or below the lemma-based one in general. On the bundled Hungarian sample it sits
between surface and lemma — 0.64 against 0.71 and 0.57 — but that ordering is a measurement,
not a property, and `tests/test_contracts.py` pins it as one.

## It is not even idempotent

Stemming a stem is not a no-op, because the output can itself look suffixed:

```pycon
>>> once = hungarian_stems(["kutyaak"])
>>> once
['kutya']
>>> hungarian_stems(once)
['kuty']

```

So a stem depends on how many times it went through the pipeline. That is a second reason a
stem-based number is only meaningful within one pipeline.

## What follows for reporting

**A stem-based TTR is comparable only to another stem-based TTR from the same stemmer
version.** Not to a lemma-based one, not to one from a different stemmer, not to one from
the same stemmer after an upgrade. Never put a stem column and a lemma column side by side
in the same table.

This is exactly why `TokenUnit` has a third member instead of stems being passed off as
lemmas. `unit=` has no default and every result records it, so the question "which stream
produced this number?" always has an answer written down. A stem stream labelled `"lemma"`
would be the failure the whole design exists to prevent: not an error, not a `NaN`, just a
plausible wrong number in a column that claims to be something else.

## See also

- [The two token streams](two-token-streams.md) — the invariant this extends.
- [Stem when you have no lemmatiser](../how-to/stem-without-a-lemmatiser.md) — the recipe.
- [What gets recorded](what-gets-recorded.md) — why every result carries its provenance.
