"""Mean dependency distance, a metric of syntactic processing load.

    MDD = (1/n) * sum |DD_i|

where *DD_i* is the linear distance between a word and its governor, and *n* is
the number of **dependency pairs** — not the number of words. Liu (2008: 170)
proposed the metric; the formulation implemented here is equation (1) of Jing &
Liu (2015: 163), whose worked example on p. 164 fixes every convention an
implementation can otherwise get wrong.

Worked example, from Jing & Liu (2015: 164)::

    "Mr. Nixon was to leave China today ."

    i  token   head   DD
    1  Mr.     2      1
    2  Nixon   3      1
    3  was     0      -     root: no governor, so no pair
    4  to      3      1
    5  leave   4      1
    6  China   5      1
    7  today   5      2
    8  .       3      -     punctuation: rejected

    MDD = (1 + 1 + 1 + 1 + 1 + 2) / 6 = 1.17

Three conventions follow from that arithmetic, and each is a silently wrong
answer if taken the other way.

**The root is excluded.** It has no governor, so it contributes no term *and*
does not appear in the denominator. Seven words give six pairs, not seven.

**Punctuation is rejected before distances are measured**, which means the
remaining tokens are re-indexed. Jing & Liu report sentence length as "SL (no
punctuations)"; Futrell et al. (2015) drop "any nodes representing punctuation
or root nodes, nor arcs between them". Filtering the *scores* without
re-indexing is a different and larger number — see
:data:`saphes._types.PunctuationPolicy`.

**Distance is the absolute difference of linear positions**, so adjacent words
are at distance 1. Hudson's "intervening words" phrasing, quoted by Jing & Liu,
would make that 0; their own arithmetic does not. Futrell states the operational
rule outright: "the number of words between a head and a dependent, *including
the dependent*".

A text is not a sentence. Jing & Liu's equations (3) and (4) average the
per-sentence means, which is not the same number as pooling every pair in the
text and dividing once. Both are available; see
:data:`saphes._types.DepAggregation`.

**This metric needs a parse, not a token stream.** :func:`saphes.readability.lix`
wants surface forms and :func:`saphes.diversity.lexical_diversity` wants lemmas;
this one wants head indices, and no amount of tokenising will produce them. Use
:mod:`saphes.adapters` to convert a parser's output, or build
:class:`DepToken` sequences yourself.

Note that Futrell et al. (2015) argue *against* summarising with a mean at all,
preferring summed dependency length regressed on sentence length, because
"summary measures that are not a function of length fall prey to inaccuracy due
to mixing dependencies of different lengths". They are cited here for the
arc-length definition, not as support for MDD.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, NamedTuple

import saphes
from saphes._types import DepAggregation, ParseSource, PunctuationPolicy

__all__ = [
    "DepToken",
    "MddResult",
    "dependency_distances",
    "mdd_from_counts",
    "mean_dependency_distance",
]


class DepToken(NamedTuple):
    """One token of a dependency parse.

    A ``NamedTuple`` rather than the frozen dataclass the *result* objects use,
    and deliberately so: this is an **input** contract, and being a plain tuple
    is what lets an adapter emit ``(1, 2, False, "PROPN")`` and a caller pass a
    bare 4-tuple without importing anything from saphes. The result objects stay
    dataclasses, because they need ``to_dict`` and an auditable field list.

    Attributes:
        index: 1-based position of this token in its sentence, as CoNLL-U
            numbers them. Must be contiguous across the sentence.
        head: 1-based position of this token's governor, or ``0`` for the root.
        is_punct: Whether this token is punctuation. Supplied by the caller,
            never guessed — saphes does not know a parser's tagset.
        pos: Part-of-speech tag, or ``None``. Provenance only; the arithmetic
            never reads it.

    Examples:
        >>> DepToken(2, 3, False, "PROPN")
        DepToken(index=2, head=3, is_punct=False, pos='PROPN')
        >>> DepToken(2, 3, False, "PROPN").head
        3
    """

    index: int
    head: int
    is_punct: bool
    pos: str | None


def mdd_from_counts(*, total_distance: int, pairs: int) -> float:
    """Compute mean dependency distance from the two counts directly.

    The arithmetic kernel. Use it when your own pipeline already has the summed
    distance and the pair count. Keyword-only, because two bare ints in this
    order are trivially transposed and the transposition returns a plausible
    number rather than an error.

    Args:
        total_distance: The sum of ``|DD_i|`` over every counted pair.
        pairs: *n*, the number of dependency pairs. Must be positive.

    Returns:
        ``total_distance / pairs``.

    Raises:
        ValueError: If ``pairs`` is not positive, if ``total_distance`` is
            negative, or if ``total_distance`` is less than ``pairs``.

    Contract:
        Preconditions:

        - ``pairs`` must be positive. A sentence of one word has zero pairs,
          and its MDD is undefined rather than zero; this raises instead of
          returning ``0.0``.
        - ``total_distance >= pairs``, because every dependency distance is
          at least 1. Violating it means the two arguments were swapped or
          the distances were computed as "intervening words"; either way it
          raises rather than returning a number below 1.

        Guarantees:

        - The result is always ``>= 1.0``.
        - Total for every input that passes the guards: ``pairs`` is known
          positive by then, so no division by zero is reachable.

    Examples:
        Jing & Liu (2015: 164), "Mr. Nixon was to leave China today .":

        >>> mdd_from_counts(total_distance=7, pairs=6)
        1.1666666666666667
        >>> round(mdd_from_counts(total_distance=7, pairs=6), 2)
        1.17

        A single-word sentence is an error, not a zero:

        >>> mdd_from_counts(total_distance=0, pairs=0)
        Traceback (most recent call last):
            ...
        ValueError: MDD needs at least one dependency pair (n), got 0
    """
    if pairs <= 0:
        msg = f"MDD needs at least one dependency pair (n), got {pairs}"
        raise ValueError(msg)
    if total_distance < 0:
        msg = f"total_distance cannot be negative, got {total_distance}"
        raise ValueError(msg)
    if total_distance < pairs:
        msg = (
            f"total_distance ({total_distance}) is less than pairs ({pairs}), "
            "but every dependency distance is at least 1. The arguments are "
            "probably transposed, or the distances were measured as "
            "intervening words rather than as a difference of positions."
        )
        raise ValueError(msg)
    return total_distance / pairs


def _sentence(parse: Sequence[Any], *, ordinal: int) -> list[DepToken]:
    """Validate one sentence and return it as ``DepToken``s.

    Contract:
        Preconditions:

        - ``parse`` must be a sequence of ``DepToken`` or of 4-tuples.
        - Indices must run 1..n contiguously and in order. A caller who
          removed punctuation but left the original indices in place fails
          here, which is the whole point of the check: the same input with
          the gaps closed up is a legitimately re-indexed sentence, and no
          later stage could tell the two apart.
        - Every head must be 0 or a valid index, and no token may govern
          itself.

        Guarantees:

        - The returned list is in index order and has at least one root.
    """
    tokens: list[DepToken] = []
    for position, raw in enumerate(parse, start=1):
        if isinstance(raw, DepToken):
            token = raw
        elif isinstance(raw, (tuple, list)) and len(raw) == 4:
            token = DepToken(int(raw[0]), int(raw[1]), bool(raw[2]), raw[3])
        else:
            msg = (
                f"sentence {ordinal}, token {position}: expected a DepToken "
                f"or a 4-tuple (index, head, is_punct, pos), got {raw!r}"
            )
            raise TypeError(msg)
        if token.index != position:
            msg = (
                f"sentence {ordinal}: token indices must run 1..n in order, but "
                f"position {position} has index {token.index}. Gaps mean tokens "
                "were removed without re-indexing the rest, which would make "
                "every distance across the gap too large. Pass the parse "
                "unmodified and let punctuation='collapse' drop it, or close "
                "the numbering up yourself."
            )
            raise ValueError(msg)
        tokens.append(token)

    length = len(tokens)
    if length == 0:
        msg = f"sentence {ordinal} is empty; a sentence needs at least one token"
        raise ValueError(msg)
    for token in tokens:
        if not 0 <= token.head <= length:
            msg = (
                f"sentence {ordinal}, token {token.index}: head {token.head} is "
                f"out of range for a sentence of {length} tokens (0 means root)"
            )
            raise ValueError(msg)
        if token.head == token.index:
            msg = (
                f"sentence {ordinal}, token {token.index}: a token cannot be its "
                "own governor; the root is marked with head=0"
            )
            raise ValueError(msg)
    if not any(token.head == 0 for token in tokens):
        msg = (
            f"sentence {ordinal} has no root (no token with head=0), so its "
            "dependency graph contains a cycle and is not a tree"
        )
        raise ValueError(msg)
    return tokens


def _arcs(
    tokens: Sequence[DepToken], *, punctuation: PunctuationPolicy
) -> tuple[list[int], int]:
    """Return the counted distances for one sentence, and the orphaned-arc count.

    Contract:
        Guarantees:

        - Every returned distance is ``>= 1``.
        - The root contributes no distance under any policy.
        - Only ``"collapse"`` can orphan an arc, and it does so only when a
          token's governor is itself punctuation.
    """
    if punctuation == "keep":
        return [abs(t.index - t.head) for t in tokens if t.head != 0], 0

    if punctuation == "ignore":
        # The original index space is retained, so a punctuation governor still
        # has a position and no arc is lost. Only the punctuation tokens' own
        # arcs are skipped.
        return [
            abs(t.index - t.head) for t in tokens if t.head != 0 and not t.is_punct
        ], 0

    # "collapse": drop punctuation and re-index what is left, which is what the
    # literature does. An arc into a dropped token has nowhere to land.
    renumbered: dict[int, int] = {}
    for token in tokens:
        if not token.is_punct:
            renumbered[token.index] = len(renumbered) + 1
    distances: list[int] = []
    orphaned = 0
    for token in tokens:
        if token.is_punct or token.head == 0:
            continue
        if token.head not in renumbered:
            orphaned += 1
            continue
        distances.append(abs(renumbered[token.index] - renumbered[token.head]))
    return distances, orphaned


def dependency_distances(
    parse: Sequence[DepToken] | Sequence[tuple[int, int, bool, str | None]],
    *,
    punctuation: PunctuationPolicy = "collapse",
) -> list[int]:
    """Return the dependency distances of one sentence.

    The visible intermediate between a parse and a score. Reach for it when a
    number looks wrong and you want to see the individual arcs rather than their
    mean, or when you want the distribution rather than its first moment.

    Args:
        parse: One sentence, as :class:`DepToken` values or 4-tuples. Indices
            must run 1..n in order.
        punctuation: How to treat punctuation. Defaults to ``"collapse"``, the
            only policy the literature supports. See
            :data:`saphes._types.PunctuationPolicy`.

    Returns:
        One distance per counted dependency pair, in token order. The root
        contributes nothing, so a well-formed sentence of *n* non-punctuation
        tokens yields *n - 1* distances.

    Raises:
        TypeError: If a token is neither a ``DepToken`` nor a 4-tuple.
        ValueError: If the indices are not contiguous, a head is out of range,
            a token governs itself, or the sentence has no root.

    Contract:
        Preconditions:

        - See :func:`_sentence` — every structural precondition is checked
          and raises, so there is no silent failure mode for a malformed
          sentence.

        Guarantees:

        - Every distance is ``>= 1``.
        - The list is empty exactly when the sentence has no countable pair,
          which is the case for a one-word sentence.

        Silences:

        - Under ``"collapse"``, an arc whose governor is punctuation is
          **dropped without warning**. Use
          :func:`mean_dependency_distance`, whose result records the count as
          ``orphaned_arcs``, if you need to know. In Universal Dependencies
          punctuation is a leaf, so this is normally zero.

    Examples:
        Jing & Liu (2015: 164), "Mr. Nixon was to leave China today .":

        >>> parse = [
        ...     DepToken(1, 2, False, "PROPN"),
        ...     DepToken(2, 3, False, "PROPN"),
        ...     DepToken(3, 0, False, "AUX"),
        ...     DepToken(4, 3, False, "PART"),
        ...     DepToken(5, 4, False, "VERB"),
        ...     DepToken(6, 5, False, "PROPN"),
        ...     DepToken(7, 5, False, "NOUN"),
        ...     DepToken(8, 3, True, "PUNCT"),
        ... ]
        >>> dependency_distances(parse)
        [1, 1, 1, 1, 1, 2]
        >>> sum(dependency_distances(parse))
        7

        The trailing period is last, so dropping it shifts nothing. A *medial*
        comma is what separates the policies:

        >>> clause = [
        ...     DepToken(1, 3, False, "PRON"),
        ...     DepToken(2, 1, True, "PUNCT"),
        ...     DepToken(3, 0, False, "VERB"),
        ... ]
        >>> dependency_distances(clause, punctuation="collapse")
        [1]
        >>> dependency_distances(clause, punctuation="ignore")
        [2]
    """
    tokens = _sentence(parse, ordinal=1)
    distances, _ = _arcs(tokens, punctuation=punctuation)
    return distances


@dataclass(frozen=True, slots=True, repr=False)
class MddResult:
    """A mean dependency distance together with everything that produced it.

    A bare float is unauditable, and MDD has more ways to disagree than LIX
    does: the punctuation policy, the aggregation, and any sentence filter all
    move the number without changing the text. Every one of them travels with
    the score.

    Attributes:
        mdd: The mean dependency distance.
        total_distance: The sum of ``|DD_i|`` over every counted pair.
        pairs: *n*, the number of dependency pairs counted.
        tokens: Non-punctuation tokens in the sentences that contributed.
        sentences: Sentences that contributed at least one pair.
        punctuation: The policy used — ``"collapse"``, ``"ignore"`` or
            ``"keep"``.
        punctuation_dropped: Punctuation tokens excluded from the count.
        orphaned_arcs: Arcs discarded because their governor was punctuation
            that ``"collapse"`` removed. Normally 0 under Universal
            Dependencies, where punctuation is a leaf.
        aggregation: ``"macro"`` (mean of per-sentence means, per Jing & Liu
            equations 3 and 4) or ``"micro"`` (every pair pooled).
        roots: Tokens with ``head=0`` across the contributing sentences. More
            than one per sentence means a fragmented parse.
        skipped_sentences: Sentences that contributed nothing, either because
            they fell below ``min_sentence_length`` or because they had no
            countable pair.
        min_sentence_length: The filter applied, in non-punctuation tokens. 0
            means no filter.
        parse_source: Where the parse came from. Provenance only.
        saphes_version: Version of saphes that produced the result.
    """

    mdd: float
    total_distance: int
    pairs: int
    tokens: int
    sentences: int
    punctuation: PunctuationPolicy
    punctuation_dropped: int
    orphaned_arcs: int
    aggregation: DepAggregation
    roots: int
    skipped_sentences: int
    min_sentence_length: int
    parse_source: ParseSource
    saphes_version: str

    @property
    def avg_sentence_length(self) -> float:
        """Mean non-punctuation tokens per contributing sentence.

        Returns:
            ``tokens / sentences``.

        Examples:
            >>> parse = [(1, 2, False, "DET"), (2, 0, False, "NOUN")]
            >>> mean_dependency_distance([parse]).avg_sentence_length
            2.0
        """
        return self.tokens / self.sentences

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the result.

        Returns:
            A plain dict with one key per field. Properties are not included;
            they are all derivable from the counts.

        Examples:
            >>> parse = [(1, 2, False, "DET"), (2, 0, False, "NOUN")]
            >>> record = mean_dependency_distance([parse]).to_dict()
            >>> record["pairs"]
            1
            >>> record["punctuation"]
            'collapse'
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr showing the score and the counts behind it."""
        return (
            f"MddResult(mdd={self.mdd:.4f}, pairs={self.pairs}, "
            f"sentences={self.sentences}, "
            f"punctuation={self.punctuation!r}, "
            f"aggregation={self.aggregation!r})"
        )


