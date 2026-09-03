"""Optional Snowball stemming, for when no lemmatiser is available.

``lexical_diversity`` wants lemmas, and saphes cannot produce them: real
lemmatisation is language-specific and heavy. That leaves anyone without
huspacy, CLTK or a treebank measuring surface forms and reporting a diversity
that is mostly morphology.

A stemmer is the cheap fallback. It strips inflectional suffixes by rule, with
no lexicon, so it removes a lot of that noise for the price of a pure-Python
dependency and no model download.

**It is not a lemmatiser, and the two results are not comparable.** Snowball
emits strings that are not words — ``fánál`` becomes ``fá``, ``adtam`` becomes
``adt`` — and it fails in both directions at once. It over-merges, collapsing
distinct lemmas that share a truncated prefix; and it under-merges, so ``kutya``
stems to ``kuty`` while ``kutyák`` stems to ``kutya``, giving one lemma two
stems. A stem-based TTR is therefore comparable only to another stem-based TTR
from the same stemmer version. Never put one in a table beside a lemma-based
one.

That is why :data:`~saphes._types.TokenUnit` has a third member rather than
stems being passed off as lemmas: the result object has to say which it was.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

__all__ = ["hungarian_stems"]

_STEMMER: Any = None


def _stemmer() -> Any:  # noqa: ANN401 - a snowballstemmer, which we cannot import
    """Return the memoised Hungarian Snowball stemmer, importing on first use."""
    global _STEMMER  # noqa: PLW0603 - the point is to construct it once
    if _STEMMER is None:
        try:
            import snowballstemmer
        except ImportError as exc:  # pragma: no cover - only without the extra
            msg = (
                "hungarian_stems() needs snowballstemmer, which saphes does not "
                "require. Install it with `uv add 'saphes[snowball]'`, or "
                "lemmatise upstream and pass unit='lemma'."
            )
            raise ImportError(msg) from exc
        _STEMMER = snowballstemmer.stemmer("hungarian")
    return _STEMMER


def hungarian_stems(tokens: Sequence[str], *, case_fold: bool = True) -> list[str]:
    """Stem Hungarian tokens with the Snowball algorithm.

    Args:
        tokens: A sequence of tokens. A raw ``str`` is rejected.
        case_fold: Whether to case-fold before stemming. Defaults to ``True``,
            because the algorithm is defined on lowercase input and silently
            under-stems anything else — ``KUTYÁK`` stems to itself. Pass
            ``False`` only if the tokens are already folded.

    Returns:
        One stem per input token, in order. Stems are not words.

    Raises:
        TypeError: If ``tokens`` is a ``str``, or if an element is not a
            ``str``.
        ImportError: If the ``snowball`` extra is not installed.

    Contract:
        Preconditions:

        - ``tokens`` must be a sequence of tokens, **not a raw string**. A
          string is a sequence of characters, so stemming one would return a
          plausible list of single letters and no error. Explicitly guarded.
        - Tokens should be Hungarian. The algorithm is total, so English or
          Greek input returns something rather than failing.

        Guarantees:

        - The output has exactly one entry per input token, in order, so it
          can be zipped back onto the surface forms.
        - Stemming never splits a type: two identical tokens always get the
          same stem. That is what makes stem-TTR at most surface-TTR.

        Silences:

        - A stem is not checked against anything. Over-stemming
          (``kutya`` → ``kuty``) and under-stemming (``kutyák`` → ``kutya``,
          the same lemma reaching a different stem) both pass silently. There
          is no signal in the output distinguishing them from a good stem.
        - Non-Hungarian tokens are stemmed by Hungarian rules without
          complaint.

    Examples:
        Inflected forms collapse onto their stem, which is what buys back the
        diversity that morphology inflates:

        >>> from saphes import hungarian_stems
        >>> hungarian_stems(["ház", "házban", "házak", "házakat"])
        ['ház', 'ház', 'ház', 'ház']

        And the honest failure, twice over. All three of these are the lemma
        ``kutya``, but the bare form is over-stemmed to ``kuty`` while the
        inflected ones stop at ``kutya`` — so one lemma reaches two stems and
        the merge is only partial:

        >>> hungarian_stems(["kutya", "kutyák", "kutyáknak"])
        ['kuty', 'kutya', 'kutya']

        The same rule truncates a bare noun that has no suffix to strip, which
        is why a stem is not a word and not a lemma:

        >>> hungarian_stems(["kert", "kertben"])
        ['ker', 'kert']

        A raw string is refused rather than stemmed character by character:

        >>> hungarian_stems("kutya kert")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        TypeError: hungarian_stems() got a raw string....
    """
    if isinstance(tokens, str):
        msg = (
            "hungarian_stems() got a raw string. A string is a sequence of "
            "characters, so stemming it would return one stem per letter. "
            "Pass segment.words(text) instead."
        )
        raise TypeError(msg)

    words = [token.casefold() for token in tokens] if case_fold else list(tokens)
    return list(_stemmer().stemWords(words))
