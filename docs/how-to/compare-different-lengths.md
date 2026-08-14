# Compare texts of different lengths

TTR falls as a text grows, so a raw TTR over corpora of different sizes mostly ranks them by
size. If you are comparing decades, books or authors whose texts differ in length, use MATTR
instead.

## Use MATTR

Pass a window:

```pycon
>>> from saphes import lexical_diversity
>>> tokens = ["a", "b", "c", "d"] * 60
>>> result = lexical_diversity(tokens, unit="lemma", window=100)
>>> result.mattr
0.04
>>> result.window
100

```

`.ttr` is still there, and still length-sensitive. Report `.mattr` when lengths differ.

## Or use the bare function

For a drop-in replacement in existing code:

```pycon
>>> from saphes import mattr
>>> mattr(["a", "b", "a", "b"], window=2)
1.0

```

## Choosing a window

The window is the span within which distinctness is measured, so it fixes what "varied" means.
Pick one and hold it fixed across everything you compare — a MATTR at window 50 and a MATTR at
window 500 are different statistics.

100 is the conventional default and what `mattr` uses if you say nothing. Report the window
alongside the number; `DiversityResult.window` records it for you.

Every text you compare must be at least `window` tokens long, or the short ones quietly fall
back to plain TTR and you are back to comparing by size:

```pycon
>>> mattr(["a", "b", "c"], window=10)
1.0

```

Three tokens, window ten — that 1.0 is a plain TTR, not a MATTR.

## Watch out for

**The bare `mattr` does not validate its window.** `lexical_diversity` does; `mattr` does not,
because its signature is frozen for drop-in use.

```pycon
>>> mattr(["a", "b"], window=0)
Traceback (most recent call last):
    ...
ZeroDivisionError: division by zero

```

**Order matters, so never pass a set.** A set is accepted and returns a number, but the
windows are drawn over arbitrary iteration order and the result means nothing. Nothing raises:

```pycon
>>> lexical_diversity({"a", "b", "c"}, unit="lemma", window=2).mattr is not None
True

```

Pass a list or a tuple, in document order.

**Concatenate in a stable order** when pooling documents into one stream — MATTR sees the
joins, so shuffling the documents changes the number.

## Related

- [`mattr` reference](../reference/diversity.md) — the full contract, including the
  degrade-to-TTR rule and the window traps.
- [What gets recorded](../explanation/what-gets-recorded.md) — why the window travels on the
  result.
