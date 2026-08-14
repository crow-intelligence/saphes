"""Small bundled samples for doctests, tests, and the worked examples in the docs.

Each sample carries raw text *and* a parallel surface/lemma annotation, so the
two token streams the package deliberately keeps apart can both be demonstrated
from one source of truth.

These are illustrations, not corpora. They are far too short for a TTR to mean
anything — which is itself the point the package keeps making.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from saphes.datasets._samples import (
    ENGLISH_PAIRS,
    ENGLISH_TEXT,
    GREEK_PAIRS,
    GREEK_TEXT,
    HUNGARIAN_PAIRS,
    HUNGARIAN_TEXT,
)

__all__ = ["Sample", "load_english", "load_greek", "load_hungarian"]


@dataclass(frozen=True, slots=True)
class Sample:
    """A sample text with parallel surface and lemma streams.

    Attributes:
        language: ISO 639 code of the language.
        text: The running text, with punctuation. Feed this to ``lix``.
        pairs: ``(surface form, lemma)`` for every token, in document order.
        source: Where the text came from.
    """

    language: str
    text: str
    pairs: tuple[tuple[str, str], ...]
    source: str

    @property
    def forms(self) -> list[str]:
        """The surface forms, in order — the stream ``lix`` wants.

        Returns:
            One surface form per token.

        Examples:
            >>> load_hungarian().forms[:3]
            ['A', 'kutya', 'futott']
        """
        return [form for form, _ in self.pairs]

    @property
    def lemmas(self) -> list[str]:
        """The lemmas, in order — the stream ``lexical_diversity`` wants.

        Returns:
            One lemma per token.

        Examples:
            >>> load_hungarian().lemmas[:3]
            ['a', 'kutya', 'fut']
        """
        return [lemma for _, lemma in self.pairs]


def _sample(
    language: str, text: str, pairs: tuple[tuple[str, str], ...], source: str
) -> Sample:
    """Build a Sample with both streams NFC-normalised.

    Contract:
        Preconditions:
            - Every element of ``pairs`` must be a two-element tuple of strings;
              anything else raises ``ValueError`` or ``TypeError`` from the
              unpacking at
              __init__.py:97.

        Guarantees:
            - Both streams are NFC-normalised, so ``len()`` on either counts
              glyphs rather than code points. This is what lets the bundled
              Greek sample be measured without a length policy.
            - Normalisation is idempotent, so re-wrapping a Sample is safe.
            - Nothing checks that ``text`` and ``pairs`` describe the same
              passage. ``tests/test_datasets.py`` does, by tokenising ``text``
              and comparing the count.
    """
    return Sample(
        language=language,
        text=unicodedata.normalize("NFC", text),
        pairs=tuple(
            (unicodedata.normalize("NFC", form), unicodedata.normalize("NFC", lemma))
            for form, lemma in pairs
        ),
        source=source,
    )


def load_english() -> Sample:
    """An English sample: light inflection, so a small surface/lemma gap.

    Returns:
        The sample.

    Examples:
        >>> sample = load_english()
        >>> sample.language
        'en'
        >>> len(sample.pairs)
        21
    """
    return _sample("en", ENGLISH_TEXT, ENGLISH_PAIRS, "Written for this package.")


def load_hungarian() -> Sample:
    """A Hungarian sample: agglutinative, so a large surface/lemma gap.

    ``kutya`` appears as ``kutya``, ``kutyák`` and ``kutyáknak`` — three surface
    types, one lemma. That is the morphology an un-lemmatised TTR would report as
    vocabulary.

    Returns:
        The sample.

    Examples:
        >>> sample = load_hungarian()
        >>> sample.language
        'hu'
        >>> sorted({f for f, lem in sample.pairs if lem == "kutya"})
        ['kutya', 'kutyák', 'kutyáknak']
    """
    return _sample("hu", HUNGARIAN_TEXT, HUNGARIAN_PAIRS, "Written for this package.")


def load_greek() -> Sample:
    """An Ancient Greek sample: Iliad 1.1-7, heavily inflected.

    Public domain text; the lemmatisation follows the Ancient Greek Dependency
    Treebank's conventions. Both streams are NFC-normalised, so ``len()`` counts
    glyphs.

    Returns:
        The sample.

    Examples:
        >>> sample = load_greek()
        >>> sample.language
        'grc'
        >>> sample.forms[0], sample.lemmas[0]
        ('μῆνιν', 'μῆνις')

        Ἀχιλῆος and Ἀχιλλεύς are two surface types and one lemma — the epic's
        subject, counted twice by a surface TTR:

        >>> sorted({f for f, lem in sample.pairs if lem == "Ἀχιλλεύς"})
        ['Ἀχιλλεύς', 'Ἀχιλῆος']
    """
    return _sample(
        "grc", GREEK_TEXT, GREEK_PAIRS, "Homer, Iliad 1.1-7 (public domain)."
    )
