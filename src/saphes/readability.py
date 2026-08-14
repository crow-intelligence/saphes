"""LIX readability, with the long-word threshold as a parameter.

    LIX = A/B + (C * 100)/A

where *A* is the number of words, *B* the number of sentences, and *C* the number
of long words. A **long word is one longer than the threshold** — so the default
``long_word_threshold=6`` counts words of **seven letters or more**, per
Björnsson's "more than six letters". That off-by-one is a known source of
disagreement between implementations, so it is stated here, in
:func:`lix`'s docstring, and in a doctest.

Worked example, computed by hand::

    "The cat sat on it. Complicated sentences generally frighten us."

    A = 10  (The cat sat on it Complicated sentences generally frighten us)
    B = 2   (two sentences)
    C = 4   (Complicated=11, sentences=9, generally=9, frighten=8; all > 6)

    LIX = 10/2 + (4 * 100)/10 = 5.0 + 40.0 = 45.0

**LIX requires surface forms, never lemmas.** Word length *is* the signal here:
Hungarian ``házakban`` is 8 characters, its lemma ``ház`` is 3. Lemmatising before
LIX destroys the measurement, and does so most severely in exactly the
agglutinative languages the threshold parameter exists to serve. This is the
opposite of what :mod:`saphes.diversity` requires — see that module, and never
feed one token stream to both.

The default 6 comes from Björnsson's Swedish original and is wrong for the
languages this package was built for: at threshold 6 roughly 39% of running
Hungarian tokens count as "long" against a Germanic norm nearer 20-25%, so the
index saturates and stops discriminating. Raise the threshold and it works again.
That is the whole point of the parameter.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

import saphes
from saphes import segment
from saphes._types import (
    LengthFn,
    LengthPolicy,
    LixBand,
    Sentencer,
    SentenceSource,
    TokenSource,
)

if TYPE_CHECKING:
    from typing import Literal

__all__ = [
    "LIX_BANDS",
    "LixResult",
    "interpret_lix",
    "lix",
    "lix_from_counts",
    "rix",
    "word_length",
]

LIX_BANDS: tuple[tuple[float, LixBand], ...] = (
    (30.0, "very easy"),
    (40.0, "easy"),
    (50.0, "standard"),
    (60.0, "difficult"),
    (float("inf"), "very difficult"),
)
"""Björnsson's interpretation bands as ``(exclusive upper bound, label)`` pairs.

