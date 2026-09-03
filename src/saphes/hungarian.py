"""Hungarian orthography: counting *letters* rather than characters.

``len("ország")`` is 6, but Hungarian has five letters there — ``sz`` is one
letter. Nine multi-character letters (``cs dz dzs gy ly ny sz ty zs``) make a
character count and a letter count different numbers, and LIX counts letters.

Three things have to be right, and only the first is obvious:

**Maximal munch, left to right.** Longest match wins at each position, and the
match is *consumed* rather than rewritten. Rewriting is what breaks
:func:`~saphes.calibration.collapse_digraphs`: replacing ``sz`` with ``s`` after
a ``z`` manufactures a fresh ``zs``, which is then collapsed again, so
``közszolgálati`` comes out at 11 letters instead of 12.

**Geminates are written short.** A long ``sz`` is spelled ``ssz``, not
``szsz``. The scan therefore reads ``ssz`` as two ``sz`` letters. This rule is
*count-neutral* against the rival compound reading: ``vasszeg`` is ``vas`` +
``szeg``, so its ``ssz`` is ``s`` plus ``sz`` rather than a long ``sz`` — but
both readings are two letters, so the count is right either way and no table
entry is needed.

**Digraphs collide at morpheme boundaries.** ``község`` is ``köz`` + ``ség``, so
its ``zs`` is two letters and not the ``zs`` digraph. Nothing in the string says
so. This module attacks that with a productive rule for the ``-ság``/``-ség``
suffix and a small table of attested compounds; see :data:`MORPHEME_BOUNDARIES`.

That last part is a **bounded lexical judgement, not morphological analysis**. A
compound outside the table is still counted wrongly; the failure moved, it did
not go away. What can be said for it is that it is now measured: on the MOKK
Hungarian Webcorpus the boundary handling moves the corpus-level long-word share
by 0.01 percentage points, and it does not move the calibrated LIX threshold.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

__all__ = [
    "BOUNDARY_EXCEPTIONS",
    "HU_LETTERS",
    "MORPHEME_BOUNDARIES",
    "hungarian_letter_count",
    "hungarian_letters",
]

HU_LETTERS: tuple[str, ...] = (
    "dzs",
    "cs",
    "dz",
    "gy",
    "ly",
    "ny",
    "sz",
    "ty",
    "zs",
)
"""The nine multi-character Hungarian letters, longest first.

Each is a single *letter* in Hungarian orthography. Ordering is longest-first so
that ``dzs`` is read as one letter rather than ``dz`` plus ``s``.
"""

_GEMINATES: Mapping[str, str] = {
    "ddzs": "dzs",
    "ccs": "cs",
    "ddz": "dz",
    "ggy": "gy",
    "lly": "ly",
    "nny": "ny",
    "ssz": "sz",
    "tty": "ty",
    "zzs": "zs",
}
"""Doubled spellings, mapped to the letter they double.

Hungarian writes a long multi-character letter by doubling its first character:
long ``sz`` is ``ssz``, long ``dzs`` is ``ddzs``. Each spelling is two letters.
"""

_OVERLAPS: Mapping[str, tuple[str, ...]] = {
    "zsz": ("z", "sz"),
}
"""Sequences where the longest match is not the attested reading.

