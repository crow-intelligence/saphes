"""Split raw text into words and sentences.

This is a *convenience* splitter, not linguistic tokenisation. It exists so that
``lix("some text")`` works out of the box and so the package has no hard
dependencies. For real work — and certainly for the agglutinative and heavily
inflected languages saphes exists to serve — tokenise upstream with a proper
analyser (``kenon.Tokenizer``, huspacy, CLTK, a treebank) and pass the tokens in.

Sentence splitting is the part with no single right answer. Björnsson's original
*B* counted "periods, colons, or capital first letters", which is not what a
modern splitter does; implementations that disagree about *B* disagree about LIX.
The default here is a self-contained, offline regex splitter that guards common
abbreviations (so ``Mr. Bennet`` is not cut in two); pass ``punkt=True`` for
NLTK's Punkt model instead. Whichever you use, ``LixResult.sentence_source`` and
``LixResult.sentencer`` record the choice.

Ported from ``lexograph.segment.units``, minus the character/unit machinery.
"""

from __future__ import annotations

import re

__all__ = ["words", "sentences"]

# A token: a run of word characters, allowing internal apostrophes and hyphens
# (so ``good-humoured`` and ``don't`` stay whole).
_TOKEN_RE = re.compile(r"\w+(?:['’-]\w+)*")

# A candidate sentence terminator: end punctuation, optional closing quotes or
# brackets, then whitespace. The whitespace requirement avoids splitting inside
# decimals and ellipses mid-token.
_SENTENCE_END_RE = re.compile(r'[.!?]+["\'”’)\]]*\s+')

# The word immediately before a candidate terminator.
_TRAILING_WORD_RE = re.compile(r"(\w+)\W*$")

# The first letter at or after a position (Unicode-aware, excludes digits).
_NEXT_LETTER_RE = re.compile(r"[^\W\d_]")

# Abbreviations whose trailing period is not a sentence boundary.
_ABBREVIATIONS = frozenset(
    {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "rev", "hon",
        "gen", "col", "capt", "sgt", "lt", "messrs",
        "vs", "etc", "al", "no", "vol", "fig", "pp", "inc", "ltd", "co",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept",
        "oct", "nov", "dec",
    }
)  # fmt: skip


def words(text: str) -> list[str]:
    """Return the word tokens of ``text`` in order.

    A token is a run of word characters with optional *internal* apostrophes or
    hyphens; punctuation and whitespace are dropped.

    The "internal" is load-bearing for LIX, and is worth stating because it is
    exactly the kind of undocumented tokeniser choice that makes implementations
    disagree. A *trailing* apostrophe is not kept, because the apostrophe branch
    requires a following word character — so Greek elision marks (``μυρί’``) do
    not inflate the letter count, while English contractions (``don't``) do.

    Args:
        text: The source text.

    Returns:
        The ordered list of word tokens.

    Contract:
        - The returned list preserves source order.
        - No returned token is empty or contains whitespace.

    Examples:
        >>> words("It's a good-humoured day.")
        ["It's", 'a', 'good-humoured', 'day']

        Greek elision: the trailing apostrophe is dropped, so ``μυρί’`` counts as
        four letters, not five.

        >>> words("μυρί’ Ἀχαιοῖς ἄλγε’ ἔθηκε")
        ['μυρί', 'Ἀχαιοῖς', 'ἄλγε', 'ἔθηκε']

        Hungarian diacritics are ordinary word characters:

        >>> words("A házakban őrült űrhajósok élnek.")
        ['A', 'házakban', 'őrült', 'űrhajósok', 'élnek']
    """
    return _TOKEN_RE.findall(text)


def sentences(text: str, *, punkt: bool = False) -> list[str]:
    """Split ``text`` into sentences, in order.

    Args:
        text: The source text.
        punkt: If ``True``, use NLTK's Punkt sentence tokenizer (downloading the
            model on first use). Requires the ``punkt`` extra. If ``False`` (the
            default), use the bundled offline regex splitter, which guards common
            abbreviations.

    Returns:
        The ordered list of sentences, each stripped of surrounding whitespace.
        Empty or whitespace-only sentences are dropped.

    Raises:
        ImportError: If ``punkt=True`` and NLTK is not installed.

    Contract:
        - The returned list preserves source order.
        - Every returned sentence is non-empty and equal to its own ``.strip()``.

    Examples:
        >>> sentences("Mr. Bennet replied that he had not. He said no more.")
        ['Mr. Bennet replied that he had not.', 'He said no more.']

        Short sentences are still sentences. (``textstat`` silently discards any
        sentence of two words or fewer, which is a large part of why its LIX
        differs from ours — see the troubleshooting docs.)

        >>> sentences("He ran. She sang. They left.")
        ['He ran.', 'She sang.', 'They left.']
    """
    if punkt:
        return _punkt_sentences(text)
    return _regex_sentences(text)


def _regex_sentences(text: str) -> list[str]:
    """Split into sentences with the offline, abbreviation-aware regex splitter."""
    result: list[str] = []
    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        prefix = text[start : match.start()]
        trailing = _TRAILING_WORD_RE.search(prefix)
        if trailing is not None:
            word = trailing.group(1)
            if word.lower() in _ABBREVIATIONS:
                continue
            # A single capital letter is an initial (e.g. "A. Bennet"), not an end.
            if len(word) == 1 and word.isalpha() and word.isupper():
                continue
        # If the next sentence would start with a lowercase letter, this
        # terminator sits inside a larger sentence — e.g. dialogue followed by
        # an attribution: '"Is it let?" she asked.' — so it is not a boundary.
        following = _NEXT_LETTER_RE.search(text, match.end())
        if following is not None and following.group(0).islower():
            continue
        sentence = text[start : match.end()].strip()
        if sentence:
            result.append(sentence)
        start = match.end()
    tail = text[start:].strip()
    if tail:
        result.append(tail)
    return result


def _punkt_sentences(text: str) -> list[str]:
    """Split into sentences with NLTK Punkt, fetching the model if needed."""
    try:
        import nltk
    except ImportError as exc:  # pragma: no cover - exercised only without nltk
        msg = (
            "sentences(punkt=True) needs NLTK, which saphes does not require. "
            "Install it with `uv add 'saphes[punkt]'`, or use the default "
            "offline regex splitter."
        )
        raise ImportError(msg) from exc

    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)
    from nltk.tokenize import sent_tokenize

    return [s.strip() for s in sent_tokenize(text) if s.strip()]
