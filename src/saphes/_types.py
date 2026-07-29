"""Shared type aliases for the saphes package.

The aliases here name the choices that change the answer. ``TokenUnit`` is the
package's central one: every token stream is *either* lemmas *or* surface forms,
the two metrics want opposite streams, and no result object is allowed to omit
which it measured.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeAlias

TokenUnit: TypeAlias = Literal["lemma", "surface"]
"""What a token stream *is*: lemmas, or surface (inflected) forms.

``lexical_diversity`` wants ``"lemma"`` — surface variation is morphology, not
vocabulary. ``lix`` requires ``"surface"`` — word length is the signal, and
lemmatising erases it. See the module docstrings for why they must not share a
token stream.
"""

LengthPolicy: TypeAlias = Literal["nfc", "graphemes", "codepoints"]
"""How to count the "letters" of a word.

``"nfc"`` normalises to NFC first (the default: idempotent for already-composed
text, and it stops decomposed input from inflating every length). ``"graphemes"``
additionally drops combining marks NFC could not compose. ``"codepoints"`` is raw
``len()``, for reproducing a published number exactly.
"""

LengthFn: TypeAlias = Callable[[str], int]
"""A caller-supplied word-length function, the escape hatch from LengthPolicy.

The seam for grapheme-cluster counting and for orthography-aware counting such as
Hungarian digraphs, neither of which the dependency-free core provides.
"""

Sentencer: TypeAlias = Callable[[str], list[str]]
"""A pluggable sentence splitter: raw text in, sentence strings out."""

SentenceSource: TypeAlias = Literal["segmented", "presegmented", "explicit"]
"""Where a LIX result's sentence count *B* came from.

Björnsson's original *B* ("periods, colons, or capital first letters") is not what
a modern splitter does, and there is no single right answer — so saphes records
which answer was taken.
"""

TokenSource: TypeAlias = Literal["provided", "segmented"]
"""Whether the caller supplied tokens or saphes split them out of raw text."""

LixBand: TypeAlias = Literal[
    "very easy", "easy", "standard", "difficult", "very difficult"
]
"""Björnsson's interpretation band for a LIX score.

Calibrated for Swedish and Germanic prose at a long-word threshold of 6. It is
meaningless at any other threshold — see ``readability.LIX_BANDS``.
"""
