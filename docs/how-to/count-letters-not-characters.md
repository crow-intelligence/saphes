# Count letters rather than characters

`len("ország")` is 6, but Hungarian has five letters there — `sz` is one letter. If your
orthography has multi-character letters, `word_length`'s default character count is not a
letter count.

## Use the bundled Hungarian counter

```pycon
>>> from saphes import hungarian_letter_count
>>> len("ország"), hungarian_letter_count("ország")
(6, 5)

```

It scans left to right taking the longest letter available, so doubled spellings come out as
two letters and the `dzs` trigraph as one:

```pycon
>>> hungarian_letter_count("meggyes"), hungarian_letter_count("dzsungel")
(6, 6)

```

It also knows where the productive `-ság`/`-ség` suffix puts a morpheme boundary, so the
`zs` in `község` is correctly two letters and the `sz` in `egészség` is correctly one:

```pycon
>>> hungarian_letter_count("község"), hungarian_letter_count("egészség")
(6, 7)

```

Pass it as a length policy:

```pycon
>>> from saphes import lix
>>> result = lix(["ország", "megvizsgálták"], sentences=1,
...              length_policy=hungarian_letter_count)
>>> result.length_policy
'custom:hungarian_letter_count'

```

The policy is recorded on the result, so a table of scores says how its lengths were counted.

## Write your own

A length policy is any callable taking a word and returning an int:

```pycon
>>> def no_vowels(word: str) -> int:
...     return sum(1 for c in word if c not in "aeiou")
>>> lix(["strength"], sentences=1, length_policy=no_vowels).long_words
1

```

## Watch out for

**Your callable's return value is not checked.** `word_length` returns whatever you give it:

```pycon
>>> from saphes import word_length
>>> word_length("ab", policy=lambda w: "not an int")
'not an int'

```

It fails later, inside `lix`, at the comparison — with a message naming neither your policy
nor the word:

```pycon
>>> lix(["ab"], sentences=1, length_policy=lambda w: "not an int")
Traceback (most recent call last):
    ...
TypeError: '>' not supported between instances of 'str' and 'int'

```

If you see that `TypeError` from `lix`, your length policy is the thing to check.

**A compound outside the boundary table is counted one letter short, silently.** The counter
knows a table of attested compound seams and a rule for the productive `-ság`/`-ség` suffix,
so it gets `község` and `igazságos` right. It cannot know about a compound nobody listed:

```pycon
>>> hungarian_letter_count("község"), hungarian_letter_count("vadzab")
(6, 5)

```

`vadzab` is `vad` + `zab`, six letters. There is no error and no warning — just a number one
too low. If your text is full of domain compounds, pass your own table:

```pycon
>>> hungarian_letter_count("vadzab", boundaries={"vadzab": "vad-zab"})
6

```

**A hyphen is not a letter, and letters do not form across it.** This differs from
`word_length`, which counts every character:

```pycon
>>> from saphes import word_length
>>> word_length("gáz-számla"), hungarian_letter_count("gáz-számla")
(10, 8)

```

**Character counting is still the default for `lix`,** as in Björnsson's original. The letter
count is calibrated separately — see
[Use a calibrated threshold](use-a-calibrated-threshold.md).

## See the segmentation

When a count looks wrong, ask for the letters rather than guessing:

```pycon
>>> from saphes import hungarian_letters
>>> hungarian_letters("kulcsszó")
['k', 'u', 'l', 'cs', 'sz', 'ó']

```

## Related

- [`word_length` reference](../reference/readability.md) — the three built-in policies and
  the Unicode normalisation they apply.
- [Calibrate a new language](calibrate-a-new-language.md) — `length_curve` takes the same
  policy, so you can calibrate on letters instead of characters.
- [`saphes.hungarian` reference](../reference/hungarian.md) — the scan table, the boundary
  table, and what each silences.
- [Measure Hungarian text](measure-hungarian-text.md) — this, the calibrated threshold and the
  stemmer in one recipe.

The boundary table is not guesswork: it was mined from the MOKK Webcorpus and reviewed by
hand. The candidates, the verdicts on each, and what the corpus can and cannot establish are
in `experiments/hungarian_boundaries/` in the repository.
