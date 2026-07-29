# Mutation testing summary

Tool: [`mutmut`](https://github.com/boxed/mutmut) 3.x (dev-only; not run in CI).
Run with `SAPHES_MUTATION=1 uv run mutmut run` — the env var loads a Hypothesis profile in
`tests/conftest.py` that suppresses the `differing_executors` health check and disables the
example database during parallel mutation runs.

## Scope

Mutation is scoped to the arithmetic core and its fast tests (see `[tool.mutmut]` in
`pyproject.toml`):

- mutated: `readability.py`, `diversity.py`, `segment.py`
- test selection: `test_readability.py`, `test_diversity.py`, `test_segment.py`,
  `test_contracts.py`

`datasets/` and `_types.py` are **not** mutated — they hold literals and type aliases, not
logic. This is a deliberate cap, not full coverage.

## Score

| metric | value |
|--------|------:|
| total mutants | 386 |
| killed | 327 |
| skipped (no covering test) | 22 |
| **survived** | **37** |
| **mutation score** | **~90%** (327 / 364 testable) |

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

## What survives, and why

All 37 remaining survivors are behaviourally equivalent or unreachable. They fall into four
classes.

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
```

The `mutants/` working copy and `.mutmut-cache` are gitignored.
