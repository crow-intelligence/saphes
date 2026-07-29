# LIX quickstart

## What it shows

1. That the counts *A*, *B* and *C* travel with the score, so any LIX figure can be checked.
2. What the `long_word_threshold` parameter actually does to the long-word share and the
   score, swept across values.
3. That Björnsson's interpretation bands stop applying once the threshold moves.
4. All three ways of supplying the sentence count *B*, and how each is recorded.

## Run it

```bash
uv run python examples/lix_quickstart.py
```

```text
=== The counts travel with the score ===
  A (words)     = 49
  B (sentences) = 4   [segmented]
  C (long words)= 20   [threshold 6]
  LIX = A/B + 100*C/A = 12.25 + 40.82 = 53.07
  band: difficult
  length policy: nfc

=== Sweeping the threshold ===
  threshold   EN share   EN LIX   HU share   HU LIX
          5     53.1%    65.31     46.3%    59.80
          6     40.8%    53.07     44.4%    57.94
          7     34.7%    46.94     37.0%    50.54
          8     22.4%    34.70     33.3%    46.83
          9     14.3%    26.54     24.1%    37.57
         10     12.2%    24.49     20.4%    33.87
         12      2.0%    14.29      9.3%    22.76

=== Bands only mean anything at threshold 6 ===
  score at threshold 9: 37.57
  band:                 None
  interpret_lix anyway: 'easy'

=== Three ways to supply B ===
      segmented: B=4  LIX= 53.07  recorded as 'segmented'
   presegmented: B=2  LIX= 65.32  recorded as 'presegmented'
       explicit: B=4  LIX= 53.07  recorded as 'explicit'
```

## Source

```python
--8<-- "examples/lix_quickstart.py"
```