Calibrated for **Swedish and Germanic prose at a long-word threshold of 6**.
Published versions of this table differ from one another in their boundaries,
which is precisely why the constant is exposed rather than buried: substitute
your own if you are working from a different source.
"""

_VALID_POLICIES = frozenset(("nfc", "graphemes", "codepoints"))

# The one threshold at which Björnsson's bands mean anything. Re-calibrating the
# threshold rescales the ``100*C/A`` term by construction, which moves the whole
# score off the scale the bands were fitted to.
_CALIBRATED_THRESHOLD = 6


def word_length(word: str, *, policy: LengthPolicy | LengthFn = "nfc") -> int:
    """Count the letters of ``word`` under a stated length policy.

    Args:
        word: The word to measure.
        policy: ``"nfc"`` normalises to NFC first, then counts code points (the
            default). ``"graphemes"`` additionally drops combining marks that NFC
            could not compose. ``"codepoints"`` is raw ``len()``. A callable is
            used as-is, and is the seam for grapheme-cluster or
            orthography-aware counting.

    Returns:
        The number of letters.

    Raises:
        ValueError: If ``policy`` is not a recognised name or a callable.

    Contract:
        Preconditions:
            - ``word`` must be a ``str`` for the three built-in policies.
              ``bytes`` or ``None`` raises ``TypeError`` (implicit, from
              ``unicodedata.normalize`` at
              readability.py:160).
            - A callable ``policy`` **must return an int**, and this is not
              checked — its value is returned unaltered (
              readability.py:151). A callable returning a ``str``
              succeeds here and then fails in ``lix`` at the long-word
              comparison with ``TypeError: '>' not supported between instances
              of 'str' and 'int'``, which names neither the policy nor the word.
            - A callable ``policy`` is trusted entirely: whatever it raises
              propagates unchanged.

        Guarantees:
            - ``word_length("") == 0`` under every built-in policy.
            - ``"nfc"`` is idempotent on already-composed text, so it is free
              for callers who already normalise.
            - The built-in policies are pure and allocate no more than one
              normalised copy of the word.

    Examples:
        >>> word_length("housing")
        7

        NFC is the default because decomposed input otherwise inflates every
        length — and it inflates most for the polytonic Greek and accented
        Hungarian this package targets, silently doubling LIX with no error:

        >>> import unicodedata
        >>> decomposed = unicodedata.normalize("NFD", "ἐϋκνήμιδες")
        >>> word_length(decomposed, policy="codepoints")
        13
        >>> word_length(decomposed)
        10

        Custom callables let you count letters rather than characters, which is
        what Hungarian orthography actually means by "letter":

        >>> word_length("ország", policy=lambda w: len(w) - w.count("sz"))
        5
    """
    if callable(policy):
        return policy(word)
    if policy == "codepoints":
        return len(word)
    if policy not in _VALID_POLICIES:
        msg = (
            "policy must be 'nfc', 'graphemes', 'codepoints', or a callable, "
            f"got {policy!r}"
        )
        raise ValueError(msg)
    composed = unicodedata.normalize("NFC", word)
    if policy == "graphemes":
        return sum(1 for char in composed if not unicodedata.combining(char))
    return len(composed)


def lix_from_counts(*, words: int, sentences: int, long_words: int) -> float:
    """Compute LIX from the three counts directly.

    The arithmetic kernel. Use it when you already have *A*, *B* and *C* from
    your own pipeline and want nothing tokenised or segmented on your behalf.
    Keyword-only, because three bare ints are trivially transposed.

    Args:
        words: *A*, the number of words. Must be positive.
        sentences: *B*, the number of sentences. Must be positive.
        long_words: *C*, the number of words longer than the threshold.

    Returns:
        The LIX score, ``A/B + 100*C/A``.

    Raises:
        ValueError: If ``words`` or ``sentences`` is not positive, if
            ``long_words`` is negative, or if ``long_words`` exceeds ``words``.

    Contract:
        Preconditions:
            - All three arguments must be ``int``. Every constraint is checked
              explicitly and raises ``ValueError`` with a message naming the
              count, so this function has no silent failure mode for integer
              input.
            - Floats are *not* rejected: the comparisons and the arithmetic all
              accept them, so ``words=10.5`` returns a score rather than
              raising. Only the callers guarantee integers.

        Guarantees:
            - The result is never negative.
            - ``long_words == words`` makes the second term exactly ``100.0``.
            - Total for every input that passes the guards — no division by
              zero is reachable, since ``words`` and ``sentences`` are known
              positive by then.

    Examples:
        >>> lix_from_counts(words=10, sentences=2, long_words=4)
        45.0

        Empty input is an error, not a zero and not a NaN:

        >>> lix_from_counts(words=0, sentences=1, long_words=0)
        Traceback (most recent call last):
            ...
        ValueError: LIX needs at least one word (A), got 0
    """
    if words <= 0:
        msg = f"LIX needs at least one word (A), got {words}"
        raise ValueError(msg)
    if sentences <= 0:
        msg = f"LIX needs at least one sentence (B), got {sentences}"
        raise ValueError(msg)
    if long_words < 0:
        msg = f"long_words (C) cannot be negative, got {long_words}"
        raise ValueError(msg)
    if long_words > words:
        msg = f"long_words (C={long_words}) cannot exceed words (A={words})"
        raise ValueError(msg)
    return words / sentences + 100.0 * long_words / words


def interpret_lix(score: float) -> LixBand:
    """Map a LIX score to Björnsson's interpretation band.

    Args:
        score: A LIX score.

    Returns:
        The band label from :data:`LIX_BANDS`.

    Contract:
        Preconditions:
            - ``score`` must be a real, non-NaN number. **NaN is not rejected
              and does not raise**: every ``score < upper`` comparison is False
              for NaN, so the loop at
              readability.py:268 falls through and the
              function returns ``"very difficult"``. A score produced by
              ``lix_from_counts`` can never be NaN, but a hand-built or
              deserialised one can.
            - Negative scores are likewise accepted and band as ``"very easy"``.
              LIX is non-negative by construction, so a negative input means
              something upstream is wrong, and this function will not say so.

        Guarantees:
            - Total for every float: the final entry of ``LIX_BANDS`` has an
              infinite bound, so some label is always returned.
            - Calibrated for Swedish/Germanic prose at ``long_word_threshold=6``
              only. At any other threshold the score is no longer on this scale;
              ``LixResult.band`` returns ``None`` there rather than mislabel it.
            - Reads the module-level ``LIX_BANDS``, which is public and
              rebindable. A caller who replaces it changes this function's
              output process-wide.

    Examples:
        >>> interpret_lix(45.0)
        'standard'
        >>> interpret_lix(19.0)
        'very easy'
        >>> interpret_lix(72.0)
        'very difficult'
    """
    for upper, label in LIX_BANDS:
        if score < upper:
            return label
    return LIX_BANDS[-1][1]  # pragma: no cover - the final bound is infinite


@dataclass(frozen=True, slots=True, repr=False)
class LixResult:
    """A LIX score together with everything that produced it.

    A bare float is unauditable. Published LIX numbers disagree because
    implementations count words, sentences and long words differently, so every
    count and every parameter travels with the score.

    Attributes:
        score: The LIX score, ``A/B + 100*C/A``.
        words: *A*, the number of words counted.
        sentences: *B*, the number of sentences counted.
        long_words: *C*, the number of words longer than the threshold.
        long_word_threshold: The threshold used. A long word is *longer than*
            this, so 6 means seven letters or more.
        length_policy: How word length was measured: ``"nfc"``, ``"graphemes"``,
            ``"codepoints"``, or ``"custom:<qualname>"``.
        unit: Always ``"surface"``. LIX is undefined on lemmas; this field is the
            contract marker that says so in any serialised table.
        sentence_source: Where *B* came from — ``"segmented"`` (split from raw
            text), ``"presegmented"`` (a list of sentences), or ``"explicit"``
            (a count the caller supplied).
        sentencer: Qualified name of the splitter used, or ``None`` when *B* did
            not come from one.
        token_source: ``"provided"`` if the caller passed tokens,
            ``"segmented"`` if saphes split them out of raw text.
        dropped_empty: Empty or whitespace-only tokens discarded before counting.
        saphes_version: Version of saphes that produced the result.
    """

    score: float
    words: int
    sentences: int
    long_words: int
    long_word_threshold: int
    length_policy: str
    unit: Literal["surface"]
    sentence_source: SentenceSource
    sentencer: str | None
    token_source: TokenSource
    dropped_empty: int
    saphes_version: str

    @property
    def rix(self) -> float:
        """RIX: long words per sentence, ``C/B``.

        Returns:
            The RIX score.

        Examples:
            >>> text = "The cat sat on it. Complicated sentences generally frighten us."
            >>> lix(text).rix
            2.0
        """
        return self.long_words / self.sentences

    @property
    def avg_sentence_length(self) -> float:
        """The first LIX term, ``A/B``: mean words per sentence.

        Returns:
            Mean sentence length in words.
        """
        return self.words / self.sentences

    @property
    def long_word_share(self) -> float:
        """The second LIX term as a proportion, ``C/A``.

        This is the quantity the threshold calibration matches across languages:
        "the longest X% of running words".

        Returns:
            The share of words that are long, in ``[0, 1]``.
        """
        return self.long_words / self.words

    @property
    def band(self) -> LixBand | None:
        """Björnsson's interpretation band, or ``None`` off the calibrated scale.

        Returns:
            The band label when ``long_word_threshold == 6``, else ``None``.
            Re-calibrating the threshold rescales the ``100*C/A`` term by
            construction, so the score is no longer on the scale Björnsson fitted
            his labels to — handing out a Swedish label for a Hungarian number at
            threshold 8 would be exactly the silent wrongness this package exists
            to prevent. Call :func:`interpret_lix` directly if you want one
            anyway.

        Examples:
            >>> text = "The cat sat on it. Complicated sentences generally frighten us."
            >>> lix(text).band
            'standard'
            >>> lix(text, long_word_threshold=8).band is None
            True
        """
        if self.long_word_threshold != _CALIBRATED_THRESHOLD:
            return None
        return interpret_lix(self.score)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable dict of the result.

        Returns:
            A plain dict with one key per field. Properties are not included;
            they are all derivable from the counts.

        Examples:
            >>> result = lix("The cat sat on it. Complicated sentences frighten us.")
            >>> result.to_dict()["long_word_threshold"]
            6
            >>> result.to_dict()["unit"]
            'surface'
        """
        return asdict(self)

    def __repr__(self) -> str:
        """Return a repr showing the score and the counts behind it."""
        return (
            f"LixResult(score={self.score:.2f}, A={self.words}, "
            f"B={self.sentences}, C={self.long_words}, "
            f"threshold={self.long_word_threshold}, "
            f"sentences={self.sentence_source!r})"
        )


