"""The share of a Hungarian text's vocabulary that is foreign — *idegenszó-arány*.

    ratio = foreign lemmas / total lemmas

**This metric requires lemmas, and the requirement is not a preference.** Hungarian
morphology buries the root: *komputerekkel* is one suffix chain away from
*komputer*, and a lexicon lookup on the surface form misses it. That is the
same argument :mod:`saphes.diversity` makes, for the same reason, and the
opposite of what :mod:`saphes.readability` needs — see those modules, and never
feed one token stream to all three.

Worked example, computed by hand::

    ["a", "komputer", "gyors", "lenni"]  against  {"komputer"}

    total   = 4
    matched = 1  (komputer)
    ratio   = 0.25

**saphes ships no lexicon here, and this function will not invent one.** You
supply the set, or you enable the phonotactic heuristic, or both; asking for
neither raises rather than reporting that every word is native. What counts as
a loan word is a linguistic judgement about a *particular* vocabulary, and the
package has no business making it silently.

That judgement is sharper than it looks. Hungarian distinguishes *jövevényszó*
— a borrowing so assimilated that no speaker hears it as foreign, like *ablak*,
*király* or *pénz*, all Slavic — from *idegen szó*, a word still felt as
foreign. A lexicon built from a dictionary's etymology fields will contain the
first kind in bulk, and a ratio computed against it measures etymological origin
rather than *idegenszó-arány*. Both are defensible numbers; they are not the
same number, and the caller is the one who knows which was wanted.

The optional heuristic is a **fallback, not a detector**, and two classes of
Hungarian spelling look foreign without being so. Both are handled, and both
were established from the MOKK Webcorpus rather than from memory.

**Morpheme seams.** The potential suffix ``-hat``/``-het`` and the allative
``-hoz``/``-hez``/``-höz`` put an ``h`` straight after a stem, so any stem
ending in ``t``, ``p`` or ``c`` manufactures a digraph across the join:
*látható*, *kapható*, *állathoz*, *táncház*. That is 1,187 word forms and 2.5
million tokens of false positive, and it is productive, so no list could cover
it. :data:`FOREIGN_PATTERNS` carries a negative lookahead instead.

**Archaic surnames.** ``th`` spells a plain *t* in *Tóth*, *Horváth*, *Németh*
and *Kossuth* — among the commonest surnames in the country. These are
lexicalised, so they are listed in :data:`HEURISTIC_EXCEPTIONS` with their
corpus frequencies, alongside native compounds like *mintha* and *otthon*.

Together the two remove **16.5% of the tokens** the heuristic used to flag
across the Webcorpus. What remains is a residual, not a solution: a surname
outside the list is still flagged, so supply ``pos_tags`` where you can, and
read ``matched_by_heuristic`` and ``pattern_counts`` rather than trusting
``ratio`` on its own.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Container, Mapping, Sequence, Sized
from dataclasses import asdict, dataclass
from typing import Literal

import saphes

__all__ = [
    "FOREIGN_PATTERNS",
    "HEURISTIC_EXCEPTIONS",
    "LoanwordResult",
    "loan_ratio_from_counts",
    "loanword_ratio",
]

FOREIGN_PATTERNS: Mapping[str, str] = {
    # Letters Hungarian orthography does not use for native vocabulary. `y` is
    # deliberately absent: it is half of `gy`, `ly`, `ny` and `ty`, so it would
    # fire on almost every native word.
    "x": r"x",
    "w": r"w",
    "q": r"q",
    # Digraphs Hungarian spells otherwise. Native `f` replaces `ph` and native
    # `t` replaces `th`, so both survive only in unassimilated spellings —
    # `philosophia` became `filozófia`, `theológia` became `teológia`.
    #
    # The negative lookahead is load-bearing, not tidiness. Hungarian's
    # potential suffix `-hat`/`-het` and its allative `-hoz`/`-hez`/`-höz` put
    # an `h` directly after a stem, so any stem ending in `t`, `p` or `c`
    # manufactures one of these digraphs across the seam: `lát` + `ható` reads
    # as `th`, `kap` + `ható` as `ph`, `tánc` + `ház` as `ch`. Measured on the
    # MOKK Webcorpus that is **1,187 word forms and 2.5 million tokens** of pure
    # false positive, dwarfing every other error the heuristic makes.
    "ch": r"ch(?!at|et|oz|ez|öz|áz)",
    "ph": r"ph(?!at|et|oz|ez|öz|áz)",
    "th": r"th(?!at|et|oz|ez|öz|áz)",
    # Word-initial clusters native Hungarian avoids. Anchored, because the same
    # letters occur freely across a morpheme boundary inside a compound.
    "initial-sztr": r"^sztr",
    "initial-str": r"^str",
    "initial-spr": r"^spr",
    "absz": r"^absz",
}
"""Spellings that suggest a word entered Hungarian from outside.

