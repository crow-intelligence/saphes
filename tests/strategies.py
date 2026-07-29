"""Shared Hypothesis strategies for saphes tests.

Deliberately constrained to named alphabets rather than ``st.text()``. Arbitrary
Unicode generates lone combining marks and mixed scripts, under which "the length
of a word" is genuinely ambiguous — so a failure there would be a question about
the test, not about the code.
"""

import string

from hypothesis import strategies as st

ascii_word = st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=12)
"""A lowercase ASCII word (1-12 letters)."""

hungarian_word = st.text(
    alphabet="aábcdeéfghiíjklmnoóöőprstuúüűvz", min_size=1, max_size=16
)
"""A word over the Hungarian lowercase alphabet (1-16 letters)."""

greek_word = st.text(alphabet="αβγδεζηθικλμνξοπρστυφχψω", min_size=1, max_size=14)
"""A word over the Greek lowercase alphabet, unaccented (1-14 letters)."""

hungarian_stem = st.sampled_from(
    ["ház", "kutya", "kert", "fa", "ember", "könyv", "út", "víz", "gyerek", "hal"]
)
"""A Hungarian nominal stem — the lemma a set of inflected forms shares."""

hungarian_suffix = st.sampled_from(
    ["", "ak", "ban", "ból", "nak", "val", "ok", "at", "hoz", "on", "ért", "ig"]
)
"""A Hungarian case/number suffix. The empty string is included, because the
bare stem is itself a valid surface form — which is why the lemma/surface type
comparison is ``<=`` and not ``<``."""

word_list = st.lists(ascii_word, min_size=1, max_size=200)
"""A non-empty list of tokens."""

positive_threshold = st.integers(min_value=0, max_value=20)
"""A LIX long-word threshold."""


@st.composite
def frequency_counts(draw: st.DrawFn) -> dict[str, int]:
    """A non-empty word-to-frequency mapping, as a frequency list supplies it.

    Frequencies start at 1 so the default ``min_frequency`` in
    ``length_curve`` is exercised rather than sidestepped.
    """
    words = draw(st.lists(ascii_word, min_size=1, max_size=60, unique=True))
    return {word: draw(st.integers(min_value=1, max_value=10_000)) for word in words}


@st.composite
def inflected_pairs(draw: st.DrawFn) -> list[tuple[str, str]]:
    """A non-empty list of ``(surface form, lemma)`` pairs from Hungarian morphology.

    Both streams come from one draw, so the surface list and the lemma list are
    guaranteed to describe the same tokens — which is what makes the type-count
    comparison a theorem rather than a coincidence.
    """
    stems = draw(st.lists(hungarian_stem, min_size=1, max_size=100))
    return [(stem + draw(hungarian_suffix), stem) for stem in stems]