def _policy_label(policy: LengthPolicy | LengthFn) -> str:
    """Return the recorded name of a length policy.

    Contract:
        Guarantees:
            - Total: returns a string for any input, callable or not.

        Silences:
            - A missing ``__qualname__`` is masked by the ``getattr`` default at
              readability.py:422,
              falling back to ``repr``. Callables without a qualname —
              ``functools.partial``, a class instance with ``__call__``, a
              builtin — therefore record something like
              ``custom:functools.partial(<built-in function len>)`` instead of a
              name. The label still identifies the policy, but it is not stable
              across processes, since a default ``repr`` embeds an address. That
              matters here because the label is provenance: it is written into
              ``LixResult.length_policy`` and serialised by ``to_dict``.
    """
    if callable(policy):
        name = getattr(policy, "__qualname__", None) or repr(policy)
        return f"custom:{name}"
    return str(policy)


def _count_sentences(
    text: str | Sequence[str],
    sentences: int | Sequence[str] | None,
    sentencer: Sentencer | None,
    *,
    is_raw: bool,
) -> tuple[int, SentenceSource, str | None]:
    """Resolve *B* from whichever of the three sources the caller used.

    Contract:
        Preconditions:
            - ``is_raw`` must be ``True`` exactly when ``text`` is a ``str``.
              The caller computes both, and this function trusts the pairing:
              the ``assert`` at
              readability.py:486
              documents it rather than enforcing it, since ``python -O`` strips
              asserts. If they ever disagree, ``splitter(text)`` is handed a
              non-string.
            - ``sentences`` must not be a ``bool``. It is rejected explicitly,
              because ``bool`` subclasses ``int`` and ``sentences=True`` would
              otherwise be read as *B*=1 — a plausible, silently wrong answer.
            - ``sentences`` must not be a bare ``str``. Also rejected
              explicitly: a string is a sequence of characters, so it would
              otherwise count as one "sentence" per character.
            - A ``sentences`` sequence must be re-iterable. A generator is
              consumed by the comprehension at
              readability.py:501
              and its elements must be strings, or ``.strip()`` raises
              ``AttributeError``.

        Guarantees:
            - Blank and whitespace-only entries are dropped from a segmented or
              pre-segmented sequence before counting.
            - An explicit integer is returned **unvalidated** — zero and
              negatives pass through here and are caught downstream by
              ``lix_from_counts``, which raises ``ValueError``.

        Silences:
            - A missing ``__qualname__`` on the splitter falls back to ``repr``
              at
              readability.py:488
              — see ``_policy_label`` for why that weakens the provenance
              record.
    """
    # bool is a subclass of int, so `sentences=True` would silently become B=1.
    if isinstance(sentences, bool):
        msg = f"sentences must be a count or a sequence of sentences, got {sentences!r}"
        raise TypeError(msg)

    if sentences is None:
        if not is_raw:
            msg = (
                "lix() got tokens but no sentences. The number of sentences (B) "
                "cannot be recovered from a token list — pass sentences= as a "
                "count, or as the list of sentence strings, or pass raw text so "
                "saphes can segment it."
            )
            raise TypeError(msg)
        splitter = sentencer or segment.sentences
        assert isinstance(text, str)  # noqa: S101 - guarded by is_raw
        split = splitter(text)
        name = getattr(splitter, "__qualname__", None) or repr(splitter)
        return len([s for s in split if s.strip()]), "segmented", name

    if isinstance(sentences, int):
        return sentences, "explicit", None

    if isinstance(sentences, str):
        msg = (
            "sentences got a single string, which is ambiguous. Pass a count, or "
            "a list of sentence strings such as ['One.', 'Two.']."
        )
        raise TypeError(msg)

    return len([s for s in sentences if s.strip()]), "presegmented", None


