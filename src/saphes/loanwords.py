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

**saphes ships no lexicon, and this function will not guess without one.** The
``lexicon`` argument is required. What counts as a loan word is a linguistic
judgement about a *particular* vocabulary, and the package has no business
making it silently.

That judgement is sharper than it looks. Hungarian distinguishes *jövevényszó*
— a borrowing so assimilated that no speaker hears it as foreign, like *ablak*,
*király* or *pénz*, all Slavic — from *idegen szó*, a word still felt as
foreign. A lexicon built from a dictionary's etymology fields will contain the
first kind in bulk, and a ratio computed against it measures etymological origin
rather than *idegenszó-arány*. Both are defensible numbers; they are not the
same number, and the caller is the one who knows which was wanted.

There is **no spelling heuristic**. An earlier version carried one — regexes for
`x`, `w`, `ch`, `th` and the like — and it was removed rather than repaired.
Measured against the shipped lexicon it covered only 8.4% of it, because most
*idegen szavak* (*prioritás*, *konszenzus*, *implementáció*) look nothing like
foreign words; what it added beyond the lexicon was overwhelmingly English and
German text in the corpus, plus native Hungarian that only looks foreign
(*mintha*, *otthon*, *látható*, and the surnames *Tóth* and *Horváth*). Worst,
the words it added that *were* foreign — *technológia*, *abszolút*, *szexuális*
— are exactly the ones a frequency-selected lexicon deliberately excludes as
assimilated, so enabling it silently reversed the caller's own decision. A
lexicon is evidence; a spelling rule was a guess that contradicted it.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Container, Sequence, Sized
from dataclasses import asdict, dataclass
from typing import Literal

import saphes

__all__ = [
    "LoanwordResult",
    "loan_ratio_from_counts",
    "loanword_ratio",
]


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
        lexicon_id: Caller-supplied label for the lexicon. Provenance only.
        lexicon_size: Entries in the lexicon, or ``None`` if none was given.
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
    lexicon_id: str | None
    lexicon_size: int | None
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
        """Return a repr showing the ratio and the counts behind it."""
        return (
            f"LoanwordResult(ratio={self.ratio:.4f}, matched={self.matched}, "
            f"total={self.total_lemmas}, unit='lemma')"
        )


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
    lexicon: Container[str],
    pos_tags: Sequence[str] | None = None,
    exclude_tags: Container[str] = frozenset({"PROPN"}),
    exclude: Container[str] = frozenset(),
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
        pos_tags: One tag per lemma, parallel to ``lemmas``. Supply it to have
            proper nouns excluded. saphes does no named-entity recognition and
            will not guess.
        exclude_tags: Tags to skip when ``pos_tags`` is given. Defaults to
            ``{"PROPN"}``.
        exclude: Lemmas to skip outright, whatever their tag.
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
        TypeError: If ``lemmas`` is a raw string, or ``lexicon`` is omitted.
        ValueError: If ``lemmas`` is empty, if ``pos_tags`` has a different
            length, or if every lemma is excluded.

    Contract:
        Preconditions:

        - ``lemmas`` must be lemmas. Nothing can check this — a surface stream
          produces no error and a **plausible, low ratio**, because inflected
          forms miss the lexicon. This is the silent failure of the module and
          the reason ``unit`` is recorded on every result.
        - ``lexicon`` is required, not defaulted. There is no fallback: a
          ratio computed against no evidence would be a number about nothing.

        Guarantees:

        - ``0.0 <= ratio <= 1.0``.
        - ``matches`` contains exactly the distinct lemmas counted in
          ``matched``, in first-appearance order.

        Silences:

        - **A loan word absent from the lexicon is counted native**, without
          any signal. The failure moves with the lexicon; it does not go away.
          ``lexicon_size`` is on the result so that a suspiciously small one
          is at least visible.
        - Proper nouns are excluded **only** when ``pos_tags`` is supplied.
          Without it, *Windows* and *Bordeaux* count as foreign if the lexicon
          happens to list them.
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

        Proper nouns are excluded when tags say which they are:

        >>> loanword_ratio(
        ...     ["Bordeaux", "komputer"],
        ...     lexicon={"bordeaux", "komputer"},
        ...     pos_tags=["PROPN", "NOUN"],
        ... ).matches
        ('komputer',)

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
    if pos_tags is not None and len(pos_tags) != len(lemmas):
        msg = (
            f"pos_tags has {len(pos_tags)} entries but lemmas has "
            f"{len(lemmas)}; they must be parallel"
        )
        raise ValueError(msg)

    total = 0
    excluded = 0
    matched_total = 0
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

        if lemma not in lexicon:
            continue

        matched_total += 1
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
        lexicon_id=lexicon_id,
        lexicon_size=len(lexicon) if isinstance(lexicon, Sized) else None,
        excluded=excluded,
        unit="lemma",
        case_folded=case_fold,
        saphes_version=saphes.__version__,
    )
