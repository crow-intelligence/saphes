# Findings: LIX threshold calibration for Hungarian
Generated: 2026-07-29T17:08:25+00:00  
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
| `mokk-4pct` | 64.00% | 53.98% | 44.52% | 35.38% | 27.33% | 19.83% | 13.85% | 9.16% | 5.79% |
| `mokk-8pct` | 63.49% | 53.16% | 43.44% | 34.24% | 26.20% | 18.88% | 13.05% | 8.59% | 5.39% |
| `mokk-full` | 61.14% | 50.55% | 40.74% | 31.60% | 23.75% | 16.87% | 11.50% | 7.49% | 4.63% |
| `leipzig-hun` | 62.24% | 51.87% | 41.68% | 31.92% | 23.43% | 16.34% | 10.84% | 6.81% | 4.02% |
| `leipzig-swe` | 46.98% | 35.37% | 25.65% | 18.60% | 13.00% | 8.78% | 5.97% | 3.90% | 2.70% |
| `mokk-4pct-asterisk-dropped` | 65.48% | 55.50% | 45.94% | 36.57% | 28.33% | 20.60% | 14.42% | 9.55% | 6.04% |
| `mokk-4pct-digraphs-collapsed` | 62.19% | 51.16% | 41.51% | 32.71% | 24.40% | 17.30% | 11.66% | 7.44% | 4.51% |

| curve | tokens | types | mean length |
|---|---:|---:|---:|
| `mokk-4pct` | 554,861,558 | 1,422,686 | 6.240 |
| `mokk-8pct` | 870,983,275 | 2,007,713 | 6.161 |
| `mokk-full` | 1,360,685,516 | 3,023,270 | 5.963 |
| `leipzig-hun` | 15,786,586 | 151,296 | 5.937 |
| `leipzig-swe` | 14,284,223 | 89,887 | 5.052 |
| `mokk-4pct-asterisk-dropped` | 517,267,619 | 1,392,317 | 6.372 |
| `mokk-4pct-digraphs-collapsed` | 554,861,558 | 1,422,686 | 5.967 |

---

## 3. Which threshold each source would choose

Every curve matched independently against the same Swedish reference.

| curve | threshold |
|---|---:|
| `leipzig-hun` | 8 |
| `mokk-4pct` | 8 |
| `mokk-4pct-asterisk-dropped` | 8 |
| `mokk-4pct-digraphs-collapsed` | 8 |
| `mokk-8pct` | 8 |
| `mokk-full` | 8 |

---

## 4. Sensitivity

**Stratum.** `mokk-4pct` is the principled choice — the 4% stratum has fewer mistakes than an average print document, while the full-corpus column carries the crawl's junk. The 8% and full columns are shown so the cost of that choice is visible rather than assumed.

**Capitalisation marker.** `mokk-4pct-asterisk-dropped` shows what happens if the trailing `*` on sentence-initial forms is treated as part of the word and those rows discarded. They are overwhelmingly short function words, so dropping them biases the mean length upward and picks too high a threshold. This is the single highest-consequence line in the reader.

**Digraphs.** Hungarian `cs, dz, gy, ly, ny, sz, ty, zs, dzs` are single letters, so a character count is not a letter count. `mokk-4pct-digraphs-collapsed` recomputes on letters. It is a sensitivity check, not better ground truth: collapsing mis-fires at morpheme boundaries, where `község` is `köz` + `ség` and its `zs` is not the digraph. Character counting stays the default, as in Björnsson's original.

**Independent corpus.** `leipzig-hun` is a different corpus entirely — 2022 news rather than a 2003 web crawl, built by a different project with a different pipeline. That it lands close to `mokk-4pct` is the strongest evidence here that the saturation is a property of Hungarian rather than an artifact of the Webcorpus.

---

## 5. Caveats

- The MOKK Webcorpus crawl is from winter 2003: 2000s web Hungarian, not song lyrics, not literary prose. A general-language reference, not a register match.
- Register matters for readability. Before trusting this threshold on your own texts, recompute the long-word share on a sample of them and check it lands where the calibration predicts.
- A calibrated threshold is a default, not a truth. The parameter stays exposed precisely because no single number is right everywhere.

---

## 6. Sources and citations

**hu_primary** — `mokk-web2.2-4pct` (`web2.2-freq-sorted.txt.gz`)
  - 120,512,445 bytes, sha256 `3221f4a8a682a044…`
  - Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). Creating open language resources for Hungarian. LREC.
  - Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). Web-based frequency dictionaries for medium density languages. Web as Corpus, ACL.

**sv_reference** — `leipzig-swe_news_2022_1M` (`swe_news_2022_1M.tar.gz`)
  - 191,328,913 bytes, sha256 `a39c02c421590a21…`
  - Goldhahn, Eckart, Quasthoff (2012). Building large monolingual dictionaries at the Leipzig Corpora Collection. LREC.

**hu_crosscheck** — `leipzig-hun_news_2022_1M` (`hun_news_2022_1M.tar.gz`)
  - 242,152,696 bytes, sha256 `60b78adfdb462353…`
  - Goldhahn, Eckart, Quasthoff (2012). Building large monolingual dictionaries at the Leipzig Corpora Collection. LREC.

---

## 7. Reproducing

```bash
uv run python experiments/lix_calibration/scripts/download_data.py
uv run python experiments/lix_calibration/scripts/run.py
```

The run asserts a set of regression anchors measured by hand before this script existed; if the reader ever starts producing different numbers it fails rather than quietly publishing them.
