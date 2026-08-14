"""Lexical diversity: type-token ratio, and its length-corrected moving average.

The arithmetic is the NLTK book's (ch. 1) — types over tokens::

    def lexical_diversity(text):
        return len(set(text)) / len(text)

**But the input must be lemmatised.** On surface forms, TTR measures *morphology*,
not vocabulary: Hungarian ``ház / házak / házban / házakat`` is four types and one
lemma, and Ancient Greek is worse. Un-lemmatised TTR reports inflectional richness
as lexical richness, and inflates most for exactly the languages this package was
built for. That is not a tuning option; it is the difference between measuring the
right thing and the wrong thing. So ``unit`` is required and has no default.

**The package consumes lemmas; it does not produce them.** Lemmatisation is
language-specific and heavy — CLTK or a treebank for Greek, huspacy for Hungarian
— and bundling one would wreck a deliberately tiny package. The caller lemmatises;
saphes measures.

This is the exact opposite of what :mod:`saphes.readability` requires, which needs
surface forms because word length is its signal. Feed one token stream to both and
exactly one of them is silently wrong — no error, no NaN, just a plausible number.
The parameter names (``lemmas=`` here, ``words=`` there), the required ``unit``,
and the ``unit`` recorded on every result all exist to make that mistake loud.

.. warning::

    **TTR is inversely related to text length**, so TTR values from texts of
    different lengths are **not comparable**. A raw TTR over corpora of different
    sizes mostly ranks them by size. Use :func:`mattr` — pass ``window=`` — when
    the things you are comparing differ in length, which for per-decade or
    per-book work they always do.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass

import saphes
from saphes import segment
from saphes._types import TokenSource, TokenUnit

__all__ = [
    "DiversityResult",
    "lexical_diversity",
    "mattr",
    "ttr_from_counts",
]

_VALID_UNITS = frozenset(("lemma", "surface"))


def ttr_from_counts(*, types: int, tokens: int) -> float:
    """Compute the type-token ratio from the two counts directly.

    The arithmetic kernel. Keyword-only, because two bare ints are trivially
    transposed — and transposing them yields a number greater than 1 rather than
    an error, which is precisely the kind of quiet wrongness worth designing out.

    Args:
        types: The number of distinct types. Must be positive.
        tokens: The number of tokens. Must be positive.

    Returns:
        ``types / tokens``, in ``(0, 1]``.

    Raises:
        ValueError: If either count is not positive, or if ``types`` exceeds
            ``tokens``.

    Contract:
        Preconditions:

        - Both arguments must be ``int``. Every constraint is checked
          explicitly and raises ``ValueError`` naming the count, so there is
          no silent failure mode for integer input.
        - Floats are not rejected — the comparisons and the division accept
          them — so a float ``tokens`` returns a ratio rather than raising.
          Only the callers guarantee integers.

        Guarantees:

        - The result lies in ``(0, 1]``.
        - ``types == tokens`` (all distinct) gives exactly ``1.0``.
        - Total for every input that passes the guards; no division by zero
          is reachable, since ``tokens`` is known positive by then.

    Examples:
        >>> ttr_from_counts(types=2, tokens=4)
        0.5
        >>> ttr_from_counts(types=0, tokens=0)
        Traceback (most recent call last):
            ...
        ValueError: TTR needs at least one token, got 0
    """
    if tokens <= 0:
        msg = f"TTR needs at least one token, got {tokens}"
        raise ValueError(msg)
    if types <= 0:
        msg = f"TTR needs at least one type, got {types}"
        raise ValueError(msg)
    if types > tokens:
        msg = f"types ({types}) cannot exceed tokens ({tokens})"
        raise ValueError(msg)
    return types / tokens


def mattr(tokens: list[str], window: int = 100) -> float:
    """Moving-Average Type-Token Ratio of a token sequence.

    The mean over every length-``window`` contiguous window of
    (distinct tokens / window). Approximately independent of total length, so
    unlike plain TTR it is comparable across texts of different sizes — it reads
    as "what fraction of words are distinct within any ``window``-token span"
    (Covington & McFall, 2010).

    This function deliberately returns a bare ``float`` and takes a bare list,
    unlike everything else in saphes, which returns a result object. It is a
    drop-in replacement for the identical implementations that grew up in
    ``music_networks`` and ``kmdb_dashboard``, and keeping the signature
    byte-compatible means those call sites change only their import line. Use
    :func:`lexical_diversity` with ``window=`` if you want the audit trail.

    Args:
        tokens: The token sequence (order matters). Should be lemmas, for the
            reasons in the module docstring.
        window: Sliding-window length in tokens.

    Returns:
        A diversity score in ``[0, 1]`` (``0.0`` for an empty sequence).

    Contract:
        Preconditions:

        - ``tokens`` must be **sized and indexable**. The annotation says
          ``list[str]``, but any sequence works — a tuple is fine. A
          generator or other one-shot iterator raises ``TypeError``
          (implicit, from ``len(tokens)`` at diversity.py:174).
        - ``tokens`` must be **ordered and meaningfully so**. Passing a
          ``set`` succeeds and returns a number, but the windows are drawn
          over arbitrary iteration order, so the result is meaningless. No
          error is raised.
        - Elements must be hashable (implicit, from ``Counter`` at
          diversity.py:180). They need not be strings; anything hashable is
          counted by identity of value.
        - ``window`` must be **positive**. This function does not check it,
          unlike ``lexical_diversity()``, which guards it at
          diversity.py:382. Passing ``window=0`` raises ``ZeroDivisionError``
          (implicit, from the final division at diversity.py:198); a
          negative ``window`` raises ``IndexError`` (implicit, from
          ``tokens[i - window]`` at diversity.py:189). Neither message
          mentions ``window``.

        Guarantees:

        - Empty input returns ``0.0`` rather than raising — the historical
          behaviour this replaces. :func:`lexical_diversity` raises instead.
        - Sequences shorter than ``window`` degrade to the plain TTR of the
          whole sequence.
        - The result lies in ``[0, 1]`` for any positive ``window``.

    Examples:
        >>> mattr(["a", "b", "a", "b"], window=2)   # every 2-window is all-distinct
        1.0
        >>> mattr(["a", "a", "a"], window=2)         # each 2-window has 1 type
        0.5
        >>> mattr(["a", "b", "c"], window=10)        # shorter than window -> plain TTR
        1.0
        >>> mattr([], window=5)
        0.0
    """
    n = len(tokens)
    if n == 0:
        return 0.0
    if n <= window:
        return len(set(tokens)) / n

    counts: Counter[str] = Counter()
    distinct = 0
    for tok in tokens[:window]:
        if counts[tok] == 0:
            distinct += 1
        counts[tok] += 1
    total = distinct
    n_windows = 1
    for i in range(window, n):
        add, rem = tokens[i], tokens[i - window]
        if counts[add] == 0:
            distinct += 1
        counts[add] += 1
        counts[rem] -= 1
        if counts[rem] == 0:
            distinct -= 1
        total += distinct
        n_windows += 1
    return total / (n_windows * window)


@dataclass(frozen=True, slots=True, repr=False)
class DiversityResult:
    """A diversity score together with everything that produced it.

    Attributes:
        ttr: The type-token ratio, ``types / tokens``.
        types: The number of distinct types counted.
        tokens: The number of tokens counted.
        unit: ``"lemma"`` or ``"surface"`` — what the token stream was declared
            to be. Always recorded, because it changes what the number means.
        case_folded: Whether tokens were case-folded before counting types.
        token_source: ``"provided"`` if the caller passed tokens,
            ``"segmented"`` if saphes split them out of raw text.
        pos_filter: A caller-supplied label describing any part-of-speech
            filtering already applied upstream. Provenance only — saphes never
            tags anything itself.
        mattr: The moving-average TTR, or ``None`` if no ``window`` was given.
        window: The MATTR window length, or ``None``.
        saphes_version: Version of saphes that produced the result.
    """

    ttr: float
    types: int
    tokens: int
    unit: TokenUnit
    case_folded: bool
    token_source: TokenSource
    pos_filter: str | None
    mattr: float | None
    window: int | None
    saphes_version: str

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the result.

        Returns:
            A plain dict with one key per field.

        Examples:
            >>> result = lexical_diversity(["ház", "kutya", "ház"], unit="lemma")
            >>> result.to_dict()["unit"]
            'lemma'
            >>> result.to_dict()["types"]
            2
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr carrying the length-comparability warning.

        The warning gets its own line, and appears only when there is no MATTR
        to fall back on — MATTR is the length-robust number, so once it is
        present the caveat no longer applies.
        """
        head = (
            f"DiversityResult(ttr={self.ttr:.4f}, types={self.types}, "
            f"tokens={self.tokens}, unit={self.unit!r}"
        )
        if self.mattr is None:
            return (
                f"{head})\n  ! TTR falls as text grows; pass window= to compare lengths"
            )
        return f"{head}, mattr={self.mattr:.4f}, window={self.window})"


