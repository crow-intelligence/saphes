"""Reader for the MOKK/BME Hungarian Webcorpus frequency lists.

Four things decide whether this reader is correct. Each of them fails silently
if you get it wrong, which is why each is called out here.

**Decode as ISO-8859-2.** Reading the file as UTF-8 corrupts ``ő`` and ``ű`` —
precisely the characters that distinguish Hungarian, and a direct hit on the
length counts.

**Use the 4% stratum (field index 4).** The strata are nested samples with
decreasing error rates; the 4% stratum has fewer mistakes than an average print
document, while the full-corpus column carries the crawl's junk (19.1M types
against 7.2M).

**Strip the trailing asterisk before anything else.** Capitalised, mostly
sentence-initial forms are marked ``A*``, ``Az*``, ``Ha*``, ``És*``. ``A*``
alone is 8,867,291 tokens in the 4% stratum. Discarding starred rows — which is
what a naive ``^[a-záéíóöőúüű]+$`` filter does — throws away overwhelmingly
*short* function words and biases the mean length upward, which picks too high a
threshold. Strip, then casefold, then test the alphabet.

**Accumulate with ``+=``, never assignment.** After stripping, ``A`` and ``A*``
both map to ``a``. A dict assignment would keep only whichever came last.

Streaming throughout: the full list is 400 MB unzipped, so no ``read_csv``.
"""

from __future__ import annotations

import gzip
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

# word, full corpus, 40% stratum, 8% stratum, 4% stratum
STRATUM_COLUMNS = {"full": 1, "40pct": 2, "8pct": 3, "4pct": 4}

HUNGARIAN_ALPHABET = re.compile(r"^[a-záéíóöőúüű]+$")

_FIELDS = 5


@dataclass(frozen=True, slots=True)
class FilterReport:
    """What the filter kept and what it threw away.

    Auditability is the point of this package, so the filter reports rather than
    silently discarding.

    Attributes:
        source: The file that was read.
        stratum: Which frequency column was used.
        rows_read: Total rows in the file.
        rows_kept: Rows that survived every filter.
        types_kept: Distinct types after merging starred and unstarred forms.
        tokens_kept: Total running tokens behind those types.
        starred_merged: Rows carrying a trailing asterisk that were merged in.
        dropped_bare_asterisk: The lone ``*`` row, an unanalysable marker.
        dropped_non_alpha: Rows rejected by the alphabet test (digits,
            punctuation, URLs, foreign strings).
        dropped_malformed: Rows without five tab-separated fields, or with a
            non-integer frequency.
    """

    source: str
    stratum: str
    rows_read: int
    rows_kept: int
    types_kept: int
    tokens_kept: int
    starred_merged: int
    dropped_bare_asterisk: int
    dropped_non_alpha: int
    dropped_malformed: int

    def summary(self) -> str:
        """Return a one-line human-readable summary."""
        return (
            f"{self.source} [{self.stratum}]: {self.rows_read:,} rows → "
            f"{self.types_kept:,} types / {self.tokens_kept:,} tokens "
            f"(merged {self.starred_merged:,} starred, "
            f"dropped {self.dropped_non_alpha:,} non-alpha, "
            f"{self.dropped_malformed:,} malformed, "
            f"{self.dropped_bare_asterisk:,} bare-asterisk)"
        )


def _open(path: Path):  # noqa: ANN202 - a file handle, gzip or plain
    """Open the list, transparently handling the gzipped full file."""
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="iso-8859-2", errors="replace")
    return open(path, encoding="iso-8859-2", errors="replace")


def read_mokk(
    path: Path,
    *,
    stratum: str = "4pct",
    keep_asterisk: bool = True,
) -> tuple[Counter[str], FilterReport]:
    """Read a MOKK frequency list into a token-weighted Counter.

    Args:
        path: Path to ``web2.2-freq-sorted.txt.gz`` or the ``top100k`` file.
        stratum: Which frequency column to use. See :data:`STRATUM_COLUMNS`.
        keep_asterisk: If ``True`` (correct), strip the capitalisation marker and
            merge the row into its lowercase form. If ``False``, discard starred
            rows entirely — the naive behaviour, kept only so the sensitivity
            run can show what it costs.

    Returns:
        The frequency Counter and a :class:`FilterReport`.

    Raises:
        KeyError: If ``stratum`` is not a known column.
    """
    if stratum not in STRATUM_COLUMNS:
        msg = f"unknown stratum {stratum!r}; expected one of {sorted(STRATUM_COLUMNS)}"
        raise KeyError(msg)
    column = STRATUM_COLUMNS[stratum]

    counts: Counter[str] = Counter()
    rows = kept = starred = bare = non_alpha = malformed = 0

    with _open(path) as handle:
        for line in handle:
            rows += 1
            fields = line.rstrip("\n").split("\t")
            if len(fields) < _FIELDS:
                malformed += 1
                continue

            word = fields[0]
            if word == "*":
                bare += 1
                continue

            is_starred = word.endswith("*")
            if is_starred:
                if not keep_asterisk:
                    non_alpha += 1
                    continue
                word = word[:-1]

            word = word.casefold()
            if not HUNGARIAN_ALPHABET.match(word):
                non_alpha += 1
                continue

            try:
                frequency = int(fields[column])
            except ValueError:
                malformed += 1
                continue

            counts[word] += frequency
            kept += 1
            if is_starred:
                starred += 1

    report = FilterReport(
        source=path.name,
        stratum=stratum,
        rows_read=rows,
        rows_kept=kept,
        types_kept=len(counts),
        tokens_kept=sum(counts.values()),
        starred_merged=starred,
        dropped_bare_asterisk=bare,
        dropped_non_alpha=non_alpha,
        dropped_malformed=malformed,
    )
    return counts, report
