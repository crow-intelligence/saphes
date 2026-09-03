# Findings: LIX across Hungarian registers

Generated: 2026-08-29T17:37:52+00:00  
saphes version: 0.1.0  
Window: 25 sentences; limit 300,000 per register

---

## 1. The panel

| register | tier | B from | thr | policy | A/B | C/A | LIX | p10 | p50 | p90 |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|
| `leipzig-swe-news` | public | corpus | 6 | chars | 15.37 | 0.2707 | **42.44** | 34.0 | 42.8 | 50.2 |
| `leipzig-hun-news` | public | corpus | 6 | chars | 18.30 | 0.4454 | **62.84** | 55.9 | 63.1 | 69.3 |
| `leipzig-hun-news` | public | corpus | 8 | chars | 18.30 | 0.2665 | **44.94** | 38.4 | 45.0 | 51.4 |
| `leipzig-hun-news` | public | corpus | 8 | letters | 18.30 | 0.2381 | **42.11** | 35.6 | 42.2 | 48.4 |
| `parlamonitor` | author-local | corpus | 6 | chars | 18.21 | 0.4138 | **59.59** | 50.9 | 59.4 | 68.8 |
| `parlamonitor` | author-local | corpus | 8 | chars | 18.21 | 0.2564 | **43.85** | 35.6 | 43.5 | 52.5 |
| `parlamonitor` | author-local | corpus | 8 | letters | 18.21 | 0.2288 | **41.09** | 32.5 | 40.8 | 49.8 |
| `kmdb` | author-local | segmented | 6 | chars | 22.64 | 0.4391 | **66.55** | 57.5 | 66.5 | 74.9 |
| `kmdb` | author-local | segmented | 8 | chars | 22.64 | 0.2673 | **49.36** | 40.9 | 49.1 | 57.4 |
| `kmdb` | author-local | segmented | 8 | letters | 22.64 | 0.2407 | **46.71** | 38.4 | 46.4 | 54.6 |
| `lyrics` | author-local | segmented | 6 | chars | 17.56 | 0.2237 | **39.93** | 25.5 | 36.7 | 57.5 |
| `lyrics` | author-local | segmented | 8 | chars | 17.56 | 0.0811 | **25.67** | 13.1 | 21.9 | 42.4 |
| `lyrics` | author-local | segmented | 8 | letters | 17.56 | 0.0600 | **23.56** | 11.3 | 19.6 | 40.2 |

---

## 2. Band mapping

Each Swedish band boundary, and the Hungarian score that sits at the same point of the distribution. A small shift means the shipped labels transfer at the calibrated threshold; a large one means Hungarian needs its own.

**Length policy: chars**

| band | Swedish boundary | share below | Hungarian boundary | shift |
|---|---:|---:|---:|---:|
| very easy | 30 | 3.4% | 35.45 | +5.45 |
| easy | 40 | 33.9% | 42.95 | +2.95 |
| standard | 50 | 89.2% | 51.16 | +1.16 |
| difficult | 60 | 100.0% | 61.60 | +1.60 |

**Length policy: letters**

| band | Swedish boundary | share below | Hungarian boundary | shift |
|---|---:|---:|---:|---:|
| very easy | 30 | 3.4% | 32.63 | +2.63 |
| easy | 40 | 33.9% | 40.18 | +0.18 |
| standard | 50 | 89.2% | 48.19 | -1.81 |
| difficult | 60 | 100.0% | 59.22 | -0.78 |

---

## 3. Stability across window lengths

The same mapping recomputed at other window lengths. A boundary that moves with the window is telling you about the window, not about Hungarian.

**Length policy: chars**

| window | very easy | easy | standard | difficult |
|---:|---:|---:|---:|---:|
| 10 | 34.91 | 42.74 | 51.42 | 61.25 |
| 25 | 35.45 | 42.95 | 51.16 | 61.60 |
| 50 | 35.67 | 43.04 | 50.98 | 61.56 |
| 100 | 35.73 | 43.10 | 50.98 | 56.78 |

**Length policy: letters**

| window | very easy | easy | standard | difficult |
|---:|---:|---:|---:|---:|
| 10 | 32.32 | 39.94 | 48.40 | 57.99 |
| 25 | 32.63 | 40.18 | 48.19 | 59.22 |
| 50 | 33.00 | 40.25 | 47.95 | 59.32 |
| 100 | 32.94 | 40.37 | 47.99 | 54.29 |

---

## 4. Caveats

- Leipzig sentence collections are sampled and deduplicated, so there are no documents. Both LIX terms are ratios, so the point estimates are unbiased, but a window of shuffled sentences is more homogeneous than a real text and its spread is correspondingly too narrow.
- The window length of 25 sentences is a choice, not a measurement. It changes the spread and therefore the mapped boundaries; the stability check is in the findings.
- Registers marked author-local are not redistributable and this panel cannot be reproduced for them from a clean checkout. Their numbers are published; their corpora are not.
- A register whose sentence count is marked segmented had its B produced by the bundled splitter rather than by the corpus. LIX implementations disagree mostly on B, so those rows are not directly comparable with the corpus-supplied ones.

---

## 5. Reproducing

```bash
uv run python experiments/lix_registers/scripts/run.py --tier1-only
uv run python experiments/lix_registers/scripts/run.py
```

The first form uses only corpora `download_data.py` fetches, and is what a clean checkout can run.
