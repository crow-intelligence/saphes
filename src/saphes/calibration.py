"""Calibrating the LIX long-word threshold from a word-length distribution.

Björnsson set the long-word boundary at "more than six letters", fitted to
Swedish. That 6 is hardcoded in every other implementation, and it is wrong for
agglutinative and heavily inflected languages: at threshold 6 the second LIX term
sits near its ceiling for every text, so the index stops discriminating.

The fix is not to guess a new number but to preserve what the term *means* — "the
longest X% of running words" — across languages. That is **equipercentile
matching**: find the threshold whose long-word share in your language is closest
to the share ``>6`` picks out in a Germanic reference.

Two things decide whether the answer is right:

**Token-weighted, never type-weighted.** A frequency list is a list of *types*.
Rare types are long, so a mean length over types runs far above the mean in
running text. LIX counts tokens. :func:`length_curve` therefore takes a
``Mapping[str, int]`` of word to frequency and never a token list — there is no
way to call it that forgets the weights.

**Register matters.** A calibrated threshold is a *default, not a truth*. Before
trusting one on your own texts, recompute the share on a sample of them and check
it lands where the calibration predicts. That is what this module is for; the
shipped numbers are a starting point, not an answer to every question.

The I/O half of the study — downloading corpora, decoding them, and building the
frequency mappings — lives in ``experiments/lix_calibration/`` and is deliberately
not part of the package. Everything here is pure, so its doctests run in CI on a
machine with no corpus.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass

import saphes
from saphes._types import LengthFn, LengthPolicy
from saphes.readability import word_length

__all__ = [
    "HU_DIGRAPHS",
    "LengthCurve",
    "ThresholdMatch",
    "ThresholdRecommendation",
    "collapse_digraphs",
    "length_curve",
    "match_threshold",
    "recommended_threshold",
]

HU_DIGRAPHS: tuple[str, ...] = (
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
"""Hungarian multi-character letters, longest first so ``dzs`` wins over ``dz``.

