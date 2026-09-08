# Mutation testing summary

Tool: [`mutmut`](https://github.com/boxed/mutmut) 3.x (dev-only; not run in CI).
Run with `SAPHES_MUTATION=1 uv run mutmut run` — the env var loads a Hypothesis profile in
`tests/conftest.py` that suppresses the `differing_executors` health check and disables the
example database during parallel mutation runs.

## Scope

Mutation is scoped to the arithmetic core and its fast tests (see `[tool.mutmut]` in
`pyproject.toml`):

- mutated: `readability.py`, `diversity.py`, `segment.py`, `syntax.py`
- test selection: `test_readability.py`, `test_diversity.py`, `test_segment.py`,
  `test_syntax.py`, `test_contracts.py`

`datasets/` and `_types.py` are **not** mutated — they hold literals and type aliases, not
logic. This is a deliberate cap, not full coverage.

## Score

| metric | value |
|--------|------:|
| total mutants | 695 |
| killed | 598 |
| skipped (no covering test) | 22 |
| **survived** | **75** |
| **mutation score** | **~89%** (598 / 673 testable) |

Per module, by mutants generated: `syntax` 311, `readability` 190, `diversity` 134,
`segment` 60. Survivors: `syntax` 39, `segment` 24, `readability` 23, `diversity` 11.

> **The three original modules account for 58 of the 75 survivors, against the 37 this
> file recorded when it was written.** That measurement dates from 2026-07-29, twelve
> commits before the Hungarian iteration landed on `main`, and was never refreshed; the
> mutant counts for those modules are essentially unchanged (384 against 386), so the
> extra survivors are in code that changed under them. Adding `syntax.py` does not touch
> those three modules. **The cause has not been investigated** — it belongs with the
> "mutation-testing baseline" item on the README roadmap, not with this change.

The kernels are killed outright: every mutation that changes `lix_from_counts`,
`ttr_from_counts`, the long-word comparison, or the MATTR sliding counter is caught by the
hand-computed regression value (LIX = 45.0 from A=10, B=2, C=4), the `textstat` parity test,
or the Hypothesis properties.

### What the first run found

The initial run scored 304/60. Inspecting the survivors surfaced **six real test gaps**,
all now closed:

| survivor | what it revealed |
|---|---|
| `mattr(tokens, window=100)` → `101` | nothing exercised the default window |
| `rix(..., long_word_threshold=6)` → `7` | the canonical text had no 7-letter word, so the default was untested |
| `counts[tok] += 1` → `= 1` in MATTR's priming loop | no test had a token repeating inside the first window with `n > window` |
| `word_length(token, policy=...)` → policy dropped | a test checked the policy was *recorded*, but not that it was *applied* |
| `if policy == "graphemes"` → `!=` | the grapheme test used input where NFC and grapheme counts agreed, so it discriminated nothing |
| `score < upper` → `<=` in `interpret_lix` | band boundaries were only asserted to be non-`None`, never to be the right label |
| `saphes_version=...` → `None` | neither result object asserted its own version field |

That is the value of the exercise: five of those seven were tests that *looked* like they
covered something and did not.

## What survives in `syntax.py`

39 survivors: **37 mutations of error-message literals**, and **2 genuinely equivalent
mutants**. No surviving mutant changes a distance, a count, or a score.

The two equivalent ones are both the re-indexing base in `_arcs`:

```python
renumbered[token.index] = len(renumbered) + 1   # -> - 1, or + 2
```

Dependency distance is a *difference* of positions, so shifting every renumbered index by
a constant cancels exactly. The dict's keys — which is what `token.head not in renumbered`
tests — are untouched either way. These cannot be killed, and the fact that they cannot is
the translation-invariance property the metric is supposed to have.

### What the first run found here

Mutation testing was worth running on this module rather than assumed: the first pass left
**68 survivors, 16 of them real**, and every one was a test gap rather than a bug. Three
classes, all invisible to a suite that looked complete:

1. **Boundary values one step off a comparison.** `total_distance < pairs` → `<=` survived
   because no test called the kernel with a sentence whose arcs are all adjacent — an
   entirely ordinary sentence. `len(content) < min_sentence_length` → `<=` survived for the
   same reason, and would have dropped exactly the three-word sentences Jing & Liu keep.
2. **Accumulators verified on one sentence only.** Five `x += n` → `x = n` mutants lived
   because the counts were only ever asserted on a single sentence, where the two are
   identical. `TestAccumulation` exists for this.
3. **A filter that keeps the wrong half.** `require_single_root and sentence_roots != 1` →
   `== 1` survived because the test asserted `sentences == 1` and `skipped == 1`, which
   hold whichever of the two sentences was dropped. Only the *score* distinguishes them.
   `TestFilterSelectsTheRightSentence` asserts that instead.

The third is the one worth remembering: a count-only assertion cannot tell a filter from
its inverse.

## What survives in the original three modules

The classes below were written against the 37 survivors measured on 2026-07-29 and are
retained as an account of *kinds*; the counts no longer add up to the current total (see
the note under Score).

**1. Error-message text (26 mutants).** Mutating the literals inside `msg = ...` — blanking
them, upper-casing them, lower-casing them. No test asserts exact message text; the
`pytest.raises(match=...)` patterns deliberately target a distinctive substring rather than
the whole sentence, so a paraphrase of the rest of the message does not fail the suite.
Asserting full message text would make every wording improvement a test failure, which is a
worse trade.

**2. Recorded-label formatting (5 mutants).** Variants of
`getattr(splitter, "__qualname__", None) or repr(splitter)`. Every variant still produces a
string containing the splitter's name, which is what the tests assert. These change how a
provenance label is *derived*, not what it identifies.

**3. Unreachable code (4 mutants).** Three index variants of `interpret_lix`'s final
`return`, which carries `# pragma: no cover` because the last entry in `LIX_BANDS` has an
infinite upper bound, so the loop always returns first. Plus one inside the `punkt=True`
branch of `segment.sentences`, which is untested by design — exercising it downloads an NLTK
model and would make CI network-dependent.

**4. Genuinely equivalent mutants (2).**

- `start = 0` → `start = None` in `_regex_sentences`. `text[None:i]` is valid Python and
  means `text[0:i]`.
- `if n <= window` → `if n < window` in `mattr`. At `n == window` the two branches compute
  the same value: the fast path returns `len(set(tokens))/n`, and the slow path primes one
  window covering all `n` tokens, never enters the sliding loop, and returns
  `distinct/(1*window)`.

## Reproducing

```bash
SAPHES_MUTATION=1 uv run mutmut run
SAPHES_MUTATION=1 uv run mutmut results
SAPHES_MUTATION=1 uv run mutmut show saphes.diversity.x_mattr__mutmut_6
SAPHES_MUTATION=1 uv run mutmut show saphes.syntax.x__arcs__mutmut_22
```

The `mutants/` working copy and `.mutmut-cache` are gitignored.