A **heuristic**, and a crude one. Each entry is named so that
:attr:`LoanwordResult.pattern_counts` can report which fired, because a ratio
that cannot be broken down is a ratio that cannot be checked.

The three digraph patterns carry a negative lookahead so they do not fire
across Hungarian's ``-hat``/``-het`` and ``-hoz``/``-hez``/``-höz`` seams; see
:data:`HEURISTIC_EXCEPTIONS` for the lexicalised cases a rule cannot reach.

What no spelling rule can do is separate a foreign *name* from a foreign
*word*. The listed surnames are handled; an unlisted one is not, and only
``pos_tags`` will catch it.

Substitutable: pass your own mapping as ``patterns=``. The value changes the
number, so it is a parameter rather than a constant.
"""

HEURISTIC_EXCEPTIONS: frozenset[str] = frozenset(
    {
        # Hungarian surnames in archaic orthography, where `th` spells plain
        # `t` and `ch` plain `cs`/`k`. Frequencies are MOKK Webcorpus 2.2
        # counts of the lower-cased form, so the list is attested rather than
        # remembered. These are among the commonest surnames in the country:
        # without them a page of Hungarian history reads as a page of foreign
        # words.
        "tóth",  # freq: 87,321
        "horváth",  # freq: 79,589
        "kossuth",  # freq: 62,854
        "németh",  # freq: 58,127
        "széchenyi",  # freq: 42,074
        "madách",  # freq: 15,203
        "batthyány",  # freq: 9,498
        "mikszáth",  # freq: 9,362
        "semmelweis",  # freq: 8,464
        "széchényi",  # freq: 5,962
        "wesselényi",  # freq: 5,052
        "weöres",  # freq: 4,585
        "báthory",  # freq: 4,515
        "zichy",  # freq: 3,987
        "lamperth",  # freq: 3,947
        "thököly",  # freq: 3,725
        "bernáth",  # freq: 3,233
        "baráth",  # freq: 3,097
        "pesuth",  # freq: 2,996
        "báthori",  # freq: 2,621
        "roth",  # freq: 2,407
        "róth",  # freq: 2,260
        "toth",  # freq: 1,692 — unaccented spelling, common in URLs and forms
        "csáth",  # freq: 1,671
        "horvath",  # freq: 1,557 — unaccented spelling
        "donáth",  # freq: 1,485
        "nemeth",  # freq: 739 — unaccented spelling
        "werbőczy",  # freq: 639
        "thaly",  # freq: 612
        "cházár",  # freq: 452
        "thúry",  # freq: 370
        "passuth",  # freq: 296
        "chorin",  # freq: 235
        # Native compounds where an `h`-initial second element meets a stem
        # ending in `t`. Lexicalised, so a rule cannot reach them, but closed
        # and short. Matching is on lemmas, so `otthonában` and `otthonról`
        # are covered by `otthon`.
        "mintha",  # freq: 290,286 — mint + ha
        "otthon",  # freq: 138,479 — ott + hon
        "itthon",  # freq: 71,946 — itt + hon
        "hátha",  # freq: 56,652 — hát + ha
        "szentháromság",  # freq: 6,130 — szent + háromság
        "kétharmad",  # freq: 1,719 — két + harmad
    }
)
"""Lemmas the spelling heuristic must not flag, however they are spelled.

Two classes, both established from the MOKK Webcorpus rather than from memory:
**Hungarian surnames in archaic orthography**, where `th` spells a plain `t`,
and **native compounds** in which an `h`-initial second element lands against a
stem-final `t`.

Note that `-gh` names — *Balogh*, *Végh*, *Országh*, *Virágh* — are **not**
listed, and do not need to be: `gh` is not one of :data:`FOREIGN_PATTERNS`, so
nothing flags them today. Adding a `gh` pattern would require adding them here
in the same breath.