These are single *letters* in Hungarian orthography, so a character count is not
a letter count. Collapsing them is a **sensitivity check, not better ground
truth** — see :func:`collapse_digraphs` for why.
"""


def collapse_digraphs(word: str, *, digraphs: tuple[str, ...] = HU_DIGRAPHS) -> str:
    """Collapse each orthographic digraph to a single character.

    Each digraph is replaced by its first character, so the result has one
    character per Hungarian *letter*.

    .. warning::

        Only the **length** of the result is meaningful. It is not a word, and
        it is not a transliteration.

    Args:
        word: A lowercase word.
        digraphs: The digraphs to collapse, longest first.

    Returns:
        A string whose length is the letter count.

    Contract:
        Preconditions:

        - ``word`` must be a ``str``; ``bytes`` raises ``TypeError``
          (implicit, from ``str.replace`` at
          calibration.py:151).
        - ``word`` must already be **lowercase**. Matching is
          case-sensitive, so ``"Ország"`` keeps its ``sz`` uncollapsed and
          returns the wrong length with no error. ``hungarian_letter_count``
          case-folds first; this function does not.
        - ``digraphs`` must be ordered **longest first**, or a shorter
          digraph consumes the prefix of a longer one — ``dz`` would eat
          ``dzs``. The default ``HU_DIGRAPHS`` is ordered correctly; a
          caller-supplied tuple is not checked.

        Guarantees:

        - The result is never longer than the input.
        - Collapsing is applied longest-first, so ``dzs`` is one letter, not
          ``dz`` plus ``s``.
        - Replacement **cascades**: each digraph is rewritten in place, so the
          output of one replacement is input to the next. Two known failures
          follow from that, both silent. See the examples.
        - Only the length of the result is meaningful. It is not a word and
          not a transliteration.

    Examples:
        ``sz`` is one letter, so ``ország`` is five letters, not six:

        >>> collapse_digraphs("ország")
        'orság'
        >>> len(collapse_digraphs("ország"))
        5

        Longest-first matters — ``dzs`` is a single letter:

        >>> len(collapse_digraphs("madzag")), len(collapse_digraphs("bridzs"))
        (5, 4)

        And the honest failure case. ``község`` is ``köz`` + ``ség``, so its
        ``zs`` spans a morpheme boundary and is *not* the digraph. Collapsing
        mis-counts it as five letters when it is six:

        >>> len(collapse_digraphs("község"))
        5

        The second failure is the cascade. Replacing ``sz`` with ``s`` after a
        ``z`` manufactures a ``zs`` that was not in the input, and that is then
        collapsed too. ``vízszint`` is ``víz`` + ``szint``, seven letters:

        >>> collapse_digraphs("vízszint")
        'vízint'
        >>> len(collapse_digraphs("vízszint"))
        6

        Both failures are why this stays a sensitivity check.
        :func:`saphes.hungarian.hungarian_letter_count` scans instead of
        rewriting and knows a table of compound seams, so it gets both of these
        right; it is the one to reach for when you want a letter count rather
        than a robustness check on a character count.
    """
    for digraph in digraphs:
        word = word.replace(digraph, digraph[0])
    return word


@dataclass(frozen=True, slots=True, repr=False)
class LengthCurve:
    """A token-weighted word-length distribution, as cumulative shares.

    Attributes:
        label: An identifier for the source this was built from.
        shares: ``(threshold, share)`` pairs, where ``share`` is the proportion
            of running tokens strictly longer than ``threshold``. Ascending by
            threshold.
        tokens: Total running tokens behind the curve.
        types: Distinct word types behind the curve.
        mean_length: Token-weighted mean word length.
        length_policy: How word length was measured.
        min_frequency: Types with a total frequency below this were dropped.
        saphes_version: Version of saphes that produced the curve.
    """

    label: str
    shares: tuple[tuple[int, float], ...]
    tokens: int
    types: int
    mean_length: float
    length_policy: str
    min_frequency: int
    saphes_version: str

    def share_above(self, threshold: int) -> float:
        """Return the share of running tokens longer than ``threshold``.

        Args:
            threshold: The long-word threshold.

        Returns:
            The share, in ``[0, 1]``.

        Raises:
            KeyError: If the curve was not computed at that threshold.

        Contract:
            Preconditions:

            - ``threshold`` must be one of the thresholds this curve was
              built with, i.e. ``0..max_threshold``. Anything else raises
              ``KeyError`` naming the covered range — it does not
              extrapolate or return zero.

            Guarantees:

            - Linear scan, not a lookup; curves are short by construction.

        Examples:
            >>> curve = length_curve({"a": 10, "abcd": 5}, label="demo")
            >>> curve.share_above(1)
            0.3333333333333333
        """
        for candidate, share in self.shares:
            if candidate == threshold:
                return share
        msg = (
            f"curve {self.label!r} has no share at threshold {threshold}; "
            f"it covers {self.shares[0][0]}..{self.shares[-1][0]}"
        )
        raise KeyError(msg)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the curve.

        Returns:
            A plain dict with one key per field.

        Examples:
            >>> curve = length_curve({"a": 10, "abcd": 5}, label="demo")
            >>> curve.to_dict()["label"]
            'demo'
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr showing the label and the headline statistics."""
        return (
            f"LengthCurve({self.label!r}, tokens={self.tokens:,}, "
            f"types={self.types:,}, mean_length={self.mean_length:.3f})"
        )


