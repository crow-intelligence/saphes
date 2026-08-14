# Calibration data

The measurements behind the shipped Hungarian threshold. Produced by
`experiments/lix_calibration/`; the full record, including every threshold from 0 to 20, is
in that directory's `results/lix_calibration.json`.

Method: token-weighted, minimum frequency 5, NFC length policy, capitalisation marker
stripped and merged before filtering.

## Cumulative long-word shares

Share of running tokens strictly longer than each threshold.

| >T | MOKK 4% | MOKK 8% | MOKK full | Leipzig HU | Leipzig SV |
|---:|---:|---:|---:|---:|---:|
| 4 | 64.00% | 63.49% | 61.14% | 62.24% | 46.98% |
| 5 | 53.98% | 53.16% | 50.55% | 51.87% | 35.37% |
| 6 | 44.52% | 43.44% | 40.74% | 41.68% | 25.65% |
| 7 | 35.38% | 34.24% | 31.60% | 31.92% | 18.60% |
| 8 | 27.33% | 26.20% | 23.75% | 23.43% | 13.00% |
| 9 | 19.83% | 18.88% | 16.87% | 16.34% | 8.78% |
| 10 | 13.85% | 13.05% | 11.50% | 10.84% | 5.97% |
| 12 | 5.79% | 5.39% | 4.63% | 4.02% | 2.70% |

| curve | tokens | mean length |
|---|---:|---:|
| `mokk-4pct` | 554,861,558 | 6.240 |
| `mokk-8pct` | 870,983,275 | 6.161 |
| `mokk-full` | 1,360,685,516 | 5.963 |
| `leipzig-hun` | 15,786,586 | 5.937 |
| `leipzig-swe` | 14,284,223 | 5.052 |

## The recommendation

```pycon
>>> from saphes import recommended_threshold
>>> hu = recommended_threshold("hu")
>>> hu.threshold, hu.bracket
(8, (8, 9))
>>> round(hu.matched_share, 4), round(hu.reference_share, 4)
(0.2733, 0.2565)
>>> round(hu.residual, 4), hu.runner_up, round(hu.runner_up_residual, 4)
(0.0168, 9, 0.0582)
>>> hu.is_boundary
False

```

Every curve, matched independently against the same Swedish reference, chose the same
threshold:

```pycon
>>> for source, threshold in hu.agreement:
...     print(f"{source:<32} {threshold}")
leipzig-hun                      8
mokk-4pct                        8
mokk-4pct-asterisk-dropped       8
mokk-4pct-digraphs-collapsed     8
mokk-8pct                        8
mokk-full                        8

```

## Sensitivity

Two variants, computed so the cost of each methodological choice is visible.

| >T | correct (strip and merge `*`) | naive (discard starred) | digraphs collapsed |
|---:|---:|---:|---:|
| 6 | 44.52% | 45.94% | 41.51% |
| 7 | 35.38% | 36.57% | 32.71% |
| 8 | 27.33% | 28.33% | 24.40% |
| 9 | 19.83% | 20.60% | 17.30% |

The MOKK lists mark capitalised, mostly sentence-initial forms with a trailing asterisk.
`A*` alone is 8.9 million tokens in the 4% stratum. Discarding those rows biases the mean
length upward, because they are overwhelmingly short function words. It happens not to change
the answer here.

## Validation against running text

From a Webcorpus crawl part, the only source with real sentence boundaries — so *A*, *B* and
*C* all come from the corpus.

| threshold | *A* | *B* | long-word share | LIX |
|---|---:|---:|---:|---:|
| Björnsson's 6 | 10,275,343 | 709,274 | 45.89% | 60.38 |
| calibrated 8 | 10,275,343 | 709,274 | 28.93% | 43.41 |

The calibration predicted a 27.33% share; this running text gives 28.93%.

## Sources

- Halácsy, Kornai, Németh, Rung, Szakadát, Trón (2004). *Creating open language resources for
  Hungarian.* LREC.
- Kornai, Halácsy, Nagy, Oravecz, Trón, Varga (2006). *Web-based frequency dictionaries for
  medium density languages.* Web as Corpus, ACL.
- Goldhahn, Eckart, Quasthoff (2012). *Building large monolingual dictionaries at the Leipzig
  Corpora Collection.* LREC.

## See also

- [Reproduce the calibration study](../how-to/reproduce-the-calibration.md)
- [Why the threshold moves](../explanation/why-the-threshold-moves.md)