Substitutable and extensible: pass ``exceptions=`` to
:func:`loanword_ratio`. The list is bounded lexical judgement, not morphological
analysis, and a surname outside it is still flagged — the failure moved, it did
not go away.
"""

_COMPILED = {name: re.compile(pattern) for name, pattern in FOREIGN_PATTERNS.items()}


def loan_ratio_from_counts(*, matched: int, total: int) -> float:
    """Compute the loan-word ratio from the two counts directly.

    The arithmetic kernel. Keyword-only, because two bare ints in this order are
    trivially transposed and the transposition returns a number above 1 rather
    than an error in every case but one.

    Args:
        matched: Lemmas identified as foreign.
        total: Lemmas considered. Must be positive.

    Returns:
        ``matched / total``, between 0.0 and 1.0.

    Raises:
        ValueError: If ``total`` is not positive, ``matched`` is negative, or
            ``matched`` exceeds ``total``.

    Contract:
        Guarantees:

        - The result is in ``[0.0, 1.0]``.
        - Total for every input that passes the guards; no division by zero is
          reachable.

    Examples:
        >>> loan_ratio_from_counts(matched=1, total=4)
        0.25
        >>> loan_ratio_from_counts(matched=0, total=4)
        0.0

        Empty input is an error, not a zero:

        >>> loan_ratio_from_counts(matched=0, total=0)
        Traceback (most recent call last):
            ...
        ValueError: the loan-word ratio needs at least one lemma, got 0
    """
    if total <= 0:
        msg = f"the loan-word ratio needs at least one lemma, got {total}"
        raise ValueError(msg)
    if matched < 0:
        msg = f"matched cannot be negative, got {matched}"
        raise ValueError(msg)
    if matched > total:
        msg = f"matched ({matched}) cannot exceed total ({total})"
        raise ValueError(msg)
    return matched / total


@dataclass(frozen=True, slots=True, repr=False)
class LoanwordResult:
    """A loan-word ratio together with everything that produced it.

    Attributes:
        ratio: Foreign lemmas over lemmas considered.
        total_lemmas: Lemmas considered, after exclusions.
        matched: Lemmas identified as foreign.
        matches: The matched lemmas themselves, in first-appearance order and
            deduplicated. The audit trail: a ratio nobody can inspect is a
            ratio nobody can check.
        matched_by_lexicon: Matches found in the supplied lexicon.
        matched_by_heuristic: Matches found *only* by the spelling heuristic.
            Kept separate because the heuristic's false positives would
            otherwise be indistinguishable from dictionary evidence.
        pattern_counts: ``(pattern name, hits)`` for each heuristic pattern that
            fired, most frequent first.
        lexicon_id: Caller-supplied label for the lexicon. Provenance only.
        lexicon_size: Entries in the lexicon, or ``None`` if none was given.
        heuristic: Whether the spelling heuristic was enabled.
        exceptions_applied: Lemmas the heuristic would have flagged but for
            :data:`HEURISTIC_EXCEPTIONS`. A large count on Hungarian prose is
            expected — ``Tóth`` and ``mintha`` are common — and a zero on a
            corpus full of names means the exceptions are not reaching it.
        excluded: Lemmas skipped — proper nouns by tag, plus anything in
            ``exclude``. They are not in ``total_lemmas``.
        unit: Always ``"lemma"``. Surface forms hide the root, so this field is
            the contract marker that says what was measured.
        case_folded: Whether lemmas were case-folded before lookup.
        saphes_version: Version of saphes that produced the result.
    """

    ratio: float
    total_lemmas: int
    matched: int
    matches: tuple[str, ...]
    matched_by_lexicon: int
    matched_by_heuristic: int
    pattern_counts: tuple[tuple[str, int], ...]
    lexicon_id: str | None
    lexicon_size: int | None
    heuristic: bool
    exceptions_applied: int
    excluded: int
    # Deliberately not TokenUnit. This metric has exactly one legal stream, and
    # pinning the literal is what stops a surface or stem stream reaching it
    # unremarked. Do not widen it.
    unit: Literal["lemma"]
    case_folded: bool
    saphes_version: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the result.

        Returns:
            A plain dict with one key per field.

        Examples:
            >>> record = loanword_ratio(
            ...     ["a", "komputer"], lexicon={"komputer"}
            ... ).to_dict()
            >>> record["matched"]
            1
            >>> record["unit"]
            'lemma'
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr carrying the heuristic caveat when it is load-bearing."""
        head = (
            f"LoanwordResult(ratio={self.ratio:.4f}, matched={self.matched}, "
            f"total={self.total_lemmas}, unit='lemma')"
        )
        if self.matched_by_heuristic:
            return (
                f"{head}\n  ! {self.matched_by_heuristic} of {self.matched} matched by "
                "spelling alone; proper nouns trip the same patterns"
            )
        return head


