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

# LIX takes SURFACE FORMS — word length is the signal.
result = lix("The cat sat on it. Complicated sentences generally frighten us.")
result.score                                       # 45.0
result.words, result.sentences, result.long_words  # (10, 2, 4)  -> A, B, C
result.band                                        # 'standard'

# Diversity takes LEMMAS, and `unit` is required — there is no default.
lexical_diversity(lemmas, unit="lemma")

# Comparing texts of different lengths? Use MATTR, not TTR.
lexical_diversity(lemmas, unit="lemma", window=100).mattr
```

## The data contract

The two metrics require **opposite** token streams.

| Metric | Wants | Because |
|---|---|---|
| `lexical_diversity` | **lemmas** | Surface variation is *noise* — it measures morphology, not vocabulary. Hungarian `ház / házak / házban / házakat` is four types and one lemma. |
| `lix` | **surface forms** | Word length *is* the signal. `házakban` is 8 characters; its lemma `ház` is 3. |

Feed the same list to both and exactly one is silently wrong — no error, no NaN, just a
plausible number. `unit` is required, the parameter names differ, a raw string is refused
where it could only be wrong, and every result records what it measured.

**saphes consumes lemmas; it does not produce them.** Lemmatisation is language-specific and
heavy — CLTK or a treebank for Greek, huspacy for Hungarian. The caller lemmatises; saphes
measures.

## Documentation

[saphes.readthedocs.io](https://saphes.readthedocs.io), organised by
[Diátaxis](https://diataxis.fr/):

- **[Tutorial](https://saphes.readthedocs.io/en/latest/tutorial/first-measurement/)** — new
  here? Measure your first text in about ten minutes, with nothing to download.
- **[How-to guides](https://saphes.readthedocs.io/en/latest/how-to/install/)** — supply a
  sentence count, compare texts of different lengths, calibrate a threshold, diagnose a
  surprise.
- **[Reference](https://saphes.readthedocs.io/en/latest/reference/)** — every function, its
  contract and its failure modes, plus the calibration data.
- **[Explanation](https://saphes.readthedocs.io/en/latest/explanation/two-token-streams/)** —
  why the two metrics need opposite input, why the threshold has to move, and why
  implementations disagree.

Every code block in the docs is executed by CI, so nothing there can drift.

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