def lix(
    words: str | Sequence[str],
    *,
    sentences: int | Sequence[str] | None = None,
    long_word_threshold: int = 6,
    length_policy: LengthPolicy | LengthFn = "nfc",
    sentencer: Sentencer | None = None,
) -> LixResult:
    """Compute the LIX readability index.

    **Pass surface forms, not lemmas.** Word length is the signal; lemmatising
    erases it. The parameter is named ``words`` (not ``lemmas``) so that wiring
    this to :func:`saphes.diversity.lexical_diversity`'s token stream fails
    loudly instead of returning a plausible wrong number.

    Args:
        words: Raw text, or an already-tokenised sequence of surface forms.
        sentences: *B*. Three accepted forms — ``None`` splits the raw text with
            ``sentencer`` (only valid when ``words`` is a string), a sequence of
            strings is counted, and an ``int`` is used directly. The choice is
            recorded on the result.
        long_word_threshold: A long word is *longer than* this. The default 6
            therefore means seven letters or more, per Björnsson. Raise it for
            agglutinative or heavily inflected languages, where 6 saturates.
        length_policy: How to count a word's letters. See :func:`word_length`.
        sentencer: A custom sentence splitter, used only when ``sentences`` is
            ``None``. Defaults to :func:`saphes.segment.sentences`.

    Returns:
        A :class:`LixResult` carrying the score, *A*, *B*, *C*, and every
        parameter used.

    Raises:
        TypeError: If tokens are given without ``sentences``, if ``sentences`` is
            a bool or a bare string.
        ValueError: If ``long_word_threshold`` is negative, or if the resolved
            counts are degenerate (no words, no sentences).

    Contract:
        Preconditions:
            - ``words`` must be a ``str`` or a **re-iterable** sequence of
              ``str``. A generator is materialised once at
              readability.py:622 so it works, but every element
              must be a string or ``.strip()`` raises ``AttributeError``
              (implicit, at
              readability.py:625).
            - Order is irrelevant here — unlike ``lexical_diversity`` with a
              window, a set of tokens gives the same LIX as a list — but the
              *count* is not, so passing a set silently deduplicates and
              undercounts *A*.
            - Tokens must be **surface forms**, not lemmas. Nothing checks this
              and nothing can: lemmas produce a lower, entirely plausible score.
              The parameter is named ``words`` rather than ``lemmas`` so that
              crossing the two metrics is a ``TypeError`` at the call site.
            - ``length_policy``, if callable, must return an int — see
              ``word_length``. A bad return value fails at the comparison at
              readability.py:635,
              not at the policy.
            - ``sentencer``, if given, must accept one string and return an
              iterable of strings; it is called only when ``sentences`` is
              ``None`` and whatever it raises propagates.

        Guarantees:
            - Empty and whitespace-only tokens are dropped before counting and
              the number is recorded as ``dropped_empty``.
            - ``long_word_threshold=0`` makes every word long, so the second
              term is exactly ``100.0``.
            - Raising the threshold never raises the score.
            - Empty input raises rather than dividing by zero.
            - ``unit`` on the result is always ``"surface"``, and every
              parameter that affected the number is recorded on the result.

    Examples:
        The hand-computed example from the module docstring:

        >>> text = "The cat sat on it. Complicated sentences generally frighten us."
        >>> result = lix(text)
        >>> result.words, result.sentences, result.long_words
        (10, 2, 4)
        >>> result.score
        45.0

        The threshold is "more than", so 6 selects words of 7+ letters:

        >>> [w for w in ["house", "houses", "housing", "household"] if len(w) > 6]
        ['housing', 'household']

        Why the parameter exists — Hungarian saturates at the Swedish default,
        and a higher threshold restores discrimination:

        >>> hu = (
        ...     "A gyermekeknek megmutatták a településeken "
        ...     "található nevezetességeket. Elutaztak."
        ... )
        >>> lix(hu).long_word_share      # three words in four count as "long"
        0.75
        >>> lix(hu).score                # an ordinary sentence, "very difficult"
        79.0
        >>> lix(hu, long_word_threshold=9).long_word_share
        0.5
        >>> lix(hu, long_word_threshold=9).score
        54.0

        Tokens plus an explicit *B*, for pipelines that have no punctuation left
        — Homer's treebank, for instance:

        >>> lix(["Complicated", "sentences", "frighten", "us"], sentences=1).score
        79.0
    """
    if long_word_threshold < 0:
        msg = f"long_word_threshold cannot be negative, got {long_word_threshold}"
        raise ValueError(msg)

    is_raw = isinstance(words, str)
    if is_raw:
        tokens = segment.words(words)
        token_source: TokenSource = "segmented"
    else:
        tokens = list(words)
        token_source = "provided"

    kept = [token for token in tokens if token.strip()]
    dropped_empty = len(tokens) - len(kept)

    n_sentences, sentence_source, sentencer_name = _count_sentences(
        words, sentences, sentencer, is_raw=is_raw
    )

    n_long = sum(
        1
        for token in kept
        if word_length(token, policy=length_policy) > long_word_threshold
    )

    score = lix_from_counts(words=len(kept), sentences=n_sentences, long_words=n_long)

    return LixResult(
        score=score,
        words=len(kept),
        sentences=n_sentences,
        long_words=n_long,
        long_word_threshold=long_word_threshold,
        length_policy=_policy_label(length_policy),
        unit="surface",
        sentence_source=sentence_source,
        sentencer=sentencer_name,
        token_source=token_source,
        dropped_empty=dropped_empty,
        saphes_version=saphes.__version__,
    )


