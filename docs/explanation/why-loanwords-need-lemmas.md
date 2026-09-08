# Why loan word detection needs lemmas

Every metric in saphes states which token stream it wants. LIX wants surface forms because
word length is the signal. Lexical diversity wants lemmas because surface variation is
morphology, not vocabulary. The loan-word ratio wants lemmas too, and for a third reason:
**the thing being looked up is a dictionary head-word, and Hungarian buries it.**

## Morphology hides the root

*komputer* takes a suffix chain — *komputerek*, *komputerekkel*, *komputereinkről* — and a
set lookup matches none of them. This is not an edge case in Hungarian; it is the ordinary
condition of a noun in running text. A lexicon of a few thousand head-words will match a
few dozen tokens on a surface stream and a few thousand on a lemma stream, from the same
corpus.

The failure has the worst possible shape. It does not raise, it does not produce a NaN, and
it does not look wrong: it produces a **lower** ratio, which is exactly what someone
arguing that a text is not full of foreign words would like to see. The more agglutinative
the passage, the further off the number, and nothing in the output says so.

```pycon
>>> from saphes import loanword_ratio
>>> loanword_ratio(["komputerekkel"], lexicon={"komputer"}).ratio
0.0
>>> loanword_ratio(["komputer"], lexicon={"komputer"}).ratio
1.0

```

That is why `LoanwordResult.unit` is the literal `"lemma"` and not the package's
`TokenUnit` alias. There is exactly one legal stream, and pinning the type is what stops a
future tidy-up from letting a surface stream through unremarked — the same device
`LixResult.unit` uses in the opposite direction.

## Stemming is not enough

A stemmer would recover *komputer* from *komputerek* often enough to be tempting. But a
stemmer both over- and under-merges, and here the errors are asymmetric in a damaging way:
truncating a native word can manufacture a string that happens to be in the lexicon, and
truncating a foreign one can destroy the very cluster the entry was keyed on. `unit="stem"`
exists in saphes for lexical diversity, where a consistent wrong merge cancels out across a
type count. It does not cancel out in a membership test.

## The harder problem: which borrowings count

Hungarian has two words for this, and they are not synonyms.

A **jövevényszó** is a borrowing so thoroughly assimilated that no speaker experiences it
as foreign. *Ablak*, *király*, *pénz*, *asztal*, *ebéd* — all Slavic, all a thousand years
old, all as ordinary as any word in the language. An **idegen szó** is a word still felt as
foreign: *absztrakt*, *marketing*, *diszkrimináció*.

*Idegenszó-arány* means the second. But a lexicon built from a dictionary's etymology
fields contains the first in bulk, because etymology does not record assimilation — and a
ratio computed against such a list measures **etymological origin**, which is a different
quantity with a different interpretation. Both are legitimate; publishing one under the
other's name is not.

saphes cannot resolve this, and does not try. It ships no lexicon, requires you to supply
one, and records `lexicon_id` on every result so that the question "which list was this?"
has an answer. The judgement is yours because it is a judgement about a particular
vocabulary and a particular research question, not a fact about the language.

## Why there is no spelling heuristic

An obvious shortcut suggests itself: *x*, *w*, *q*, *ch*, *ph*, *th* and word-initial
clusters like *sztr-* really are foreign to native Hungarian orthography, so why not just
look for them?

It was tried, and removed. Three findings killed it.

**It covers almost nothing.** Only 8.4% of the shipped 15,203-lemma lexicon trips any such
pattern. The words that actually carry an *idegenszó-arány* in Hungarian prose —
*prioritás*, *konszenzus*, *implementáció*, *kompetencia* — look nothing like foreign words.
A spelling rule was never a substitute for a list.

**Hungarian manufactures the same spellings itself.** The potential suffix *-hat*/*-het* and
the allative *-hoz*/*-hez*/*-höz* place an *h* directly after a stem, so any stem ending in
*t*, *p* or *c* produces one of these digraphs at the seam: *látható*, *kapható*, *állathoz*,
*táncház*. On the MOKK Webcorpus that is 1,187 word forms and 2.5 million tokens of false
positive — and it is productive, so no exception list could ever have covered it. Add the
surnames, where *th* spells a plain *t*: *Tóth*, *Horváth*, *Németh*, *Kossuth*.

**Worst, it contradicted the lexicon.** The genuinely foreign words it found that a
frequency-selected list does not contain were *technológia*, *abszolút*, *szexuális* —
precisely the assimilated internationalisms such a list excludes on purpose. Enabling the
heuristic silently reversed the caller's own decision about where *idegen szó* ends and
ordinary Hungarian begins.

A lexicon is evidence about a particular vocabulary. A spelling rule was a guess, and it
disagreed with the evidence.

## See also

- [Two token streams](two-token-streams.md) — the same argument for LIX and diversity
- [How to customise the lexicon](../how-to/customise-the-loanword-lexicon.md)
