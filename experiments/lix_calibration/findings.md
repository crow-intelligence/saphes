# Findings: LIX threshold calibration for Hungarian
Generated: 2026-09-03T13:07:57+00:00  
Primary source: web2.2-freq-sorted.txt.gz  
saphes version: 0.1.0

---

## 1. Headline result

**Recommended Hungarian `long_word_threshold`: 8**  
Bracket: (8, 9)  
Matched share: 27.33% against a Swedish reference of 25.65% at threshold 6  
Residual: 0.0168

Björnsson's threshold of 6 selects 25.65% of running Swedish tokens. In Hungarian the same threshold selects 44.52% — the index saturates, and differences between texts stop showing up. Threshold 8 restores what the term means: the longest quarter or so of running words.

The nearest alternative, threshold 9, misses by 0.0582 against the winner's 0.0168 — a factor of 3.5. The choice is not on a knife edge.

---

## 2. Cumulative long-word shares

Token-weighted share of running words strictly longer than each threshold.

| curve | >4 | >5 | >6 | >7 | >8 | >9 | >10 | >11 | >12 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `leipzig-hun` | 62.24% | 51.87% | 41.68% | 31.92% | 23.43% | 16.34% | 10.84% | 6.81% | 4.02% |
| `leipzig-hun-letters` | 60.42% | 49.16% | 38.40% | 29.43% | 20.68% | 14.01% | 8.87% | 5.32% | 3.00% |
| `leipzig-swe` | 46.98% | 35.37% | 25.65% | 18.60% | 13.00% | 8.78% | 5.97% | 3.90% | 2.70% |
| `mokk-4pct` | 64.00% | 53.98% | 44.52% | 35.38% | 27.33% | 19.83% | 13.85% | 9.16% | 5.79% |
| `mokk-4pct-asterisk-dropped` | 65.48% | 55.50% | 45.94% | 36.57% | 28.33% | 20.60% | 14.42% | 9.55% | 6.04% |
| `mokk-4pct-asterisk-dropped-letters` | 63.66% | 52.69% | 42.88% | 33.85% | 25.33% | 18.03% | 12.16% | 7.77% | 4.72% |
| `mokk-4pct-digraphs-collapsed` | 62.19% | 51.16% | 41.51% | 32.71% | 24.40% | 17.30% | 11.66% | 7.44% | 4.51% |
| `mokk-4pct-letters` | 62.19% | 51.17% | 41.52% | 32.71% | 24.41% | 17.31% | 11.67% | 7.45% | 4.51% |
| `mokk-8pct` | 63.49% | 53.16% | 43.44% | 34.24% | 26.20% | 18.88% | 13.05% | 8.59% | 5.39% |
| `mokk-8pct-letters` | 61.66% | 50.28% | 40.45% | 31.60% | 23.34% | 16.45% | 10.98% | 6.96% | 4.17% |
| `mokk-full` | 61.14% | 50.55% | 40.74% | 31.60% | 23.75% | 16.87% | 11.50% | 7.49% | 4.63% |
| `mokk-full-letters` | 59.44% | 47.90% | 38.09% | 29.24% | 21.25% | 14.78% | 9.75% | 6.10% | 3.60% |

| curve | tokens | types | mean length |
|---|---:|---:|---:|
| `leipzig-hun` | 15,786,586 | 151,296 | 5.937 |
| `leipzig-hun-letters` | 15,786,586 | 151,296 | 5.681 |
| `leipzig-swe` | 14,284,223 | 89,887 | 5.052 |
| `mokk-4pct` | 554,861,558 | 1,422,686 | 6.240 |
| `mokk-4pct-asterisk-dropped` | 517,267,619 | 1,392,317 | 6.372 |
| `mokk-4pct-asterisk-dropped-letters` | 517,267,619 | 1,392,317 | 6.093 |
| `mokk-4pct-digraphs-collapsed` | 554,861,558 | 1,422,686 | 5.967 |
| `mokk-4pct-letters` | 554,861,558 | 1,422,686 | 5.968 |
| `mokk-8pct` | 870,983,275 | 2,007,713 | 6.161 |
| `mokk-8pct-letters` | 870,983,275 | 2,007,713 | 5.893 |
| `mokk-full` | 1,360,685,516 | 3,023,270 | 5.963 |
| `mokk-full-letters` | 1,360,685,516 | 3,023,270 | 5.725 |

---

## 3. Which threshold each source would choose

Every curve matched independently against the same Swedish reference.

| curve | threshold |
|---|---:|
| `leipzig-hun` | 8 |
| `mokk-4pct` | 8 |
| `mokk-4pct-asterisk-dropped` | 8 |
| `mokk-4pct-digraphs-collapsed` | 8 |
| `mokk-4pct-letters` | 8 |
| `mokk-8pct` | 8 |
| `mokk-full` | 8 |