@dataclass(frozen=True, slots=True, repr=False)
class ThresholdMatch:
    """The result of equipercentile-matching one curve against another.

    Attributes:
        threshold: The matched threshold for the target language.
        target_share: The target's long-word share at ``threshold``.
        reference_share: The reference's share at ``reference_threshold``.
        reference_threshold: The threshold matched against, normally 6.
        residual: ``abs(target_share - reference_share)``. How close the match
            actually is — a large residual means no threshold reproduces the
            reference share well.
        bracket: The two consecutive thresholds whose shares the reference share
            falls between. Almost always two different numbers on real data —
            an exact hit is a coincidence — so use :attr:`is_boundary` rather
            than this to judge whether the answer is contested.
        runner_up: The next-best threshold after ``threshold``.
        runner_up_residual: How far the runner-up misses by.
        target_label: Label of the target curve.
        reference_label: Label of the reference curve.
        table: The whole target curve, per the study's brief — the deliverable
            is "here is the share at every threshold, and here is why we chose
            this one", so the choice stays revisable.
    """

    threshold: int
    target_share: float
    reference_share: float
    reference_threshold: int
    residual: float
    bracket: tuple[int, int]
    runner_up: int
    runner_up_residual: float
    target_label: str
    reference_label: str
    table: tuple[tuple[int, float], ...]

    @property
    def is_boundary(self) -> bool:
        """Whether the runner-up matches nearly as well as the winner.

        A bare "the reference share falls between two thresholds" would be true
        of essentially every real dataset, since an exact hit is a coincidence.
        What actually matters is whether the second-best threshold is close
        enough that the choice between them is near-arbitrary.

        Returns:
            ``True`` when the runner-up's residual is no more than twice the
            winner's — i.e. the answer is contested and should be reported with
            its bracket rather than as a settled integer.

        Examples:
            A contested case. The reference share of 0.45 sits almost exactly
            between the target's 0.5 and 0.4, so 5 and 6 are equally defensible:

            >>> target = length_curve({"a" * n: 10 for n in range(1, 11)},
            ...                       label="target")
            >>> ref = length_curve({"ab": 11, "abcd": 9}, label="ref")
            >>> match = match_threshold(target, ref, reference_threshold=3)
            >>> match.reference_share
            0.45
            >>> match.bracket
            (5, 6)
            >>> match.is_boundary
            True

            A settled case. Here the reference share is matched exactly, and the
            nearest alternative is a long way off:

            >>> ref2 = length_curve({"a" * n: 10 for n in range(1, 6)},
            ...                     label="ref2")
            >>> settled = match_threshold(target, ref2, reference_threshold=3)
            >>> settled.threshold, settled.residual
            (6, 0.0)
            >>> settled.is_boundary
            False
        """
        return self.runner_up_residual <= 2 * self.residual

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the match.

        Returns:
            A plain dict with one key per field.

        Examples:
            >>> target = length_curve({"a" * n: 10 for n in range(1, 11)},
            ...                       label="target")
            >>> ref = length_curve({"a" * n: 10 for n in range(1, 6)},
            ...                    label="ref")
            >>> match = match_threshold(target, ref, reference_threshold=3)
            >>> match.to_dict()["threshold"]
            6
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr showing the match and how close it is."""
        return (
            f"ThresholdMatch(threshold={self.threshold}, "
            f"bracket={self.bracket}, "
            f"target_share={self.target_share:.4f}, "
            f"reference_share={self.reference_share:.4f}, "
            f"residual={self.residual:.4f})"
        )


def length_curve(
    counts: Mapping[str, int],
    *,
    label: str,
    max_threshold: int = 20,
    min_frequency: int = 5,
    length_policy: LengthPolicy | LengthFn = "nfc",
) -> LengthCurve:
    """Build a token-weighted cumulative word-length curve from frequencies.

    Args:
        counts: A mapping of word to **frequency in running text**. Not a token
            list, and not a set of types.
        label: An identifier for the source, recorded on the result.
        max_threshold: Compute shares for every threshold from 0 to this.
        min_frequency: Drop types whose total frequency is below this, to shed
            typo noise. Applied *after* any merging the caller did, so a word
            split across several rows is judged on its total.
        length_policy: How to measure word length. See
            :func:`saphes.readability.word_length`. Pass
            :func:`hungarian_letter_count` for the digraph sensitivity check.

    Returns:
        A :class:`LengthCurve`.

    Raises:
        ValueError: If ``max_threshold`` is negative, if ``min_frequency`` is
            negative, if any count is negative, or if nothing survives the
            frequency filter.

    Contract:
        Preconditions:

        - ``counts`` must be a **Mapping**, not a sequence of pairs. A list
          of ``(word, count)`` tuples — a natural reading of the name —
          raises ``AttributeError: 'list' object has no attribute 'items'``
          (implicit, at
          calibration.py:475).
        - Keys must be strings, or ``word_length`` raises ``TypeError``.
        - Values must be **token frequencies in running text**, not ones.
          This is the study's likeliest silent failure and the signature is
          the only guard: a mapping of all-1 counts is perfectly valid input
          and yields the type-weighted curve, which runs far above the
          truth while still looking plausible.
        - Values should be ``int``. Floats are **not** rejected — they pass
          the comparisons and the addition — so a float frequency makes
          ``LengthCurve.tokens`` a float despite its ``int`` annotation.
        - ``length_policy``, if callable, must return an int; a
          zero-returning policy silently drops the word at
          calibration.py:482.

        Guarantees:

        - Shares are non-increasing as the threshold rises.
        - Every share lies in ``[0, 1]``; the share above 0 is exactly 1.0,
          since every surviving word has at least one letter.
        - Weighting is by token, never by type. **Passing all-1 counts
          yields the type-weighted curve, which is not what you want** —
          rare types are long, so it runs far above the truth while still
          looking plausible.
        - A curve that would be empty raises rather than returning zeros, so
          an over-aggressive ``min_frequency`` cannot pass unnoticed.

        Silences:

        - Words whose measured length is zero are skipped without record at
          calibration.py:482 — they count toward neither ``tokens``
          nor ``types``. With the built-in policies only the empty string
          does this; with a custom policy it may not be.

    Examples:
        Three types, twenty running tokens:

        >>> counts = {"a": 10, "abcd": 5, "abcdefghi": 5}
        >>> curve = length_curve(counts, label="demo")
        >>> curve.tokens, curve.types
        (20, 3)
        >>> curve.mean_length          # (1*10 + 4*5 + 9*5) / 20
        3.75
        >>> curve.share_above(1)       # 10 of 20 tokens are longer than 1
        0.5
        >>> curve.share_above(4)       # 5 of 20
        0.25

        The type-weighting trap, made visible. The same three words with their
        frequencies discarded give a completely different — and wrong — answer:

        >>> flat = length_curve(dict.fromkeys(counts, 1), label="wrong",
        ...                     min_frequency=1)
        >>> flat.share_above(1)        # 2 of 3 "tokens"
        0.6666666666666666
        >>> round(flat.mean_length, 4)
        4.6667
    """
    if max_threshold < 0:
        msg = f"max_threshold cannot be negative, got {max_threshold}"
        raise ValueError(msg)
    if min_frequency < 0:
        msg = f"min_frequency cannot be negative, got {min_frequency}"
        raise ValueError(msg)

    by_length: dict[int, int] = {}
    tokens = 0
    types = 0
    for word, frequency in counts.items():
        if frequency < 0:
            msg = f"count for {word!r} is negative: {frequency}"
            raise ValueError(msg)
        if frequency < min_frequency:
            continue
        length = word_length(word, policy=length_policy)
        if length == 0:
            continue
        by_length[length] = by_length.get(length, 0) + frequency
        tokens += frequency
        types += 1

    if tokens == 0:
        msg = (
            f"no tokens survived the filter for {label!r} "
            f"(min_frequency={min_frequency}); the curve would be empty"
        )
        raise ValueError(msg)

    shares = tuple(
        (
            threshold,
            sum(count for length, count in by_length.items() if length > threshold)
            / tokens,
        )
        for threshold in range(max_threshold + 1)
    )
    mean_length = sum(length * count for length, count in by_length.items()) / tokens

    return LengthCurve(
        label=label,
        shares=shares,
        tokens=tokens,
        types=types,
        mean_length=mean_length,
        length_policy=_policy_label(length_policy),
        min_frequency=min_frequency,
        saphes_version=saphes.__version__,
    )


def match_threshold(
    target: LengthCurve,
    reference: LengthCurve,
    *,
    reference_threshold: int = 6,
) -> ThresholdMatch:
    """Find the target threshold that reproduces the reference's long-word share.

    Equipercentile matching. Rather than keeping Björnsson's literal 6, this
    keeps what the second LIX term *means*: the longest X% of running words.

    Args:
        target: The curve for the language being calibrated.
        reference: The curve for the language the threshold was fitted on,
            normally a Germanic one.
        reference_threshold: The threshold to match at in ``reference``.

    Returns:
        A :class:`ThresholdMatch`, carrying the whole target curve alongside the
        chosen threshold.

    Raises:
        KeyError: If ``reference`` has no share at ``reference_threshold``.

    Contract:
        Preconditions:

        - ``reference`` must have been computed out to at least
          ``reference_threshold``, or ``share_above`` raises ``KeyError``.
        - Both curves should have been built with the **same**
          ``length_policy`` and ``min_frequency``. Nothing checks this, and
          mismatched curves compare cleanly and produce a wrong threshold.
          Both parameters are recorded on each ``LengthCurve`` so the
          mismatch is at least auditable after the fact.
        - The two curves must come from comparable corpora for the result to
          mean anything. This is a methodological precondition the code
          cannot enforce.

        Guarantees:

        - The chosen threshold minimises
          ``abs(target_share - reference_share)`` over the target curve;
          ties go to the lower threshold.
        - ``bracket`` spans the two consecutive thresholds the reference
          share falls between, so a result sitting on a boundary is visible
          rather than rounded away.
        - ``runner_up`` is the second-ranked threshold, or the winner itself
          when the target curve has exactly one point (
          calibration.py:576
          ). In that degenerate case ``is_boundary`` compares the winner
          with itself and reports ``True``.
        - The whole target curve travels on ``table``, so the choice stays
          revisable.

    Examples:
        A target language whose words run longer than the reference's needs a
        higher threshold to select the same share of running text:

        >>> target = length_curve({"a" * n: 10 for n in range(1, 11)},
        ...                       label="long-words")
        >>> ref = length_curve({"a" * n: 10 for n in range(1, 6)},
        ...                    label="short-words")
        >>> match = match_threshold(target, ref, reference_threshold=3)
        >>> match.reference_share      # two fifths of the reference is "long"
        0.4
        >>> match.threshold            # the threshold selecting two fifths here
        6
        >>> match.residual
        0.0

        Keeping the literal 3 would have selected 70% of the target's running
        words instead of 40% — the term would mean something different:

        >>> target.share_above(3)
        0.7
    """
    reference_share = reference.share_above(reference_threshold)

    ranked = sorted(
        target.shares,
        key=lambda pair: (abs(pair[1] - reference_share), pair[0]),
    )
    threshold, target_share = ranked[0]
    runner_up, runner_up_share = ranked[1] if len(ranked) > 1 else ranked[0]

    lower = [t for t, share in target.shares if share >= reference_share]
    upper = [t for t, share in target.shares if share <= reference_share]
    bracket = (max(lower) if lower else threshold, min(upper) if upper else threshold)

    return ThresholdMatch(
        threshold=threshold,
        target_share=target_share,
        reference_share=reference_share,
        reference_threshold=reference_threshold,
        residual=abs(target_share - reference_share),
        bracket=bracket,
        runner_up=runner_up,
        runner_up_residual=abs(runner_up_share - reference_share),
        target_label=target.label,
        reference_label=reference.label,
        table=target.shares,
    )


@dataclass(frozen=True, slots=True, repr=False)
class ThresholdRecommendation:
    """A calibrated long-word threshold, with everything behind it.

    Attributes:
        language: ISO 639 code of the calibrated language.
        threshold: The recommended ``long_word_threshold``.
        bracket: The two thresholds the reference share falls between.
        matched_share: The language's long-word share at ``threshold``.
        reference_share: The reference language's share at its own threshold.
        reference_id: Which corpus supplied the reference share.
        reference_threshold: The threshold matched at in the reference.
        residual: How far the match misses by.
        runner_up: The next-best threshold.
        runner_up_residual: How far the runner-up misses by.
        is_boundary: Whether the runner-up matches nearly as well, making the
            choice near-arbitrary. ``False`` means the winner is clear.
        agreement: ``(source, threshold)`` for every curve in the study, matched
            independently. Unanimity is the real evidence; a single number from
            a single corpus would not be.
        sources: The corpora behind the recommendation.
        caveats: Why this is a default and not a truth. Read them.
        saphes_version: Version of saphes carrying the calibration.
    """

    language: str
    threshold: int
    bracket: tuple[int, int]
    matched_share: float
    reference_share: float
    reference_id: str
    reference_threshold: int
    residual: float
    runner_up: int
    runner_up_residual: float
    is_boundary: bool
    agreement: tuple[tuple[str, int], ...]
    sources: tuple[str, ...]
    caveats: tuple[str, ...]
    saphes_version: str

    def __int__(self) -> int:
        """Return the threshold, so the object can be used where an int is."""
        return self.threshold

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the recommendation.

        Returns:
            A plain dict with one key per field.

        Examples:
            >>> recommended_threshold("hu").to_dict()["language"]
            'hu'
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr showing the threshold and how well supported it is."""
        return (
            f"ThresholdRecommendation({self.language!r}, "
            f"threshold={self.threshold}, bracket={self.bracket}, "
            f"matched_share={self.matched_share:.4f}, "
            f"reference_share={self.reference_share:.4f}, "
            f"contested={self.is_boundary})"
        )


