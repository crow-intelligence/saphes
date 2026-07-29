"""Saphes — readability (LIX) and lexical diversity (TTR/MATTR), made auditable.

Two metrics, done carefully, with the parameters other implementations hardcode.

The one thing to get right: **the two metrics need opposite token streams.**
:func:`~saphes.diversity.lexical_diversity` wants lemmas, because surface
variation is morphology rather than vocabulary.
:func:`~saphes.readability.lix` requires surface forms, because word length is
its signal and lemmatising erases it. Feed one stream to both and exactly one of
them is silently wrong.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("saphes")
except PackageNotFoundError:  # pragma: no cover - only when running uninstalled
    __version__ = "0.0.0+unknown"

from saphes.diversity import (  # noqa: E402 - __version__ must precede these
    DiversityResult,
    lexical_diversity,
    mattr,
    ttr_from_counts,
)
from saphes.readability import (  # noqa: E402 - __version__ must precede these
    LIX_BANDS,
    LixResult,
    interpret_lix,
    lix,
    lix_from_counts,
    rix,
    word_length,
)
from saphes.segment import sentences, words  # noqa: E402 - as above

__all__ = [
    "LIX_BANDS",
    "DiversityResult",
    "LixResult",
    "__version__",
    "interpret_lix",
    "lexical_diversity",
    "lix",
    "lix_from_counts",
    "mattr",
    "rix",
    "sentences",
    "ttr_from_counts",
    "word_length",
    "words",
]
