# Troubleshooting

## Why doesn't my score match `textstat` or an online LIX calculator?

Almost always: **the sentence count**.

A 2022 evaluation of five Python readability libraries found they rank the same texts
differently, because they count words, sentences and long words differently. saphes exists
partly to make that difference visible rather than mysterious — so here is the comparison,
run against `textstat` 0.7.13.

| text | `textstat` | saphes | textstat *B* | saphes *B* | *A* | *C* |
|---|---:|---:|---:|---:|---:|---:|
| ordinary prose | 27.50 | 27.50 | 2 | 2 | 15 | 3 |
| short sentences | 53.44 | **47.44** | **1** | **3** | 9 | 4 |
| abbreviation | 14.59 | 14.59 | 2 | 2 | 11 | 1 |

*A* and *C* agree everywhere. The arithmetic is identical. Give saphes the same *B* and the
scores match to floating-point exactness:

```python
import textstat
from saphes import lix

lix(text, sentences=textstat.sentence_count(text)).score == textstat.lix(text)   # True
```

That equality is asserted as a test in the saphes suite.

### What differs, precisely

`textstat.sentence_count` splits on `\b[^.!?]+[.!?]*` and then **silently discards any
sentence of two words or fewer**, flooring the result at 1. So:

```
"He ran. She sang. The committee deliberated extensively yesterday."
```

has three sentences. `textstat` counts **one**, because "He ran." and "She sang." are each
two words and get dropped. That collapses *A/B* from 3.0 to 9.0 and inflates LIX by 6
points. saphes keeps all three.

Neither behaviour is *wrong* — Björnsson's original *B* was "periods, colons, or capital
first letters", which is not what any modern splitter does. There is no single right answer
here. saphes takes a position, documents it, makes the splitter pluggable, and **records
which one produced the number**:

```python
result = lix(text)
result.sentences         # 3
result.sentence_source   # 'segmented'
result.sentencer         # 'sentences'
```

If you need to reproduce a `textstat` figure exactly, pass its count:

```python
lix(text, sentences=textstat.sentence_count(text))
```

### A footnote worth knowing

`textstat`'s own docstring states the formula as `LIX = A/B + A*100/C` — the last term
transposed. The code is correct; the documentation is not. This is the general hazard:
published LIX numbers rarely come with the counts that produced them, so they cannot be
checked. Every saphes result carries its counts for exactly this reason.

## My Hungarian / Greek / Finnish texts all score the same

The index has saturated. At `long_word_threshold=6`, the second term `100·C/A` is close to
its ceiling for every text, so differences between texts stop showing up.

Raise the threshold. See [Threshold and saturation](tutorials/threshold_saturation.md).

## `lexical_diversity()` raised a TypeError about `unit`

`unit` is required and has no default:

```python
lexical_diversity(tokens, unit="lemma")     # tokens are lemmas
lexical_diversity(tokens, unit="surface")   # tokens are surface forms
```

The choice changes what the number means, so saphes will not guess. See
[The two contracts](tutorials/two_contracts.md).

## `lexical_diversity()` refused my string

```python
lexical_diversity("some text", unit="lemma")   # TypeError
```

A string can only be split into surface forms. Lemmas have to come from upstream analysis —
huspacy, CLTK, a treebank. If you genuinely want surface diversity, ask for it:

```python
lexical_diversity("some text", unit="surface")   # fine
```

## `lix()` refused my token list

```python
lix(tokens)   # TypeError: B cannot be recovered from a token list
```

The number of sentences is not derivable from a bag of tokens. Pass it:

```python
lix(tokens, sentences=24)
```

## My scores changed after I switched Unicode normalisation

They would have. `length_policy` defaults to `"nfc"` precisely so they do not: decomposed
input otherwise inflates every word by two or three characters, pushing essentially the
whole text over any threshold. If you need raw code points — to reproduce a published
figure, say — ask for them explicitly with `length_policy="codepoints"`, and the result
will record that you did.

## Which token stream do the downstream projects use?

- **Homer** (`gold_lemmas.parquet`): `form` → `lix`, `lemma` → `lexical_diversity`. The
  treebank drops punctuation, so *B* has to be supplied explicitly — verse lines are the
  usual choice, comparable within the corpus but not to prose.
- **music_networks** (`SongDoc`): `.text` → `lix`, `.tokens` → `lexical_diversity`. **Never
  the reverse.** `SongDoc.tokens` is content lemmas only, stop-word-stripped, lowercased,
  with n-grams glued into single tokens like `nagy_szerelem` — lossy in all four ways that
  matter for word length.