def lexical_diversity(
    lemmas: str | Sequence[str],
    *,
    unit: TokenUnit,
    case_fold: bool = False,
    window: int | None = None,
    pos_filter: str | None = None,
) -> DiversityResult:
    """Measure lexical diversity of a token stream.

    ``unit`` is required and has no default. The choice that changes the answer
    is never made silently.

    Args:
        lemmas: A sequence of tokens — lemmas, for the reasons in the module
            docstring. A raw string is accepted only with ``unit="surface"``,
            since a string can only ever be split into surface forms.
        unit: ``"lemma"`` or ``"surface"``. Required. ``"surface"`` is available
            for teaching and for reproducing the raw NLTK-book number, but the
            caller must ask for it deliberately, and the result records it.
        case_fold: Case-fold tokens before counting types. Default ``False`` —
            lemmatisers vary on proper nouns, so this is the caller's call and
            saphes will not do it behind their back. Uses ``str.casefold()``,
            which as a side effect merges Greek final sigma (``ς``) with ``σ``.
        window: If given, also compute :func:`mattr` over this window. Use it
            whenever the texts being compared differ in length.
        pos_filter: A label recording any POS filtering already applied
            upstream, e.g. ``"content words (NOUN/VERB/ADJ/ADV)"``. Provenance
            only; saphes never tags.

    Returns:
        A :class:`DiversityResult` carrying the score, the counts, and the
        parameters used.

    Raises:
        TypeError: If ``unit`` is omitted, or if a raw string is passed with
            ``unit="lemma"``.
        ValueError: If ``unit`` is not a recognised value, if ``window`` is not
            positive, or if the token stream is empty.

    Contract:
        Preconditions:

        - ``lemmas`` must be a ``str`` or a sequence of hashable tokens.
          Hashability is required by the ``set`` at
          diversity.py:409.
        - **If ``window`` is given, the sequence must be ordered.** A
          ``set`` is accepted and returns a plausible number, but MATTR is
          then computed over arbitrary iteration order and is meaningless.
          Nothing raises. A ``set`` also makes the TTR trivially ``1.0``,
          which is at least visibly odd; the MATTR is not.
        - Tokens need not be strings — ``[1, 2, 1]`` returns 0.667 — **but
          only while ``case_fold`` is False.** With ``case_fold=True`` the
          same input raises ``AttributeError: 'int' object has no attribute
          'casefold'`` (implicit, at
          diversity.py:403), so
          an unrelated flag decides whether non-string tokens work.
        - Tokens must be **lemmas** unless ``unit="surface"`` is declared.
          Nothing checks this and nothing can: surface forms produce a
          higher, entirely plausible TTR. The required ``unit`` and the
          refusal of raw strings are the only guards.
        - A generator is accepted; it is materialised once at
          diversity.py:399.

        Guarantees:

        - The TTR lies in ``(0, 1]``.
        - An all-distinct token list gives exactly ``1.0``; one token
          repeated *n* times gives ``1/n``.
        - Empty input raises rather than dividing by zero — including input
          that becomes empty only after a raw string is segmented.
        - ``unit``, ``case_folded``, ``window`` and ``pos_filter`` are all
          recorded on the result, so the number can be interpreted later.
        - ``pos_filter`` is a label only. It never filters anything; saphes
          does not tag.

    Examples:
        >>> lexical_diversity(["ház", "kutya", "ház"], unit="lemma")
        DiversityResult(ttr=0.6667, types=2, tokens=3, unit='lemma')
          ! TTR falls as text grows; pass window= to compare lengths

        The asymmetry the ``unit`` parameter exists to expose. These are the same
        four Hungarian tokens, before and after lemmatisation:

        >>> surface = ["ház", "házak", "házban", "házakat"]
        >>> lexical_diversity(surface, unit="surface").ttr
        1.0
        >>> lexical_diversity(["ház"] * 4, unit="lemma").ttr
        0.25

        The surface number is not 4x richer vocabulary; it is one word inflected
        four ways. That gap is the morphology the lemmas removed.

        A raw string cannot produce lemmas, so it is refused rather than
        quietly measured as something else:

        >>> lexical_diversity(  # doctest: +ELLIPSIS
        ...     "ház házak házban", unit="lemma"
        ... )
        Traceback (most recent call last):
            ...
        TypeError: lexical_diversity() got a raw string with unit='lemma'....

        With ``window=``, MATTR travels alongside — the length-robust number to
        use when comparing corpora of different sizes:

        >>> result = lexical_diversity(["a", "b", "a", "b"], unit="lemma", window=2)
        >>> result.ttr, result.mattr
        (0.5, 1.0)

        The repr drops the length warning once a MATTR is present, because MATTR
        is the number that survives a length difference.
    """
    if unit not in _VALID_UNITS:
        msg = f"unit must be 'lemma' or 'surface', got {unit!r}"
        raise ValueError(msg)
    if window is not None and window <= 0:
        msg = f"window must be positive, got {window}"
        raise ValueError(msg)

    if isinstance(lemmas, str):
        if unit != "surface":
            msg = (
                "lexical_diversity() got a raw string with unit='lemma'. A string "
                "can only be split into surface forms; lemmas must come from "
                "upstream analysis (huspacy, CLTK, a treebank). Pass "
                "unit='surface' to measure surface diversity, or pass a sequence "
                "of lemmas."
            )
            raise TypeError(msg)
        tokens = segment.words(lemmas)
        token_source: TokenSource = "segmented"
    else:
        tokens = list(lemmas)
        token_source = "provided"

    if case_fold:
        tokens = [token.casefold() for token in tokens]

    if not tokens:
        msg = "lexical_diversity needs at least one token, got an empty sequence"
        raise ValueError(msg)

    n_types = len(set(tokens))
    ttr = ttr_from_counts(types=n_types, tokens=len(tokens))

    return DiversityResult(
        ttr=ttr,
        types=n_types,
        tokens=len(tokens),
        unit=unit,
        case_folded=case_fold,
        token_source=token_source,
        pos_filter=pos_filter,
        mattr=None if window is None else mattr(tokens, window=window),
        window=window,
        saphes_version=saphes.__version__,
    )
