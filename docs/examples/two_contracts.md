# The two contracts

## What it shows

1. Both metrics computed the right way and the wrong way, on English, Hungarian and Ancient
   Greek.
2. That the error grows with the morphology of the language — small in English, large in
   Hungarian.
3. That both mistakes are silent: no error, no NaN, just a plausible number.
4. The three guards that make the mistake loud instead.

## Run it

```bash
uv run python examples/two_contracts.py
```

```text
Both mistakes are silent. No error, no NaN — just a plausible number.
The gap grows with the morphology of the language.

--- en (21 tokens) ---
  diversity   (wants LEMMAS)
    on lemmas   TTR = 0.6190   <- correct
    on surface  TTR = 0.7143   <- inflated by morphology
    gap         +0.0952
  readability (wants SURFACE FORMS)
    on surface  LIX =  35.57  <- correct
    on lemmas   LIX =  26.05  <- word length erased
    gap         +9.52
    mean word length: 4.48 surface vs 4.05 lemma

--- hu (14 tokens) ---
  diversity   (wants LEMMAS)
    on lemmas   TTR = 0.5714   <- correct
    on surface  TTR = 0.7143   <- inflated by morphology
    gap         +0.1429
  readability (wants SURFACE FORMS)
    on surface  LIX =  26.10  <- correct
    on lemmas   LIX =   4.67  <- word length erased
    gap         +21.43
    mean word length: 4.36 surface vs 3.00 lemma

--- grc (44 tokens) ---
  diversity   (wants LEMMAS)
    on lemmas   TTR = 0.8864   <- correct
    on surface  TTR = 0.9545   <- inflated by morphology
    gap         +0.0682
  readability (wants SURFACE FORMS)
    on surface  LIX =  44.21  <- correct
    on lemmas   LIX =  35.12  <- word length erased
    gap         +9.09
    mean word length: 5.02 surface vs 4.75 lemma

What stops you making the mistake:
  no unit           -> TypeError: lexical_diversity() missing 1 required keyword-only argument: 'unit'
  string as lemmas  -> TypeError: lexical_diversity() got a raw string with unit='lemma'. A st...
  tokens, no B      -> TypeError: lix() got tokens but no sentences. The number of sentences (...
```

Note the Hungarian LIX row: `26.10` computed correctly, `4.67` computed on lemmas. Nothing
in the second number looks wrong on its own.

## Source

```python
--8<-- "examples/two_contracts.py"
```