def recommended_threshold(language: str) -> ThresholdRecommendation:
    """Look up the calibrated long-word threshold for a language.

    The number ships; the corpus does not. The study that produced it is in
    ``experiments/lix_calibration/``, and the full provenance record — every
    curve at every threshold — is in that directory's ``results/``.

    ``lix`` deliberately takes **no** ``language=`` parameter. Pass the threshold
    explicitly, so the choice is visible at the call site rather than dispatched
    on behind your back.

    Args:
        language: ISO 639 code, e.g. ``"hu"``.

    Returns:
        A :class:`ThresholdRecommendation`.

    Raises:
        KeyError: If the language has not been calibrated. The message lists
            those that have.

    Examples:
        >>> hu = recommended_threshold("hu")
        >>> hu.threshold
        8
        >>> int(hu)
        8

        Hungarian at threshold 8 selects about the same share of running words
        that Björnsson's 6 selects in Swedish — which is what the second LIX
        term is supposed to mean:

        >>> round(hu.matched_share, 3), round(hu.reference_share, 3)
        (0.273, 0.257)

        Six independently computed curves — two Hungarian corpora nineteen years
        apart, three sampling strata, and a digraph-aware variant — all choose
        the same threshold:

        >>> sorted({t for _, t in hu.agreement})
        [8]
        >>> hu.is_boundary
        False

        Use it explicitly. ``kertben`` is seven letters — long under Björnsson's
        Swedish threshold, ordinary under the Hungarian one:

        >>> from saphes import lix
        >>> text = "A kutyák megálltak a kertben és vártak."
        >>> round(lix(text, sentences=1).long_word_share, 3)
        0.286
        >>> tuned = lix(text, sentences=1, long_word_threshold=int(hu))
        >>> round(tuned.long_word_share, 3)
        0.143

        Uncalibrated languages raise rather than guess:

        >>> recommended_threshold("grc")
        Traceback (most recent call last):
            ...
        KeyError: "no calibration for 'grc'; calibrated languages: hu"

    Contract:
        Preconditions:

        - ``language`` must be a key of the shipped calibration table.
          Unknown languages raise ``KeyError`` listing what is available —
          deliberately, rather than falling back to Björnsson's 6, which
          would be a silent wrong answer for exactly the languages this
          package exists to serve.
        - Lookup is exact and case-sensitive: ``"HU"`` and ``"hun"`` both
          raise.

        Guarantees:

        - Pure and offline. The number ships in the package; no corpus and
          no network are involved.
        - Every field is coerced to its declared type on the way out, so a
          malformed generated record fails here rather than downstream.

        Silences:

        - Depends on ``saphes.datasets._lix_calibration``, which is
          **generated** by ``experiments/lix_calibration/scripts/run.py``
          and imported lazily at
          calibration.py:757.
          Nothing verifies that the shipped literal matches the committed
          JSON it was produced from, and nothing can — the corpora are not
          distributed. A hand-edit to that module would be invisible here;
          the guard against it is that the same numbers also live in
          ``findings.md`` and ``results/lix_calibration.json``.
    """
    from saphes.datasets._lix_calibration import CALIBRATIONS

    if language not in CALIBRATIONS:
        msg = (
            f"no calibration for {language!r}; calibrated languages: "
            f"{', '.join(sorted(CALIBRATIONS))}"
        )
        raise KeyError(msg)

    record = CALIBRATIONS[language]
    return ThresholdRecommendation(
        language=language,
        threshold=int(record["threshold"]),
        bracket=tuple(record["bracket"]),
        matched_share=float(record["matched_share"]),
        reference_share=float(record["reference_share"]),
        reference_id=str(record["reference_id"]),
        reference_threshold=int(record["reference_threshold"]),
        residual=float(record["residual"]),
        runner_up=int(record["runner_up"]),
        runner_up_residual=float(record["runner_up_residual"]),
        is_boundary=bool(record["is_boundary"]),
        agreement=tuple(record["agreement"]),
        sources=tuple(record["sources"]),
        caveats=tuple(record["caveats"]),
        saphes_version=saphes.__version__,
    )


def _policy_label(policy: LengthPolicy | LengthFn) -> str:
    """Return the recorded name of a length policy.

    A duplicate of ``readability._policy_label``, kept local so that
    ``calibration`` does not import a private name from a sibling module. See
    that copy for the ``__qualname__`` fallback and why it matters.

    Contract:
        Guarantees:

        - Total: returns a string for any input.

        Silences:

        - A missing ``__qualname__`` falls back to ``repr`` at
          calibration.py:807,
          so the recorded ``LengthCurve.length_policy`` can embed an address
          and differ between processes.
    """
    if callable(policy):
        name = getattr(policy, "__qualname__", None) or repr(policy)
        return f"custom:{name}"
    return str(policy)
