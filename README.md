<p align="center">
  <img src="https://raw.githubusercontent.com/crow-intelligence/saphes/main/img/saphes_logo.png" alt="saphes logo" width="480">
</p>

# saphes

Readability, lexical diversity, syntactic complexity and loan-word ratio — a small set of
metrics, done carefully, with the parameters other implementations hardcode.

*saphes* — σαφής, "clear, plain, distinct". Aristotle makes clarity the chief virtue of λέξις
(style); the other classical axis is ποικιλία, variety. The package began as exactly those two
axes — **LIX measures clarity, TTR measures variety** — and has since grown a third,
**how hard a sentence is to hold in your head**, and a fourth, **how much of the vocabulary
is still felt as foreign**.

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

The core has **no dependencies** — plain Python and the standard library. Two optional
extras stay out of the core path: `saphes[snowball]` for Hungarian stemming and
`saphes[punkt]` for the NLTK sentence splitter.

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

Hungarian needs three things English does not — a retuned threshold, a letter count, and a
stand-in for a lemmatiser:

```python
from saphes import hungarian_letter_count, hungarian_stems, lix, recommended_threshold

# `sz` is one letter, not two characters. The threshold is calibrated per policy.
hu = recommended_threshold("hu-letters")          # 8, not Björnsson's Swedish 6
lix(text, length_policy=hungarian_letter_count, long_word_threshold=int(hu))

# No lemmatiser? Snowball is the fallback, declared as its own unit.
lexical_diversity(hungarian_stems(tokens), unit="stem")
```

### Syntactic complexity, from any parser

```python
from saphes import from_conllu, mean_dependency_distance, mean_hierarchical_distance

parses = from_conllu(open("corpus.conllu").read())
mdd = mean_dependency_distance(parses, parser="emtsv tok-dep-conll")
mhd = mean_hierarchical_distance(parses, parser="emtsv tok-dep-conll")
print(mdd.mdd, mhd.mhd)
```

`from_spacy` takes a HuSpaCy or spaCy `Doc` and imports neither. **Record `parser=`:** a
parser carries the annotation convention of the treebank it was trained on, and that
convention decides which word is the head — which is the whole input to a distance measure.

### Loan words

```python
from pathlib import Path
from saphes import loanword_ratio

lexicon = set(Path("idegenszavak.txt").read_text(encoding="utf-8").split())
print(loanword_ratio(lemmas, lexicon=lexicon).ratio)
```

saphes ships no lexicon in the package; `lexicon` is required. A 15,203-lemma Hungarian list
lives in `experiments/loanwords/results/`.

## The data contract

Each metric wants a **different** input, and two of them want opposites.

| Metric | Wants | Because |
|---|---|---|
| `lix`, `rix` | **surface forms** | Word length *is* the signal. `házakban` is 8 characters; its lemma `ház` is 3. |
| `lexical_diversity` | **lemmas** | Surface variation is *noise* — it measures morphology, not vocabulary. Hungarian `ház / házak / házban / házakat` is four types and one lemma. |
| `loanword_ratio` | **lemmas** | Morphology buries the root. `komputerekkel` misses a lexicon holding `komputer`. |
| `mean_dependency_distance`, `mean_hierarchical_distance` | **a parse** | Head indices. No tokeniser produces them; they come from a parser, via `saphes.adapters`. |

Feed the same list to the first two and exactly one is silently wrong — no error, no NaN,
just a plausible number. `unit` is required, the parameter names differ (`words=` against
`lemmas=` against `parses=`), a raw string is refused where it could only be wrong, and
every result records what it measured.

**saphes consumes lemmas; it does not produce them.** Lemmatisation is language-specific and
heavy — CLTK or a treebank for Greek, huspacy for Hungarian. The caller lemmatises; saphes
measures.

The one exception is optional and honest about itself: `saphes[snowball]` gives Hungarian
Snowball stemming for callers with no lemmatiser. Its output is declared as `unit="stem"`, a
third stream with its own name, because a stemmer both over- and under-merges and a
stem-based number is comparable only to another from the same stemmer.

## Documentation

[saphes.readthedocs.io](https://saphes.readthedocs.io), organised by
[Diátaxis](https://diataxis.fr/):

- **[Tutorial](https://saphes.readthedocs.io/en/latest/tutorial/first-measurement/)** — new
  here? Measure your first text in about ten minutes, with nothing to download.
- **[How-to guides](https://saphes.readthedocs.io/en/latest/how-to/install/)** — measure
  Hungarian text, pass a HuSpaCy doc or emtsv stream, customise the loan-word lexicon, supply
  a sentence count, count letters rather than characters, stem without a lemmatiser,
  calibrate a threshold.
- **[Reference](https://saphes.readthedocs.io/en/latest/reference/)** — every function, its
  contract and its failure modes, plus the calibration data.
- **[Explanation](https://saphes.readthedocs.io/en/latest/explanation/two-token-streams/)** —
  why the metrics need different input, what dependency distance measures, why loan words
  need lemmas, why the threshold has to move, and why implementations disagree.

Every code block in the docs is executed by CI, so nothing there can drift.

## Roadmap

- [x] LIX with a parameterised long-word threshold
- [x] TTR and MATTR with a required, recorded token unit
- [x] RIX (long words per sentence)
- [x] Empirically calibrated per-language thresholds, from token-weighted word-length
      distributions — Hungarian ships as `recommended_threshold("hu")`
- [x] Phonotactically aware Hungarian letter counting — `sz` is one letter, `ssz` is two, and
      morpheme boundaries are handled by rule plus an attested table
- [x] Optional Snowball stemming for callers with no lemmatiser, as a declared third unit
- [x] Mean dependency distance and mean hierarchical distance, from any parser's output
- [x] Zero-dependency adapters for HuSpaCy/spaCy and CoNLL-U/emtsv
- [x] Loan-word ratio (*idegenszó-arány*) against a caller-supplied lexicon
- [ ] A public-domain Hungarian loan-word lexicon to ship with it
- [ ] The same study for Ancient Greek, for the Homer project
- [ ] POS-filtered diversity, once lemmas carry tags
- [ ] MTLD, HD-D, vocd-D, Maas

**Research**

- [ ] **Diachronic analysis:** test MDD and loan word density changes on the ParlaMonitor
      corpus across time
- [ ] **Data diversity benchmarking:** benchmark MDD and idegenszó-arány across diverse
      Hungarian registers (Webcorpus, legal texts, literary prose, social media)
- [ ] **Multilingual scaling:** test the agnostic MDD calculation engine on Universal
      Dependencies corpora across multiple languages
- [ ] **Dependency motifs:** chain motif identification for advanced cognitive load
      mapping, extending the MDD/MHD pair (Jing & Liu 2017)

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
