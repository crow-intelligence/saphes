"""Saphes — readability (LIX) and lexical diversity (TTR/MATTR), made auditable.

Two metrics, done carefully, with the parameters other implementations hardcode.

The one thing to get right: **the two metrics need opposite token streams.**
:func:`~saphes.diversity.lexical_diversity` wants lemmas, because surface
variation is morphology rather than vocabulary.
:func:`~saphes.readability.lix` requires surface forms, because word length is
its signal and lemmatising erases it. Feed one stream to both and exactly one of
them is silently wrong.

Three parameters that other implementations hardcode are exposed here, because
each of them changes the answer:

- **The long-word threshold.** Björnsson's 6 is Swedish. Hungarian ships
  calibrated at 8 — see :func:`~saphes.calibration.recommended_threshold`.
- **What counts as a letter.** ``sz`` is one Hungarian letter, not two
  characters — see :mod:`saphes.hungarian`.
- **What a token stream is.** ``"lemma"``, ``"surface"`` or ``"stem"``, declared
  by the caller and recorded on every result.

The core has no runtime dependencies. Stemming (:mod:`saphes.stem`) and the
Punkt sentence splitter are optional extras, imported lazily and never on the
core path.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("saphes")
except PackageNotFoundError:  # pragma: no cover - only when running uninstalled
    __version__ = "0.0.0+unknown"

from saphes.calibration import (  # noqa: E402 - __version__ must precede these
    ThresholdRecommendation,
    recommended_threshold,
)
from saphes.diversity import (  # noqa: E402 - __version__ must precede these
    DiversityResult,
    lexical_diversity,
    mattr,
    ttr_from_counts,
)
from saphes.hungarian import (  # noqa: E402 - __version__ must precede these
    hungarian_letter_count,
    hungarian_letters,
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
from saphes.stem import hungarian_stems  # noqa: E402 - as above

__all__ = [
    "LIX_BANDS",
    "DiversityResult",
    "LixResult",
    "ThresholdRecommendation",
    "__version__",
    "hungarian_letter_count",
    "hungarian_letters",
    "hungarian_stems",
    "interpret_lix",
    "lexical_diversity",
    "lix",
    "lix_from_counts",
    "mattr",
    "recommended_threshold",
    "rix",
    "sentences",
    "ttr_from_counts",
    "word_length",
    "words",
]
