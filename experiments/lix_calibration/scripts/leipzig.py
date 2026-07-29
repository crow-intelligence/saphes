"""Reader for Leipzig Corpora Collection word lists.

Leipzig builds every language's corpus with the same pipeline, so a Swedish and a
Hungarian list from the same year and genre are directly comparable. That is what
makes the equipercentile comparison honest rather than an argument about
methodology.

Archive layout, verified against the servers::

    swe_news_2022_1M/swe_news_2022_1M-meta.txt
    swe_news_2022_1M/swe_news_2022_1M-words.txt

``-words.txt`` is UTF-8, tab-separated, ``id \\t word \\t frequency``, sorted
alphabetically, and **includes punctuation as rows** — so the alphabet filter is
not optional. There is no capitalisation marker as in the MOKK lists;
capitalised forms simply appear as themselves, so case-folding and accumulating
with ``+=`` merges them. The same code path therefore serves both sources.
"""

from __future__ import annotations

import re
import tarfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ALPHABETS = {
    "swe": re.compile(r"^[a-zåäöé]+$"),
    "hun": re.compile(r"^[a-záéíóöőúüű]+$"),
}

_FIELDS = 3


@dataclass(frozen=True, slots=True)
class LeipzigReport:
    """What was read from a Leipzig archive.

    Attributes:
        source: The archive file name.
        corpus_id: The corpus identifier, e.g. ``swe_news_2022_1M``.
        rows_read: Rows in the word list.
        types_kept: Distinct types after case-folding and filtering.
        tokens_kept: Total running tokens behind those types.
        dropped_non_alpha: Rows rejected by the alphabet test.
        meta: The corpus metadata Leipzig ships, as key-value pairs.
    """

    source: str
    corpus_id: str
    rows_read: int
    types_kept: int
    tokens_kept: int
    dropped_non_alpha: int
    meta: tuple[tuple[str, str], ...]

    def summary(self) -> str:
        """Return a one-line human-readable summary."""
        return (
            f"{self.corpus_id}: {self.rows_read:,} rows → "
            f"{self.types_kept:,} types / {self.tokens_kept:,} tokens "
            f"(dropped {self.dropped_non_alpha:,} non-alpha)"
        )


def read_leipzig(path: Path, *, language: str) -> tuple[Counter[str], LeipzigReport]:
    """Read a Leipzig ``*_1M.tar.gz`` word list into a token-weighted Counter.

    Args:
        path: Path to the downloaded archive.
        language: ``"swe"`` or ``"hun"``, selecting the alphabet filter.

    Returns:
        The frequency Counter and a :class:`LeipzigReport`.

    Raises:
        KeyError: If ``language`` has no configured alphabet.
        LookupError: If the archive contains no ``*-words.txt`` member. The
            message lists the members that *were* found, rather than guessing.
    """
    if language not in ALPHABETS:
        msg = f"no alphabet configured for {language!r}; have {sorted(ALPHABETS)}"
        raise KeyError(msg)
    alphabet = ALPHABETS[language]

    words_text: str | None = None
    meta_text = ""
    corpus_id = path.name.replace(".tar.gz", "")
    seen: list[str] = []

    # Stream mode: members arrive in archive order and cannot be seeked back to.
    # Note extractfile(...).read() then .decode() — wrapping the handle in a
    # TextIOWrapper raises, because the stream object has no seekable().
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            seen.append(member.name)
            if member.name.endswith("-words.txt"):
                handle = archive.extractfile(member)
                if handle is not None:
                    words_text = handle.read().decode("utf-8", errors="replace")
            elif member.name.endswith("-meta.txt"):
                handle = archive.extractfile(member)
                if handle is not None:
                    meta_text = handle.read().decode("utf-8", errors="replace")
            if words_text is not None and meta_text:
                break

    if words_text is None:
        msg = (
            f"no '*-words.txt' member in {path.name}; found: "
            f"{', '.join(seen) if seen else '(nothing)'}"
        )
        raise LookupError(msg)

    counts: Counter[str] = Counter()
    rows = non_alpha = 0
    for line in words_text.splitlines():
        fields = line.split("\t")
        if len(fields) < _FIELDS:
            continue
        rows += 1
        word = fields[1].casefold()
        if not alphabet.match(word):
            non_alpha += 1
            continue
        try:
            counts[word] += int(fields[2])
        except ValueError:
            non_alpha += 1

    meta: list[tuple[str, str]] = []
    for line in meta_text.splitlines():
        parts = line.split("\t")
        if len(parts) >= _FIELDS:
            meta.append((parts[1].strip(), parts[2].strip()))

    report = LeipzigReport(
        source=path.name,
        corpus_id=corpus_id,
        rows_read=rows,
        types_kept=len(counts),
        tokens_kept=sum(counts.values()),
        dropped_non_alpha=non_alpha,
        meta=tuple(meta),
    )
    return counts, report
