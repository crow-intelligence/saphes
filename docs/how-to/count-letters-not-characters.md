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

**Collapsing digraphs is a sensitivity check, not ground truth.** It misfires wherever a
digraph spans a morpheme boundary — `község` is `köz` + `ség`, so its `zs` is two letters,
but the collapser cannot know that:

```pycon
>>> hungarian_letter_count("község")   # the true count is 6
5

```

This is why character counting stays the default, as in Björnsson's original. Use the letter
count to check whether your conclusion survives the choice, not to replace it.

## Related

- [`word_length` reference](../reference/readability.md) — the three built-in policies and
  the Unicode normalisation they apply.
- [Calibrate a new language](calibrate-a-new-language.md) — `length_curve` takes the same
  policy, so you can calibrate on letters instead of characters.