``zsz`` is ambiguous — ``zs`` + ``z``, or ``z`` + ``sz``. Both are two letters,
so the count is the same either way and this only fixes the *segmentation*. It
is worth fixing because every ``zsz`` type in the MOKK Webcorpus above a
frequency of 25 is the second reading: ``köz`` + ``szolgálati``, ``víz`` +
``szint``, ``száz`` + ``szor``, ``ház`` + ``szám``, ``torz`` + ``szülött``. The
sole counter-example is the acronym ``vdszsz``.
"""

_SCAN: tuple[tuple[str, tuple[str, ...]], ...] = tuple(
    sorted(
        [(spelling, (letter, letter)) for spelling, letter in _GEMINATES.items()]
        + list(_OVERLAPS.items())
        + [(letter, (letter,)) for letter in HU_LETTERS],
        key=lambda entry: -len(entry[0]),
    )
)

_BOUNDARY = "-"

# The productive -ság/-ség suffix after a stem-final z or c. The (?<!s) is what
# makes `egészség` and `készség` self-correcting with no table entry: there the
# `sz` binds leftward and the rule must not fire.
_SUFFIX_RULE = re.compile(r"((?<!s)z|c)(?=s[áé]g)")

MORPHEME_BOUNDARIES: Mapping[str, str] = {
    # Compounds in `-zavar`, after a stem-final s or d. The commonest class by
    # far, and productive, but listed rather than ruled: `s` + `zavar` cannot be
    # told from a real `sz` without knowing the stem.
    "alvászavar": "alvás-zavar",  # freq: 596
    "beszédzavar": "beszéd-zavar",  # freq: 124
    "identitászavar": "identitás-zavar",  # freq: 113
    "magatartászavar": "magatartás-zavar",  # freq: 92
    "rendzavar": "rend-zavar",  # freq: 91
    "látászavar": "látás-zavar",  # freq: 93
    "evészavar": "evés-zavar",  # freq: 87
    "ritmuszavar": "ritmus-zavar",  # freq: 79, also covers szívritmuszavar
    "működészavar": "működés-zavar",  # freq: 65
    "vérzészavar": "vérzés-zavar",  # freq: 65
    "légzészavar": "légzés-zavar",  # freq: 57
    # Colour compounds in `-zöld`, after a stem-final s or d.
    "kékeszöld": "kékes-zöld",  # freq: 343
    "világoszöld": "világos-zöld",  # freq: 341
    "sárgászöld": "sárgás-zöld",  # freq: 226
    "szürkészöld": "szürkés-zöld",  # freq: 193
    "smaragdzöld": "smaragd-zöld",  # freq: 155
    "haragoszöld": "haragos-zöld",  # freq: 102
    "zöldzóna": "zöld-zóna",  # freq: 262
    "leveszöldség": "leves-zöldség",  # freq: 51
    # Compounds in `-zár`, `-zászló`, `-záradék`, after a stem-final s or d.
    "nyílászár": "nyílás-zár",  # freq: 862, covers nyílászáró
    "évadzár": "évad-zár",  # freq: 389
    "rövidzár": "rövid-zár",  # freq: 329, covers rövidzárlat
    "honvédzászló": "honvéd-zászló",  # freq: 193
    "védzáradék": "véd-záradék",  # freq: 163
    # Compounds on `víz`, `gáz`, `pénz`, `eszköz`, `ház`, `nehéz`, `tánc`.
    "vízsug": "víz-sug",  # freq: 832, covers vízsugár/vízsugarat/vízsugaras
    "gázspray": "gáz-spray",  # freq: 318
    "gázsütő": "gáz-sütő",  # freq: 75
    "házsor": "ház-sor",  # freq: 280
    "eszközsor": "eszköz-sor",  # freq: 116
    "pénzsóvár": "pénz-sóvár",  # freq: 105
    "pénzsegély": "pénz-segély",  # freq: 54
    "nehézsúly": "nehéz-súly",  # freq: 327
    "nehézsors": "nehéz-sors",  # freq: 63
    "táncsport": "tánc-sport",  # freq: 140
    "táncstúdió": "tánc-stúdió",  # freq: 69
    # Compounds in `-zene`, after a stem-final s.
    "fúvószene": "fúvós-zene",  # freq: 1102, covers fúvószenekar
    "vonószene": "vonós-zene",  # freq: 130
    # A toponym, kis + Zombor.
    "kiszombor": "kis-zombor",  # freq: 190
}
"""Attested compounds whose seam manufactures a false digraph.

Keys are substrings; each maps to itself with a boundary marker inserted at the
seam. Applied by plain substring replacement, so an entry also covers the
inflected forms built on it — ``házsor`` covers ``házsorok``.

Entries are compounds only. The productive ``-ság``/``-ség`` suffix is handled
by rule instead, because a list of instances would be endless: the corpus has
``egyezség``, ``hitközség``, ``nagyközség``, ``ínyencség`` and ``féligazság``
alongside the obvious ``igazság``.

Every entry is a linguistic judgement that the corpus can support but not prove
— see ``experiments/hungarian_boundaries/`` for the evidence behind each one.
"""

BOUNDARY_EXCEPTIONS: frozenset[str] = frozenset(
    {
        "kavicságy",  # freq: 55 — kavics + ágy, so the cs is real
    }
)
"""Words where the ``-ság``/``-ség`` rule fires but should not.

