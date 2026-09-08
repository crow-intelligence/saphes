# How to load or customise the foreign word dictionary

saphes ships **no** Hungarian loan-word lexicon. `loanword_ratio` takes the set you give
it, or falls back to a spelling heuristic, or both — and refuses to run with neither. This
page is how to supply one.

## Pass a set

Any object supporting `in` works. A `set` of lower-case lemmas is the usual choice:

```pycon
>>> from saphes import loanword_ratio
>>> lexicon = {"komputer", "internet", "szoftver"}
>>> result = loanword_ratio(["a", "komputer", "gyors"], lexicon=lexicon)
>>> result.ratio
0.3333333333333333
>>> result.matches
('komputer',)

```

Entries are matched after NFC normalisation and case folding, so a lexicon of dictionary
head-words matches capitalised text without extra work.

## Use the bundled list

saphes ships no lexicon inside the package, but the repository carries one:
`experiments/loanwords/results/idegenszavak.txt`, 15,203 Hungarian lemmas.

```python
from pathlib import Path
from saphes import loanword_ratio

lexicon = set(
    Path("experiments/loanwords/results/idegenszavak.txt")
    .read_text(encoding="utf-8")
    .split()
)
result = loanword_ratio(lemmas, lexicon=lexicon, lexicon_id="idegenszavak-2026-09")
```

It is a **frequency-selected** list, not a dictionary transcription: candidates are MOKK
Hungarian Webcorpus word forms verified against Bakos Ferenc's *Idegen szavak és kifejezések
szótára*, with hapaxes and the Zipfian head removed. That second cut is the interesting one
— `internet`, `program` and `koncepció` are all in Bakos and all too common in Hungarian to
be felt as foreign, so they are not in the list. See
`experiments/loanwords/README.md` for the method, the parameters and two known limits.

It is deliberately **not** inside `saphes.datasets`. Every other bundled dataset can be
regenerated from a script in this repository; this one cannot, because the script reads a
copyrighted dictionary that is not here. A generated literal nobody can reproduce would be
worse than a file you load explicitly.

## Load one from a file

```python
from pathlib import Path
from saphes import loanword_ratio

lexicon = {
    line.strip().casefold()
    for line in Path("idegenszavak.txt").read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
}

result = loanword_ratio(lemmas, lexicon=lexicon, lexicon_id="idegenszavak-2026-09")
```

Pass `lexicon_id` so the result records which list produced the number. It never changes
the arithmetic; it is there so a table of results stays interpretable six months later.

## Feed it lemmas, never surface forms

This is the one that silently gives a wrong answer:

```pycon
>>> loanword_ratio(["komputerekkel"], lexicon={"komputer"}).ratio
0.0
>>> loanword_ratio(["komputer"], lexicon={"komputer"}).ratio
1.0

```

No error, no warning — just a ratio that is too low, and the more agglutinative the text,
the further off it is. See [why loan words need
lemmas](../explanation/why-loanwords-need-lemmas.md).

## Turn on the spelling heuristic — and pass tags with it

```pycon
>>> result = loanword_ratio(["absztrakt", "taxi", "kutya"], heuristic=True)
>>> result.matched, result.matched_by_heuristic
(2, 2)
>>> result.pattern_counts
(('absz', 1), ('x', 1))

```

!!! danger "The heuristic flags common Hungarian surnames"
    `th` survives in Hungarian surnames as an archaic spelling of plain *t*, so **Tóth,
    Horváth, Németh and Kossuth all match**, as do Széchenyi on `ch` and Wesselényi on `w`.
    On running text full of names the ratio is not slightly off — it is meaningless.

    Supply `pos_tags` whenever you enable the heuristic:

    ```pycon
    >>> loanword_ratio(
    ...     ["Tóth", "taxi"], heuristic=True, pos_tags=["PROPN", "NOUN"]
    ... ).matches
    ('taxi',)

    ```

saphes does no named-entity recognition and will not guess which tokens are names. The tags
come from your parser, the same way lemmas and sentence counts do.

## Change the patterns

`FOREIGN_PATTERNS` is a plain mapping of name to regex, and `patterns=` replaces it. To
drop the surname-prone rule:

```pycon
>>> from saphes import FOREIGN_PATTERNS, loanword_ratio
>>> safer = {k: v for k, v in FOREIGN_PATTERNS.items() if k != "th"}
>>> loanword_ratio(["Tóth", "Horváth"], heuristic=True, patterns=safer).matched
0

```

Each pattern is named so `pattern_counts` can report which fired. Adding your own is the
same shape: `{"my-rule": r"..."}`.

## Read the receipt, not just the ratio

```pycon
>>> result = loanword_ratio(
...     ["komputer", "taxi", "kutya"], lexicon={"komputer"}, heuristic=True
... )
>>> result.matched_by_lexicon, result.matched_by_heuristic
(1, 1)

```

`matched_by_lexicon` is dictionary evidence; `matched_by_heuristic` is a guess from
spelling. They are kept apart so you can decide how much to trust the total. A result whose
matches are mostly heuristic deserves a look at `matches` before it is published.
