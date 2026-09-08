# Mutation testing summary

Tool: [`mutmut`](https://github.com/boxed/mutmut) 3.x (dev-only; not run in CI).
Run with `SAPHES_MUTATION=1 uv run mutmut run` — the env var loads a Hypothesis profile in
`tests/conftest.py` that suppresses the `differing_executors` health check and disables the
example database during parallel mutation runs.

## Scope

Mutation is scoped to the arithmetic core and its fast tests (see `[tool.mutmut]` in
`pyproject.toml`):

- mutated: `readability.py`, `diversity.py`, `segment.py`, `syntax.py`, `adapters.py`
- test selection: `test_readability.py`, `test_diversity.py`, `test_segment.py`,
  `test_syntax.py`, `test_adapters.py`, `test_contracts.py`

`datasets/` and `_types.py` are **not** mutated — they hold literals and type aliases, not
logic. This is a deliberate cap, not full coverage.

## Score

| metric | value |
|--------|------:|
| total mutants | 1,073 |
| killed | 929 |
| skipped (no covering test) | 22 |
| detected by timeout | 1 |
| **survived** | **121** |
| **mutation score** | **~88%** (929 / 1,051 testable) |

Mutants generated: `syntax` 578, `readability` 190, `diversity` 134, `adapters` 111,
`segment` 60. **Survivors: `syntax` 68, `readability` 23, `adapters` 17, `diversity` 11,
`segment` 2.**

> **Read survivor counts from the `: survived` lines only.** `mutmut results` also lists
> the 22 "no covering test" mutants, and all 22 are in `segment.py` — the `punkt` branch
> that is untested by design. Counting every line in that file reports `segment` at 24
> rather than 2, and makes the three original modules look like 58 survivors instead of
> 36. An earlier revision of this document made exactly that mistake and recorded a
> regression that does not exist: those three modules stand at **36**, against the **37**
> measured on 2026-07-29, which is no change at all.

The one timeout is a kill, not a gap. `seen.add(node)` → `seen.add(None)` in `_depths`
disables cycle detection, so the mutant loops forever on the cyclic-parse test rather than
raising. It is detected by not finishing.

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

68 survivors: **64 mutations of error-message literals**, and **4 equivalent mutants**. No
surviving mutant changes a distance, a depth, a count or a score.

Two equivalents are the re-indexing base in `_arcs`:

```python
renumbered[token.index] = len(renumbered) + 1   # -> - 1, or + 2
```

Dependency distance is a *difference* of positions, so shifting every renumbered index by a
constant cancels exactly, and the dict's keys — which is what `token.head not in
renumbered` tests — are untouched either way. That these cannot be killed *is* the
translation invariance the metric is supposed to have.

The other two come from the MHD path:

- `deepest = 0` → `deepest = 1`. Any sentence that contributes has a non-root token, so its
  maximum depth is at least 1 and `max(0, x) == max(1, x)`.
- `min_sentence_length: int = 0` → `1`. `len(content) < 0` is never true, and `len(content)
  < 1` is true only for an all-punctuation sentence — which the `if not counted` branch
  skips anyway, incrementing the same counter. Same outcome by two routes.

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

### And again when MHD landed

Adding hierarchical distance reintroduced the same three classes in the new code — 32
non-string survivors, down to 4 after one round. The MHD-specific one worth recording:
`sum(per_sentence) / len(per_sentence)` → `sum(per_sentence) * len(per_sentence)` survived
every single-sentence test, because dividing by one and multiplying by one agree. Only a
two-sentence macro assertion distinguishes them.

One gap needed a *shape* of input the suite did not contain at all. The propagation of
"an ancestor was punctuation" down a chain is only exercised when several uncached
ancestors are walked in one pass, which needs a **head-final** tree — a token whose
governor comes after it. Every other fixture had each governor already computed by the time
its dependent was reached, so the propagation never carried more than one step and two
mutations of it were invisible.

## What survives in `adapters.py`

The first pass left 23 survivors, **5 of them not error-message text**. After one round
of fixes there are 17, **all** of them error-message text: no surviving mutant changes an
index, a head, a tag or a count. One was a genuine
piece of dead code and was deleted rather than tested around:

```python
for number, raw in enumerate(text.splitlines(), start=1):
    line = raw.rstrip("\n")     # splitlines() has already removed it
```

Both mutations of that `rstrip` survived because neither could change anything. The line is
gone; `splitlines()` strips the terminator itself.

The other four were test gaps, each pinning something the adapters actually promise:

- `line.split("\t")` → `line.split(None)` — splitting on whitespace instead of tabs. Only
  distinguishable when a field *contains* a space, which `MISC` does in glossed treebanks.
- `DepToken(..., upos)` → `DepToken(..., None)` — the POS tag being dropped on the CoNLL-U
  path. The doctest covered it; doctests are not in the mutation test selection, so a
  unit test now covers it too.
- `offset = tokens[0].i` → `None` — `offset` appears only in an error message, so the test
  now asserts the token range that message reports.

## What survives in the original three modules

36 survivors, against the 37 measured on 2026-07-29 — unchanged in substance. The account
of *kinds* below still holds; only the tallies inside it are from that original run.

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