def _is_flat(parses: Sequence[object]) -> bool:
    """Report whether ``parses`` looks like one sentence rather than many.

    Contract:
        Guarantees:

        - True only for a sequence whose first element is a ``DepToken`` or a
          4-tuple beginning with an ``int``, which no sequence-of-sentences
          can be.
    """
    if not parses:
        return False
    first = parses[0]
    if isinstance(first, DepToken):
        return True
    return (
        isinstance(first, tuple)
        and len(first) == 4
        and isinstance(first[0], int)
        and not isinstance(first[0], bool)
    )


def mean_dependency_distance(
    parses: Sequence[Sequence[DepToken]],
    *,
    punctuation: PunctuationPolicy = "collapse",
    aggregation: DepAggregation = "macro",
    min_sentence_length: int = 0,
    require_single_root: bool = False,
    parse_source: ParseSource = "provided",
) -> MddResult:
    """Measure mean dependency distance over a sequence of parsed sentences.

    Implements equation (1) of Jing & Liu (2015: 163) per sentence, and their
    equation (3) to combine sentences into a text-level figure.

    Args:
        parses: Parsed sentences — a sequence of sequences of
            :class:`DepToken`. **Not** a flat token list; passing one raises.
        punctuation: How to treat punctuation. Defaults to ``"collapse"``, the
            policy the literature uses.
        aggregation: ``"macro"`` (the default, Jing & Liu equation 3) or
            ``"micro"``.
        min_sentence_length: Discard sentences with fewer than this many
            non-punctuation tokens. Defaults to 0, meaning no filter. Jing &
            Liu used 3; it is off by default because it is a corpus-preparation
            choice, not a property of the metric.
        require_single_root: Discard sentences with more than one root, as
            Futrell et al. (2015) do. Defaults to ``False``.
        parse_source: Provenance label recorded on the result.

    Returns:
        An :class:`MddResult` carrying the score, every count behind it, and
        every parameter that moved it.

    Raises:
        TypeError: If ``parses`` is a flat sequence of tokens, or a token is
            neither a ``DepToken`` nor a 4-tuple.
        ValueError: If ``parses`` is empty, if ``punctuation`` or
            ``aggregation`` is not a recognised value, if
            ``min_sentence_length`` is negative, if a sentence is malformed, or
            if no sentence survives to contribute a pair.

    Contract:
        Preconditions:

        - ``parses`` must be sentences, not tokens. A flat token list is
          detected and raises, because it would otherwise be read as a
          sequence of one-token sentences and return a confident wrong
          answer.
        - Every sentence must be structurally valid; see
          :func:`dependency_distances`.

        Guarantees:

        - ``mdd >= 1.0`` whenever a result is returned at all.
        - ``pairs``, ``total_distance`` and ``sentences`` describe exactly the
          arcs that produced ``mdd``, so the score is recomputable from the
          record under ``"micro"``.
        - Empty input raises rather than returning ``0.0`` or ``nan``.

        Silences:

        - Sentences with no countable pair — a one-word sentence, or one
          filtered out by ``min_sentence_length`` or
          ``require_single_root`` — are **skipped without warning**. They are
          counted in ``skipped_sentences``, and a caller who does not read
          that field will not learn how much of the text was measured.
        - Non-projective sentences are measured normally, which is correct:
          Jing & Liu note that they "can be represented in the same way".
        - ``pos`` is never read. A mis-tagged token changes nothing unless
          ``is_punct`` is also wrong.

    Examples:
        Jing & Liu (2015: 164), "Mr. Nixon was to leave China today .", whose
        published MDD is 1.17:

        >>> parse = [
        ...     DepToken(1, 2, False, "PROPN"),
        ...     DepToken(2, 3, False, "PROPN"),
        ...     DepToken(3, 0, False, "AUX"),
        ...     DepToken(4, 3, False, "PART"),
        ...     DepToken(5, 4, False, "VERB"),
        ...     DepToken(6, 5, False, "PROPN"),
        ...     DepToken(7, 5, False, "NOUN"),
        ...     DepToken(8, 3, True, "PUNCT"),
        ... ]
        >>> result = mean_dependency_distance([parse])
        >>> round(result.mdd, 2)
        1.17
        >>> result.pairs
        6
        >>> result.total_distance
        7
        >>> result
        MddResult(mdd=1.1667, pairs=6, sentences=1, punctuation='collapse', \
aggregation='macro')

        Zhang & Zhou (2023), "The quick brown fox jumped over the lazy dog.",
        whose published MDD is 2.125:

        >>> fox = [
        ...     DepToken(1, 4, False, "DET"),
        ...     DepToken(2, 4, False, "ADJ"),
        ...     DepToken(3, 4, False, "ADJ"),
        ...     DepToken(4, 5, False, "NOUN"),
        ...     DepToken(5, 0, False, "VERB"),
        ...     DepToken(6, 9, False, "ADP"),
        ...     DepToken(7, 9, False, "DET"),
        ...     DepToken(8, 9, False, "ADJ"),
        ...     DepToken(9, 5, False, "NOUN"),
        ...     DepToken(10, 5, True, "PUNCT"),
        ... ]
        >>> mean_dependency_distance([fox]).mdd
        2.125

        A flat token list is refused rather than read as one-word sentences:

        >>> mean_dependency_distance(parse)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: mean_dependency_distance() takes parsed sentences, not tokens...
    """
    if _is_flat(parses):
        msg = (
            "mean_dependency_distance() takes parsed sentences, not tokens: a "
            "sequence of sequences of DepToken. You passed what looks like a "
            "single sentence — wrap it, as mean_dependency_distance([parse]). "
            "Read as-is it would be a sequence of one-token sentences, none of "
            "which has a dependency pair."
        )
        raise TypeError(msg)
    if not parses:
        msg = "mean_dependency_distance() needs at least one sentence, got none"
        raise ValueError(msg)
    if punctuation not in ("collapse", "ignore", "keep"):
        msg = f"punctuation must be 'collapse', 'ignore' or 'keep', got {punctuation!r}"
        raise ValueError(msg)
    if aggregation not in ("macro", "micro"):
        msg = f"aggregation must be 'macro' or 'micro', got {aggregation!r}"
        raise ValueError(msg)
    if min_sentence_length < 0:
        msg = f"min_sentence_length cannot be negative, got {min_sentence_length}"
        raise ValueError(msg)

    per_sentence: list[float] = []
    total_distance = 0
    pairs = 0
    counted_tokens = 0
    dropped_punct = 0
    orphaned = 0
    roots = 0
    skipped = 0

    for ordinal, parse in enumerate(parses, start=1):
        tokens = _sentence(parse, ordinal=ordinal)
        content = [t for t in tokens if not t.is_punct]
        sentence_roots = sum(1 for t in tokens if t.head == 0)
        if len(content) < min_sentence_length:
            skipped += 1
            continue
        if require_single_root and sentence_roots != 1:
            skipped += 1
            continue
        distances, sentence_orphaned = _arcs(tokens, punctuation=punctuation)
        if not distances:
            skipped += 1
            continue
        per_sentence.append(sum(distances) / len(distances))
        total_distance += sum(distances)
        pairs += len(distances)
        counted_tokens += len(content)
        dropped_punct += len(tokens) - len(content)
        orphaned += sentence_orphaned
        roots += sentence_roots

    if not per_sentence:
        msg = (
            f"no sentence yielded a dependency pair ({skipped} skipped). A "
            "one-word sentence has none, and min_sentence_length or "
            "require_single_root may have removed the rest."
        )
        raise ValueError(msg)

    if aggregation == "macro":
        mdd = sum(per_sentence) / len(per_sentence)
    else:
        mdd = mdd_from_counts(total_distance=total_distance, pairs=pairs)

    return MddResult(
        mdd=mdd,
        total_distance=total_distance,
        pairs=pairs,
        tokens=counted_tokens,
        sentences=len(per_sentence),
        punctuation=punctuation,
        punctuation_dropped=dropped_punct,
        orphaned_arcs=orphaned,
        aggregation=aggregation,
        roots=roots,
        skipped_sentences=skipped,
        min_sentence_length=min_sentence_length,
        parse_source=parse_source,
        saphes_version=saphes.__version__,
    )
