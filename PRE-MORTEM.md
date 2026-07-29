# saphes — pre-mortem

A fragility map: *assume a future incident has happened — what most likely caused it?*
This is a design-review artifact, not a bug list. Each entry names a failure mode, how it
would surface, and a direction. Nothing here is a confirmed defect; items marked
**[needs human decision]** would change public behaviour and are deliberately **not**
changed in this pass.

Scope: read-through of `src/saphes/` at 0.1.0. The core is small and fully covered by
tests, `ruff` and `ty` are clean, and the two arithmetic kernels are pinned by
hand-computed regression values (LIX = 45.0 from A=10, B=2, C=4) and by exact parity with
`textstat` given the same sentence count. The fragilities below are mostly *semantic*.

---

## High-impact fragilities

### 1. Someone wires both metrics to one token stream *(most important)*

The package's central claim is that `lexical_diversity` needs lemmas and `lix` needs
surface forms. A well-meaning refactor — "why are we tokenising twice?" — collapses them
into one stream and produces no error, no NaN, and two plausible numbers, one of which is
wrong.

Surfaces as: a Hungarian LIX that suddenly looks reasonable (it is not), or a TTR that
jumps between releases.

Guarded by `tests/test_contracts.py`: distinct parameter names, a required `unit`, the
`unit` recorded on every result, and pinned asymmetry *floors* rather than bare `>`
comparisons. The floor matters — a merged stream gives a gap of exactly 0.0, which a `>`
test would catch but a `>=` test would not, and which a "cleanup" of the assertion could
silently remove. The Hypothesis property (`types(lemma) <= types(surface)`) is the
strongest form, because it is a theorem about lemmatisation rather than a sample.

### 2. The bundled samples are far too small to calibrate anything

`load_hungarian()` is 14 tokens; `load_greek()` is 44. They exist to demonstrate the
surface/lemma asymmetry, and they do that honestly. They cannot support any claim about
what threshold a language needs — the long-word share on 14 tokens is noise.

This nearly went wrong once already: an early draft of `examples/lix_quickstart.py`
narrated "Hungarian saturates at threshold 6" over a table whose own numbers showed
Hungarian *below* English. The example was rewritten to claim only what its data supports
and to cite the corpus measurement separately.

Direction: when the calibration study lands, keep the corpus figures and the toy samples
visibly separate. Do not let a doctest-sized sample become the evidence for a
distributional claim.

**Update (0.2.0).** The calibration study honours this: every published figure comes from a
named corpus with its token count attached, and the bundled samples are used only to
demonstrate the surface/lemma asymmetry. The same trap surfaced once more during the study
itself — an early version of `validate_b.py` compared the lemma stream (0.71% of tokens,
selected by the analyser rather than at random) against the *full* surface stream, and
reported the resulting difference as the two-contracts asymmetry. It compared two different
samples. It now pairs each lemma with its own surface form, so both streams cover exactly
the same tokens. The honest gap is smaller than the toy samples suggest, and `validation.md`
says so.

### 3. Sentence counting is the whole disagreement, and *B* is often unavailable

`A` and `C` are robust — we match `textstat` exactly on both. Every real divergence is *B*.
And the two projects this package was built for cannot supply *B* at all: Homer's treebank
drops punctuation, and the `music_networks` spaCy pipeline runs with the parser disabled.

So most real use will go through `sentences=<explicit count>`, where the number's meaning
depends entirely on what the caller decided a sentence is. `sentence_source` on the result
is what keeps that auditable rather than hidden.

**[needs human decision]** — for Homer specifically, *B* = verse-line count is comparable
within the corpus but not to prose. That choice should be made once, written down, and
reused, not re-decided per notebook.

### 4. Björnsson's bands are a moving target in the literature

`LIX_BANDS` uses upper bounds at 30/40/50/60. Published versions of this table differ from
one another — some put "very easy" below 25, some band 25–30 separately. The constant is
exposed and documented as substitutable, and `band` returns `None` off threshold 6, which
removes the worst case. But a user comparing a saphes band label to a band label from
another tool may still disagree with us for reasons that have nothing to do with the score.

Direction: the score is the number to compare; the label is a convenience. The docs say so.

---

## Medium-impact fragilities

### 5. `length_policy="graphemes"` is not grapheme clusters

