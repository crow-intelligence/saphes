# The two token streams

The single most important idea in saphes is that its two metrics require **opposite** input,
and that feeding them the same input produces no error at all.

| Metric | Wants | Because |
|---|---|---|
| `lexical_diversity` | **lemmas** | Surface variation is noise — it measures morphology, not vocabulary. |
| `lix` | **surface forms** | Word length *is* the signal, and lemmatising erases it. |

There is a third value, `unit="stem"`, for callers with no lemmatiser. It is a *degraded
substitute* for the lemma stream rather than a third contract — see
[Stemming is not lemmatisation](stemming-is-not-lemmatisation.md).

## Why diversity wants lemmas

Type–token ratio counts distinct words. But "distinct" is doing a lot of work: Hungarian
`ház`, `házak`, `házban` and `házakat` are four distinct strings and one word — house, in
four cases. Counting them separately does not measure a richer vocabulary; it measures a
richer *case system*.

That matters most for exactly the languages this package was built for. English inflects
lightly, so an un-lemmatised TTR is wrong by a little. Hungarian is agglutinative and Ancient
Greek heavily inflected, so it is wrong by a lot — and wrong in a way that correlates with
the language rather than the text, which makes cross-linguistic comparison meaningless.

Un-lemmatised TTR is not a cruder measure of the same thing. It is a measure of a different
thing, wearing the same name.

## Why readability wants surface forms

LIX counts words longer than a threshold. `házakban` is eight characters; its lemma `ház` is
three. Lemmatise first and the long words simply stop being long.

The failure is worst in the same languages, and for the same reason: the more morphology a
language carries, the more of the word length lives in the endings that lemmatisation
removes. On the bundled Hungarian sample, LIX computed on lemmas comes out at 4.7 against
26.1 on the forms as written.

Neither number looks wrong on its own. That is the whole problem.

## Why this cannot be solved by inspection

saphes could try to guess. It could check whether a token stream "looks lemmatised" —
whether the tokens are short, or share prefixes, or match a dictionary.

It deliberately does not. Any such test is a heuristic, and heuristics are wrong sometimes.
A package whose argument is that silent wrongness is the enemy cannot then introduce a silent
guess at its own foundation. The alternative — asking the caller, and recording the answer —
is less convenient and completely reliable.

There is a second reason. saphes does not lemmatise, and could not check a claim it has no
machinery to verify. Lemmatisation is language-specific and heavy: CLTK or a treebank for
Greek, huspacy or emtsv for Hungarian. Bundling one would wreck a deliberately tiny package
and duplicate work already done upstream, better, by people who specialise in it. The caller
lemmatises; saphes measures.

The optional Snowball stemmer is the deliberate exception, and it does not breach the
principle, because it does not claim to have lemmatised. It is a few hundred lines of suffix
stripping with no lexicon, it lives behind an extra, and its output is declared as
`unit="stem"` — a third stream with its own name, rather than a lemma stream that happens to
be wrong.

## What stops the mistake

Four guards, none of which inspects the data:

**The unit is required.** `lexical_diversity` has no default for `unit`, so the call does not
run until you have said what your tokens are. This catches the highest-probability accident —
copying a working `lix(...)` call and changing the function name — because a `lix` call never
carries `unit=`.

**The parameter names differ.** `lix(words=...)` against
`lexical_diversity(lemmas=...)`. Crossing them raises `TypeError` at the call site, before
any measurement happens.

**A raw string is refused where it could only be wrong.** A string can only be split into
surface forms, so `lexical_diversity("some text", unit="lemma")` is a contradiction, and is
rejected rather than quietly measured as something else.

**Every result records its unit.** So a table of scores written months ago can still be
interpreted, which is the difference between a number and a finding.

None of these prevent a determined mistake. A caller who declares `unit="lemma"` and passes
surface forms gets a wrong answer, and nothing can stop that. What the guards prevent is the
*accidental* version — the one that happens because two similar-looking calls sat next to
each other in a notebook.

## The asymmetry as a theorem

The regression test that guards this is not a sample but a proof. Lemmatisation is a function
on tokens, so it can only merge types, never split them. With the token count held equal, the
lemma stream can therefore never have more types than the surface stream, and never the
higher TTR.

**The theorem does not extend to stems.** Stemming is a function on tokens too, so
stem-TTR ≤ surface-TTR for the same reason. But a stemmer is not a coarsening of a
lemmatiser: it both over-merges and under-merges, and it can give one lemma two different
stems. So nothing follows about how a stem-TTR compares to a lemma-TTR — that ordering is a
measurement, not a proof. See
[Stemming is not lemmatisation](stemming-is-not-lemmatisation.md).

That is why the property test asserts `<=` rather than `<`: every suffix in a generated draw
may have come out empty, in which case the two streams are identical and the ratio is equal.
The pinned floors in the sample-based tests do the complementary job — a refactor that wired
both metrics to one stream would produce a gap of exactly zero, and a floor of 0.05 catches
that where a bare `>` would not.

## See also

- [Your first measurement](../tutorial/first-measurement.md) — see the gap yourself, in about
  ten minutes.
- [What gets recorded](what-gets-recorded.md) — why the unit travels with every result.
- [`lexical_diversity` reference](../reference/diversity.md) — the full contract, including
  what happens when the stream is unordered or non-string.