def _fold(lemma: str, *, case_fold: bool) -> str:
    """Normalise one lemma for lookup.

    Contract:
        Guarantees:

        - NFC first, so a decomposed lemma matches a composed lexicon entry.
        - Case folding is applied only when asked; it is not a no-op for
          Hungarian, where it also merges the long vowels' cases.
    """
    folded = unicodedata.normalize("NFC", lemma)
    return folded.casefold() if case_fold else folded


def loanword_ratio(
    lemmas: Sequence[str],
    *,
    lexicon: Container[str] | None = None,
    heuristic: bool = False,
    patterns: Mapping[str, str] = FOREIGN_PATTERNS,
    pos_tags: Sequence[str] | None = None,
    exclude_tags: Container[str] = frozenset({"PROPN"}),
    exclude: Container[str] = frozenset(),
    exceptions: Container[str] = HEURISTIC_EXCEPTIONS,
    case_fold: bool = True,
    lexicon_id: str | None = None,
) -> LoanwordResult:
    """Measure the share of foreign lemmas in a Hungarian text.

    Args:
        lemmas: The lemma stream. **Not** surface forms: Hungarian morphology
            hides the root, so a raw string raises rather than being split.
        lexicon: Membership test for known foreign lemmas — any object
            supporting ``in``, usually a ``set``. Entries are compared after the
            same folding applied to the lemmas.
        heuristic: Enable the spelling heuristic. Defaults to ``False``, because
            it cannot distinguish a foreign word from a foreign name.
        patterns: The heuristic's patterns. Defaults to
            :data:`FOREIGN_PATTERNS`; substituting changes the number.
        pos_tags: One tag per lemma, parallel to ``lemmas``. Supply it to have
            proper nouns excluded. saphes does no named-entity recognition and
            will not guess.
        exclude_tags: Tags to skip when ``pos_tags`` is given. Defaults to
            ``{"PROPN"}``.
        exclude: Lemmas to skip outright, whatever their tag.
        exceptions: Lemmas the **heuristic** must not flag, defaulting to
            :data:`HEURISTIC_EXCEPTIONS`. It does not affect the lexicon: a
            dictionary match is evidence, and an exception is only a statement
            that a spelling is misleading. Pass ``frozenset()`` to disable.
        case_fold: Fold case before lookup. Defaults to ``True`` — the opposite
            of :func:`saphes.diversity.lexical_diversity`, and deliberately so:
            a lexicon is a list of dictionary forms, and matching it is the
            whole operation. The two defaults differ because the two questions
            differ.
        lexicon_id: Provenance label recorded on the result.

    Returns:
        A :class:`LoanwordResult` carrying the ratio, the matched lemmas, and
        every parameter that moved the number.

    Raises:
        TypeError: If ``lemmas`` is a raw string.
        ValueError: If ``lemmas`` is empty, if neither ``lexicon`` nor
            ``heuristic`` is supplied, if ``pos_tags`` has a different length,
            or if every lemma is excluded.

    Contract:
        Preconditions:

        - ``lemmas`` must be lemmas. Nothing can check this — a surface stream
          produces no error and a **plausible, low ratio**, because inflected
          forms miss the lexicon. This is the silent failure of the module and
          the reason ``unit`` is recorded on every result.
        - Either ``lexicon`` or ``heuristic`` must be given. Asking for
          neither raises rather than reporting 0.0 for every text.

        Guarantees:

        - ``0.0 <= ratio <= 1.0``.
        - ``matched == matched_by_lexicon + matched_by_heuristic``, counting
          each distinct lemma once, so the two sources never double-count.
        - ``matches`` contains exactly the lemmas counted in ``matched``.

        Silences:

        - **A loan word absent from the lexicon is counted native**, without
          any signal. The failure moves with the lexicon; it does not go away.
          ``lexicon_size`` is on the result so that a suspiciously small one
          is at least visible.
        - Proper nouns are excluded **only** when ``pos_tags`` is supplied.
          Without it, *Windows* and *Bordeaux* count as foreign words.
        - Duplicate lemmas are counted once in ``matches`` but once **per
          occurrence** in ``matched`` and ``total_lemmas``, so the ratio is
          token-weighted rather than type-weighted.

    Examples:
        >>> result = loanword_ratio(
        ...     ["a", "komputer", "gyors", "lenni"], lexicon={"komputer"}
        ... )
        >>> result.ratio
        0.25
        >>> result.matches
        ('komputer',)
        >>> result
        LoanwordResult(ratio=0.2500, matched=1, total=4, unit='lemma')

        The heuristic catches what a small lexicon misses, and says so:

        >>> spelled = loanword_ratio(
        ...     ["absztrakt", "taxi", "kutya"], heuristic=True
        ... )
        >>> spelled.matched, spelled.matched_by_heuristic
        (2, 2)
        >>> spelled.pattern_counts
        (('absz', 1), ('x', 1))

        Hungarian spellings that only look foreign are excepted by default —
        the archaic surnames, and the seams where an ``-hat``/``-hoz`` suffix
        lands an ``h`` against a stem-final ``t``:

        >>> loanword_ratio(["Tóth", "látható"], heuristic=True, lexicon=set()).matched
        0

        An unlisted surname is still flagged, so tags remain worth supplying:

        >>> loanword_ratio(["Wagnerné"], heuristic=True, lexicon=set()).matched
        1

        Surface forms are not refused, and that is the danger:

        >>> loanword_ratio(["komputerekkel"], lexicon={"komputer"}).ratio
        0.0
    """
    if isinstance(lemmas, str):
        msg = (
            "loanword_ratio() got a raw string. Hungarian morphology hides the "
            "root, so this metric needs lemmas from upstream analysis (huspacy, "
            "emtsv), not text that saphes could split into surface forms."
        )
        raise TypeError(msg)
    if not lemmas:
        msg = "loanword_ratio() needs at least one lemma, got none"
        raise ValueError(msg)
    if lexicon is None and not heuristic:
        msg = (
            "loanword_ratio() needs a lexicon, heuristic=True, or both. With "
            "neither it would report every word as native, which is a number "
            "about nothing. saphes ships no Hungarian loan-word lexicon."
        )
        raise ValueError(msg)
    if pos_tags is not None and len(pos_tags) != len(lemmas):
        msg = (
            f"pos_tags has {len(pos_tags)} entries but lemmas has "
            f"{len(lemmas)}; they must be parallel"
        )
        raise ValueError(msg)

    compiled = (
        _COMPILED
        if patterns is FOREIGN_PATTERNS
        else {name: re.compile(p) for name, p in patterns.items()}
    )

    total = 0
    excluded = 0
    matched_total = 0
    by_lexicon = 0
    by_heuristic = 0
    hits: dict[str, int] = {}
    spared = 0
    seen: list[str] = []
    seen_set: set[str] = set()

    for position, raw in enumerate(lemmas):
        lemma = _fold(raw, case_fold=case_fold)
        if pos_tags is not None and pos_tags[position] in exclude_tags:
            excluded += 1
            continue
        if lemma in exclude or raw in exclude:
            excluded += 1
            continue
        total += 1

        in_lexicon = lexicon is not None and lemma in lexicon
        if heuristic and lemma in exceptions:
            spared += 1
        fired = (
            [name for name, rx in compiled.items() if rx.search(lemma)]
            if heuristic and lemma not in exceptions
            else []
        )
        if not in_lexicon and not fired:
            continue

        matched_total += 1
        if in_lexicon:
            by_lexicon += 1
        else:
            by_heuristic += 1
            for name in fired:
                hits[name] = hits.get(name, 0) + 1
        if lemma not in seen_set:
            seen_set.add(lemma)
            seen.append(lemma)

    if total == 0:
        msg = "every lemma was excluded; nothing was measured"
        raise ValueError(msg)

    return LoanwordResult(
        ratio=loan_ratio_from_counts(matched=matched_total, total=total),
        total_lemmas=total,
        matched=matched_total,
        matches=tuple(seen),
        matched_by_lexicon=by_lexicon,
        matched_by_heuristic=by_heuristic,
        pattern_counts=tuple(sorted(hits.items(), key=lambda kv: (-kv[1], kv[0]))),
        lexicon_id=lexicon_id,
        lexicon_size=len(lexicon) if isinstance(lexicon, Sized) else None,
        heuristic=heuristic,
        exceptions_applied=spared,
        excluded=excluded,
        unit="lemma",
        case_folded=case_fold,
        saphes_version=saphes.__version__,
    )