def rix(
    words: str | Sequence[str],
    *,
    sentences: int | Sequence[str] | None = None,
    long_word_threshold: int = 6,
    length_policy: LengthPolicy | LengthFn = "nfc",
    sentencer: Sentencer | None = None,
) -> float:
    """Compute RIX: long words per sentence, ``C/B``.

    Anderson's simplification of LIX. Nearly free once LIX exists, and it drops
    the *A/B* term entirely. No interpretation bands ship for it: Anderson's are
    calibrated to English school grades, which compounds the problem that already
    makes :attr:`LixResult.band` return ``None`` off threshold 6.

    Args:
        words: Raw text, or an already-tokenised sequence of surface forms.
        sentences: *B*, in any of the three forms :func:`lix` accepts.
        long_word_threshold: A long word is *longer than* this.
        length_policy: How to count a word's letters. See :func:`word_length`.
        sentencer: A custom sentence splitter.

    Returns:
        The RIX score, ``C/B``.

    Contract:
        Preconditions:
            - Identical to ``lix``: this is a thin wrapper that builds a full
              ``LixResult`` and returns one property of it. Every precondition
              and every exception documented there applies here unchanged.

        Guarantees:
            - Never negative, and zero exactly when no word exceeds the
              threshold.
            - Discards the audit trail. ``lix(...).rix`` returns the same number
              *and* keeps the counts and parameters that produced it; prefer it
              unless you genuinely want a bare float.

    Examples:
        >>> rix("The cat sat on it. Complicated sentences generally frighten us.")
        2.0
    """
    return lix(
        words,
        sentences=sentences,
        long_word_threshold=long_word_threshold,
        length_policy=length_policy,
        sentencer=sentencer,
    ).rix
