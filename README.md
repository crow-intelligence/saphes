<p align="center">
  <img src="https://raw.githubusercontent.com/crow-intelligence/saphes/main/img/saphes_logo.png" alt="saphes logo" width="480">
</p>

# saphes

Readability and lexical diversity — two metrics, done carefully, with the parameters other
implementations hardcode.

*saphes* — σαφής, "clear, plain, distinct". Aristotle makes clarity the chief virtue of λέξις
(style); the other classical axis is ποικιλία, variety. The two metrics here are exactly those
axes: **LIX measures clarity, TTR measures variety.**

## Why this exists

`textstat`, `textdescriptives`, `lexicalrichness` and `taaled` already cover this ground. Two
reasons to still build it:

1. **The LIX long-word threshold is hardcoded at 6 everywhere.** That 6 comes from Björnsson's
   Swedish original, and it is wrong for the languages we work on. Hungarian is agglutinative
   and Ancient Greek heavily inflected, so at threshold 6 nearly every token counts as "long"
   and the index saturates into a flat line. Measured over the full Hungarian Webcorpus,
   **44.5% of running tokens are "long" at threshold 6**, against **25.7%** in Swedish. On
   real Hungarian prose that pushes LIX to 60.4 — "very difficult" — where the calibrated
   threshold gives 43.4. Parameterising the threshold is the whole point.
2. **Implementations disagree.** They count words, sentences and long words differently, so
   they rank the same texts differently. So: expose the counts, document every choice, make
   results auditable.

Non-goal: becoming another kitchen-sink readability library.

## Installation

```
uv add saphes
```

The core has **no dependencies** — plain Python and the standard library.

## Quickstart

```python
from saphes import lix, lexical_diversity

# LIX takes SURFACE FORMS. Word length is the signal.
result = lix("The cat sat on it. Complicated sentences generally frighten us.")
result.score            # 45.0
result.words, result.sentences, result.long_words   # (10, 2, 4)  -> A, B, C
result.band             # 'standard'

# Raise the threshold for inflected languages, where 6 saturates.
hu = "A gyermekeknek megmutatták a településeken található nevezetességeket. Elutaztak."
lix(hu).score                                  # 79.0 — an ordinary sentence, "very difficult"
lix(hu).long_word_share                        # 0.75 — three words in four are "long"
lix(hu, long_word_threshold=9).score           # 54.0 — discrimination restored
lix(hu, long_word_threshold=9).long_word_share # 0.50

# Or use the calibrated default, with its provenance attached.
from saphes import recommended_threshold
rec = recommended_threshold("hu")
rec.threshold        # 8
rec.matched_share    # 0.273 — against Swedish 0.257 at threshold 6
lix(hu, long_word_threshold=int(rec))

# Diversity takes LEMMAS, and `unit` is required — no default.
lexical_diversity(["ház", "kutya", "ház"], unit="lemma")

# Comparing texts of different lengths? Use MATTR, not TTR.
lexical_diversity(lemmas, unit="lemma", window=100).mattr
```

## The data contract

The single most important thing in this package: **the two metrics require opposite token
streams.**

| Metric | Required input | Why |
|---|---|---|
| `lexical_diversity` | **lemmas** | Surface variation is *noise* — it measures morphology, not vocabulary. Hungarian `ház / házak / házban / házakat` is four types and one lemma. |
| `lix` | **surface forms** | Word length *is* the signal. `házakban` is 8 characters; its lemma `ház` is 3. Lemmatising erases the measurement. |

Feed the same list to both and exactly one of them is silently wrong — no error, no NaN, just
a plausible number. Four guards exist against that:

- `unit` is a **required** keyword on `lexical_diversity`, with no default.
- The parameter names differ: `lemmas=` versus `words=`. Crossing them raises.
- A raw string is **refused** by `lexical_diversity` unless you pass `unit="surface"`, since a
  string can only ever yield surface forms.
- Every result records the `unit` it measured, so any serialised table says which stream
  produced each number.

**saphes consumes lemmas; it does not produce them.** Lemmatisation is language-specific and
heavy — CLTK or a treebank for Greek, huspacy for Hungarian. The caller lemmatises; saphes
measures.

## Features

- **`lix(...)`** — the readability index, with `long_word_threshold` as a first-class
  parameter. A long word is `len(word) > threshold`, so the default 6 means **seven letters or
  more**, per Björnsson's "more than six letters".
- **Three ways to supply the sentence count *B*** — segmented from raw text with a pluggable
  splitter, pre-split, or an explicit integer. Neither a treebank that drops punctuation nor a
  spaCy pipeline with the parser disabled can give you sentences, so the explicit path is not
  a corner case. The result records which was used.
- **`lexical_diversity(...)`** — TTR and MATTR, with the token unit declared and recorded.
- **`mattr(tokens, window=100)`** — the length-corrected moving average, as a bare float, for
  drop-in use.
- **Calibrated thresholds, with their provenance.** `recommended_threshold("hu")` returns the
  empirically matched threshold *and* the shares behind it, the runner-up, which of six
  independently computed curves agreed, and the caveats. The number ships; the corpus does
  not. The study is in `experiments/lix_calibration/`.
- **Counts, not just scores.** Every function returns *A*, *B*, *C* (or types and tokens) plus
  every parameter used and the saphes version. A bare float is unauditable.
- **Explicit length policy.** Decomposed Unicode otherwise inflates every word length, which
  hits polytonic Greek and accented Hungarian hardest. `length_policy` defaults to NFC
  normalisation and can be swapped for grapheme counting, raw code points, or your own
  callable.

> [!WARNING]
> **TTR is inversely related to text length.** TTR values from texts of different lengths are
> **not comparable** — a raw TTR over corpora of different sizes mostly ranks them by size.
> This matters directly for per-decade and per-book work, where lengths always differ. Pass
> `window=` and read `.mattr` instead.

## Documentation

Full docs at [saphes.readthedocs.io](https://saphes.readthedocs.io); sources in `docs/`.
Worked examples live in `examples/` and are included in the docs verbatim, so they cannot
drift.

## Roadmap

- [x] LIX with a parameterised long-word threshold
- [x] TTR and MATTR with a required, recorded token unit
- [x] RIX (long words per sentence)
- [x] Empirically calibrated per-language thresholds, from token-weighted word-length
      distributions — Hungarian ships as `recommended_threshold("hu")`
- [ ] The same study for Ancient Greek, for the Homer project
- [ ] POS-filtered diversity, once lemmas carry tags
- [ ] MTLD, HD-D, vocd-D, Maas

**Maintenance**

- [x] Logo and README banner
- [ ] Mutation-testing baseline

Explicitly out of scope: Flesch, Kincaid, SMOG and relatives. They need syllabification, which
is language-specific and a different project. LIX was chosen precisely because it needs only
word length and sentence count, so it travels across languages.

## Made by

saphes is made by [Crow Intelligence](https://crowintelligence.org/).

## License

MIT