It drops combining marks after NFC. That is the right answer for residual marks NFC cannot
compose, but it is not Unicode grapheme-cluster segmentation, and the name invites the
confusion. Emoji, Indic conjuncts and ZWJ sequences are all counted differently than a
grapheme-cluster library would count them.

Mitigation is in place — the callable escape hatch, recorded as `custom:<qualname>` — but
the name is a hazard. **[needs human decision]** whether to rename it to
`"nfc_no_marks"` before 1.0, while the API is still young.

### 6. Case folding is off by default, and that is load-bearing

Lemmatisers vary on proper nouns, so saphes will not case-fold behind the caller's back.
The consequence is that a caller who forgets `case_fold=True` on a capitalised-heavy corpus
gets an inflated type count, and nothing warns them. `case_folded` is recorded on the
result, but nobody reads a field they did not know to look for.

Note this also cuts the other way in Greek: `case_fold=True` merges final sigma `ς` with
`σ`, which is usually desirable and is *not* obvious from the parameter name.

### 7. `mattr`'s empty-input contract differs from everything else

`mattr([])` returns `0.0`; `lexical_diversity([], unit=...)` raises. This is deliberate —
`mattr` preserves byte-compatible behaviour with the two duplicate implementations it
replaces, so downstream call sites change only an import. But two functions in one module
disagreeing about empty input is exactly the sort of thing a future tidy-up "fixes",
breaking `music_networks` silently at the same time.

Documented in both docstrings and in `CLAUDE.md`. A test pins it.

### 8. The `sentences` union is loose

`int | Sequence[str] | None` covers three genuinely needed paths, and `bool` and bare `str`
are explicitly rejected because both would otherwise be read as something plausible
(`True` → B=1; a string → a sequence of characters). But the union is still the widest
surface in the package, and a fourth accepted type would be easy to add carelessly.

---

## Low-impact, worth knowing

### 9. `segment.sentences(punkt=True)` is untested

Exercising it downloads an NLTK model, which would make CI network-dependent and flaky. The
branch is small and delegates immediately, but it is the one unexercised path in the
package (`segment.py` sits at 80% coverage for this reason alone).

### 10. Doctests are load-bearing and version-coupled

`--doctest-modules` runs every `Examples:` block in CI. That is a feature — it is why the
worked LIX example cannot drift. But it means result `__repr__`s must never include
`saphes_version`, or every release breaks every doctest. Enforced by
`test_repr_omits_the_version` in two test files.

### 11. A calibrated threshold gets treated as a truth

`recommended_threshold("hu")` returns 8, unanimously supported by six curves. The risk is
not that it is wrong — it is that it gets copied into a project as *the* Hungarian number
and stops being questioned. It is calibrated against **2000s web Hungarian and 2022 news**,
matched to a **Swedish** reference share that is itself one defensible choice among several.
The lyrics essay works on a different register entirely.

The result object carries its caveats for this reason, and `saphes.calibration` is public
so anyone can recompute on their own corpus. But nobody reads a `caveats` field they did not
go looking for.

Direction: when the lyrics essay adopts the threshold, recompute the long-word share on
actual lyrics first and check it lands near 27%. If it does not, that is a finding about
register, not a bug in the calibration.

### 12. The generated literal drifts from its generator

`src/saphes/datasets/_lix_calibration.py` is written by `run.py` and committed. Nothing in
CI checks that re-running the generator reproduces it — the runner has no corpus, so nothing
*can*. The generator formats its own output to keep the diff clean, which removes the most
likely cause of spurious drift, but a hand-edit to the literal would go unnoticed until
someone next ran the full study.

Mitigation in place: a "do not edit by hand" banner in the generated module, and the same
warning in `CLAUDE.md`. The real guard is that the numbers also live in
`results/lix_calibration.json` and in `findings.md`, so a hand-edit would disagree with two
other committed artifacts.

### 13. The elision-apostrophe behaviour is a silent tokeniser choice

`_TOKEN_RE` keeps *internal* apostrophes (`don't` = 5 letters) but drops *trailing* ones
(`μυρί’` → `μυρί`, 4 letters). Both are defensible; the combination is the kind of
undocumented decision that makes implementations disagree. It is documented and doctested,
which is the most this package can do about it.
