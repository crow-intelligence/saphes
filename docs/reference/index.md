# API overview

::: saphes
    options:
      members: false

## The modules

| Module | What is in it |
|---|---|
| [`readability`](readability.md) | `lix`, `rix`, `lix_from_counts`, `word_length`, `interpret_lix`, `LIX_BANDS` |
| [`diversity`](diversity.md) | `lexical_diversity`, `ttr_from_counts`, `mattr` |
| [`segment`](segment.md) | `words`, `sentences` — the dependency-free splitters |
| [`hungarian`](hungarian.md) | `hungarian_letters`, `hungarian_letter_count`, the boundary table |
| [`stem`](stem.md) | `hungarian_stems` — optional, behind the `snowball` extra |
| [`calibration`](calibration.md) | `recommended_threshold`, `length_curve`, `match_threshold` |
| [`datasets`](datasets.md) | The bundled EN/HU/GRC samples |

The data pages — [LIX bands](lix-bands.md), [calibration data](calibration-data.md),
[glossary](glossary.md) — carry the measured numbers and the vocabulary.