These are the character-policy curves — the panel behind `hu`. The letter policy has its own panel, in section 5, measured under that policy rather than borrowed from this one.

---

## 4. Sensitivity

**Stratum.** `mokk-4pct` is the principled choice — the 4% stratum has fewer mistakes than an average print document, while the full-corpus column carries the crawl's junk. The 8% and full columns are shown so the cost of that choice is visible rather than assumed.

**Capitalisation marker.** `mokk-4pct-asterisk-dropped` shows what happens if the trailing `*` on sentence-initial forms is treated as part of the word and those rows discarded. They are overwhelmingly short function words, so dropping them biases the mean length upward and picks too high a threshold. This is the single highest-consequence line in the reader.

**Digraphs.** Hungarian `cs, dz, gy, ly, ny, sz, ty, zs, dzs` are single letters, so a character count is not a letter count, and two rows recompute on letters. `mokk-4pct-digraphs-collapsed` is the naive version — replace each digraph with its first character — kept because it is what earlier releases shipped. It over-merges twice over: the replacement cascades, so `vízszint` comes out at six letters when it is seven, and it mis-fires at morpheme boundaries, where `község` is `köz` + `ség` and its `zs` is not the digraph at all. `mokk-4pct-letters` is the scanner in `saphes.hungarian`, which fixes both. The two differ by about 0.01 percentage points, which is the whole measured cost of knowing where morpheme boundaries are, and neither moves the threshold. Character counting stays the default for `lix`, as in Björnsson's original; the letter policy ships its own calibration under `hu-letters` (section 5).

**Independent corpus.** `leipzig-hun` is a different corpus entirely — 2022 news rather than a 2003 web crawl, built by a different project with a different pipeline. That it lands close to `mokk-4pct` is the strongest evidence here that the saturation is a property of Hungarian rather than an artifact of the Webcorpus.

---

## 5. The same match, on letters

A threshold is calibrated against a way of counting letters, so the letter policy gets a calibration of its own rather than borrowing the character one. The Swedish reference is unchanged: Swedish has no multi-character letters, so its character count already is a letter count.

**`hu-letters` `long_word_threshold`: 8**  
Bracket: (7, 8)  
Matched share: 24.41% against the Swedish 25.65% at 6  
Residual: 0.0124  
Runner-up: 7 (residual 0.0706)

Same threshold as `hu`, different share behind it. That is the point of shipping both keys: pairing a threshold with the wrong length policy measures something neither calibration measured.

| curve | threshold |
|---|---:|
| `leipzig-hun-letters` | 7 |
| `mokk-4pct-asterisk-dropped-letters` | 8 |
| `mokk-4pct-letters` | 8 |
| `mokk-8pct-letters` | 8 |
| `mokk-full-letters` | 7 |

3 of 5 curves choose 8; the rest choose [7]. That is weaker support than the character policy's panel in section 3, and it is recorded rather than borrowed from it. The winning residual is nonetheless the smaller of the two, so the disagreement is between curves rather than within the primary one — read the bracket, not just the winner.

---

## 6. Caveats

- The MOKK Webcorpus crawl is from winter 2003: 2000s web Hungarian, not song lyrics, not literary prose. A general-language reference, not a register match.
- Register matters for readability. Before trusting this threshold on your own texts, recompute the long-word share on a sample of them and check it lands where the calibration predicts.
- A calibrated threshold is a default, not a truth. The parameter stays exposed precisely because no single number is right everywhere.

---

## 7. Sources and citations

**hu_crosscheck** — `leipzig-hun_news_2022_1M` (`hun_news_2022_1M.tar.gz`)
  - 242,152,696 bytes, sha256 `60b78adfdb462353…`
  - Goldhahn, Eckart, Quasthoff (2012). Building large monolingual dictionaries at the Leipzig Corpora Collection. LREC.

**hu_primary** — `mokk-web2.2-4pct` (`web2.2-freq-sorted.txt.gz`)
  - 120,512,445 bytes, sha256 `3221f4a8a682a044…`
  - Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). Creating open language resources for Hungarian. LREC.
  - Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). Web-based frequency dictionaries for medium density languages. Web as Corpus, ACL.

**sv_reference** — `leipzig-swe_news_2022_1M` (`swe_news_2022_1M.tar.gz`)
  - 191,328,913 bytes, sha256 `a39c02c421590a21…`
  - Goldhahn, Eckart, Quasthoff (2012). Building large monolingual dictionaries at the Leipzig Corpora Collection. LREC.

---

## 8. Reproducing

```bash
uv run python experiments/lix_calibration/scripts/download_data.py
uv run python experiments/lix_calibration/scripts/run.py
```

The run asserts a set of regression anchors measured by hand before this script existed; if the reader ever starts producing different numbers it fails rather than quietly publishing them.
