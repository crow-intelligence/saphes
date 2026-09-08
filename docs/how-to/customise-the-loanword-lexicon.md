# How to load or customise the foreign word dictionary

saphes ships **no** Hungarian loan-word lexicon inside the package. `loanword_ratio`
requires the set you give it — `lexicon` is a required argument, and there is no fallback.
This page is how to supply one.

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

## Read the receipt, not just the ratio

```pycon
>>> result = loanword_ratio(["komputer", "taxi", "kutya"], lexicon={"komputer"})
>>> result.matched, result.total_lemmas
(1, 3)
>>> result.matches
('komputer',)

```

`matches` is the audit trail: the lemmas that produced the number, so a surprising ratio can
be checked rather than argued about. `lexicon_size` is there too — a suspiciously small one
is the usual explanation for a suspiciously low ratio.

!!! note "There is no spelling heuristic"
    Earlier versions carried one — regexes for `x`, `w`, `ch`, `th`. It was removed rather
    than repaired: it covered only 8.4% of the shipped lexicon, most of what it added
    beyond it was English text in the corpus and native Hungarian that merely looks foreign
    (*mintha*, *otthon*, *látható*, *Tóth*), and the genuinely foreign words it added were
    the assimilated ones a frequency-selected lexicon deliberately excludes. A lexicon is
    evidence; the spelling rule was a guess that contradicted it.