The ``c`` half of the rule cannot tell ``malacság`` (``malac`` + ``ság``, where
``cs`` is a false digraph) from ``kavicságy`` (``kavics`` + ``ágy``, where it is
a real one). Matched as substrings, so an entry covers inflected forms.
"""


def hungarian_letters(
    word: str,
    *,
    boundaries: Mapping[str, str] = MORPHEME_BOUNDARIES,
    suffix_rule: bool = True,
) -> list[str]:
    """Split a word into Hungarian letters.

    Case-folds, inserts morpheme boundaries where they are known, then scans
    left to right taking the longest letter available at each position.

    Args:
        word: The word to split.
        boundaries: Compound seams to mark before scanning. Defaults to
            :data:`MORPHEME_BOUNDARIES`; pass ``{}`` to disable.
        suffix_rule: Whether to apply the productive ``-ság``/``-ség`` rule.
            Defaults to ``True``. Turning it off lowers the count on words like
            ``igazság``, so it changes results.

    Returns:
        One entry per letter. A doubled spelling yields its letter twice, so
        ``ssz`` yields ``['sz', 'sz']`` and the list does not rejoin to the
        input.

    Raises:
        TypeError: If ``word`` is not a ``str``. Incidental, from
            ``str.casefold``.

    Contract:
        Preconditions:

        - ``word`` should be a single token. Whitespace and punctuation are
          not rejected; they fall through to the single-character branch and
          are counted as letters, silently.

        Guarantees:

        - ``len()`` of the result never exceeds ``len(word)``.
        - Case-insensitive.
        - Every entry is either one of :data:`HU_LETTERS` or a single
          character.
        - Hyphens contribute nothing and block letters from forming across
          them, so ``gáz-számla`` is eight letters and not nine.

        Silences:

        - A compound outside ``boundaries`` whose seam forms a digraph is
          counted one letter short, with no error and no warning. That is the
          residual failure this module bounds rather than removes.
        - Doubled spellings are always read as geminates. Where the rival
          reading is a compound seam the count is the same either way, so
          nothing is lost — but the *segmentation* is then wrong.
        - ``zsz`` is always read as ``z`` + ``sz``, per :data:`_OVERLAPS`.
          The count is the same under either reading.

    Examples:
        ``sz`` is one letter, so ``ország`` is five:

        >>> hungarian_letters("ország")
        ['o', 'r', 'sz', 'á', 'g']

        A doubled spelling is two letters, written short:

        >>> hungarian_letters("asszony")
        ['a', 'sz', 'sz', 'o', 'ny']

        Consuming rather than rewriting keeps neighbouring letters apart. The
        naive collapser reads ``vízszint`` as six letters because replacing
        ``sz`` with ``s`` manufactures a ``zs``; here the ``z`` and the ``sz``
        stay separate:

        >>> hungarian_letters("vízszint")
        ['v', 'í', 'z', 'sz', 'i', 'n', 't']
    """
    word = word.casefold()
    for root, marked in boundaries.items():
        if root in word:
            word = word.replace(root, marked)
    if suffix_rule and not any(word_ in word for word_ in BOUNDARY_EXCEPTIONS):
        word = _SUFFIX_RULE.sub(r"\1" + _BOUNDARY, word)

    letters: list[str] = []
    index = 0
    while index < len(word):
        for spelling, emitted in _SCAN:
            if word.startswith(spelling, index):
                letters.extend(emitted)
                index += len(spelling)
                break
        else:
            if word[index] != _BOUNDARY:
                letters.append(word[index])
            index += 1
    return letters


def hungarian_letter_count(
    word: str,
    *,
    boundaries: Mapping[str, str] = MORPHEME_BOUNDARIES,
    suffix_rule: bool = True,
) -> int:
    """Count Hungarian *letters* rather than characters.

    A :data:`~saphes._types.LengthFn` suitable for passing to
    ``lix(..., length_policy=...)``, since both keyword arguments have
    defaults.

    Args:
        word: The word to measure.
        boundaries: Compound seams to mark before scanning. Defaults to
            :data:`MORPHEME_BOUNDARIES`.
        suffix_rule: Whether to apply the productive ``-ság``/``-ség`` rule.
            Defaults to ``True``.

    Returns:
        The number of Hungarian letters.

    Raises:
        TypeError: If ``word`` is not a ``str``.

    Contract:
        Guarantees:

        - Equal to ``len(hungarian_letters(word))``, always.
        - Never exceeds ``len(word)``.
        - Case-insensitive.

        Silences:

        - Everything :func:`hungarian_letters` silences, since this is a
          count of its output.

    Examples:
        ``ország`` is six characters but five letters:

        >>> len("ország"), hungarian_letter_count("ország")
        (6, 5)

        Doubled spellings and the ``dzs`` trigraph:

        >>> hungarian_letter_count("meggyes"), hungarian_letter_count("dzsungel")
        (6, 6)

        The productive suffix rule splits ``igazság`` into ``igaz`` + ``ság``,
        so its ``zs`` is two letters and not the digraph:

        >>> hungarian_letter_count("igazságos")
        9

        And it correctly declines to fire on ``egészség``, where the ``sz``
        binds leftward:

        >>> hungarian_letter_count("egészség")
        7
    """
    return len(hungarian_letters(word, boundaries=boundaries, suffix_rule=suffix_rule))
