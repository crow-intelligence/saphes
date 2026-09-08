"""Shared type aliases for the saphes package.

The aliases here name the choices that change the answer. ``TokenUnit`` is the
package's central one: every token stream is *either* lemmas *or* surface forms,
the two metrics want opposite streams, and no result object is allowed to omit
which it measured.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeAlias

TokenUnit: TypeAlias = Literal["lemma", "surface", "stem"]
"""What a token stream *is*: lemmas, surface (inflected) forms, or stems.

``lexical_diversity`` wants ``"lemma"`` — surface variation is morphology, not
vocabulary. ``lix`` requires ``"surface"`` — word length is the signal, and
lemmatising erases it. See the module docstrings for why they must not share a
token stream.

``"stem"`` is the algorithmic fallback for callers with no lemmatiser, produced
by :func:`saphes.stem.hungarian_stems`. It is a *third* stream and not a cheaper
spelling of ``"lemma"``: a stemmer both over- and under-merges, so a stem-based
result is comparable only to another from the same stemmer. It has its own
member precisely so that no result object can report a stem count as a lemma
count.
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

PunctuationPolicy: TypeAlias = Literal["collapse", "ignore", "keep"]
"""How punctuation is treated when measuring dependency distance.

``"collapse"`` is the default and the only one the literature supports: the
punctuation tokens are removed and the remaining tokens **re-indexed**, so
distances are measured across the punctuation-free sequence. Jing & Liu (2015)
report sentence length as "SL (no punctuations)", which is only coherent on a
re-indexed sequence, and Futrell et al. (2015) drop "any nodes representing
punctuation or root nodes, nor arcs between them".

``"ignore"`` keeps the original index space and merely skips the punctuation
tokens' own arcs. No paper in ``papers/`` describes this; it is what software
produces by filtering a score list without re-indexing, and it reports a
**larger** MDD than ``"collapse"`` for any sentence with medial punctuation. It
exists here to reproduce such an implementation, not because it is defensible.

``"keep"`` counts every token, punctuation included. Furthest from the
literature, and offered only so a disagreement can be diagnosed rather than
guessed at.
"""

DepAggregation: TypeAlias = Literal["macro", "micro"]
"""How per-sentence dependency distances combine into one number for a text.

``"macro"`` is the default and matches Jing & Liu (2015: 164) equations (3) and
(4): average the per-sentence means, so every sentence weighs the same
regardless of length. ``"micro"`` pools every dependency pair in the text and
divides once, so long sentences dominate.

They are different numbers, not different roundings of one number. A naive
implementation produces ``"micro"`` by accident, which is why the choice is
recorded on the result rather than left implicit.
"""

ParseSource: TypeAlias = Literal["conllu", "spacy", "provided"]
"""Where a dependency parse came from.

Provenance only — it never changes the arithmetic. ``"provided"`` means the
caller built the token sequence themselves rather than going through an adapter.
"""
