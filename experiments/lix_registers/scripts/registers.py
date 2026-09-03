"""Readers for the register panel, in two tiers.

Every caveat saphes ships tells the reader that a calibrated threshold belongs
to a register, and to recompute on their own. The study that produced the
threshold never did that itself: every corpus in it is web or news. This module
supplies the other registers.

**Tier 1 is reproducible by anyone.** Leipzig news for Swedish and Hungarian,
and the MOKK crawl part — all fetched by
``experiments/lix_calibration/scripts/download_data.py``.

**Tier 2 is not.** It reads corpora that live in sibling projects on the
author's machine: parliamentary speeches, corruption journalism, song lyrics.
They are not redistributable and the paths are not guessable, so every tier-2
register is opt-in via ``--corpus-root``, is skipped with a log line when
absent, and carries its tier in the published record. A run with no tier-2
corpora present must still produce a complete, publishable result.

**Where *B* comes from matters more than anything else here.** Implementations
of LIX disagree almost entirely on the sentence count, so a panel that mixed
corpus-supplied *B* with a segmenter's *B* would be measuring the segmenter as
much as the register. Each reader therefore declares which it offers, and where
a corpus supplies *B* the panel measures both and reports the gap.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

TIER_LOCAL = "author-local"
TIER_PUBLIC = "public"


@dataclass(frozen=True, slots=True)
class Register:
    """One corpus in the panel.

    Attributes:
        key: Short identifier used in the record.
        description: What kind of language this is.
        tier: ``"public"`` or ``"author-local"``.
        supplies_sentences: Whether *B* comes from the corpus rather than a
            segmenter.
        path: Where it was read from, or ``None`` if absent.
    """

    key: str
    description: str
    tier: str
    supplies_sentences: bool
    path: Path | None


def parlamonitor_sentences(root: Path, *, limit: int | None = None) -> Iterator[str]:
    """Sentences from Hungarian parliamentary speeches.

    The records carry a ``sentences`` list produced upstream, so *B* is the
    corpus's own count and not a segmenter's.
    """
    path = root / "parlamonitor" / "data" / "raw" / "cycle43-speeches.jsonl"
    count = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            for sentence in json.loads(line).get("sentences") or []:
                text = sentence.strip()
                if not text:
                    continue
                yield text
                count += 1
                if limit is not None and count >= limit:
                    return


def kmdb_texts(root: Path, *, limit: int | None = None) -> Iterator[str]:
    """Article text from the K-Monitor corruption-journalism corpus.

    Read from the SQLite store rather than the token Parquet, which would need
    pyarrow — a heavy dependency for one row of a panel. The consequence is
    stated rather than hidden: this register has **no corpus sentence count**,
    so its *B* comes from the bundled splitter.

    Only canonical, Hungarian, non-duplicate rows.
    """
    path = root / "kmdb_dashboard" / "data" / "kmdb.sqlite"
    query = (
        "SELECT effective_text FROM article_clean "
        "WHERE is_hu = 1 AND is_canonical = 1 AND effective_text IS NOT NULL"
    )
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        for (text,) in connection.execute(query):
            if text and text.strip():
                yield text
    finally:
        connection.close()


def lyrics_texts(root: Path, *, limit: int | None = None) -> Iterator[str]:
    """Hungarian song lyrics.

    Lyrics have line breaks rather than sentences. Nothing here invents a
    sentence boundary: the panel records *A* and *C* for this register and
    reports *B* as segmenter-derived, which for lyrics is a weak notion. Read
    the mean sentence length for this row as "words between things the splitter
    took for a full stop", not as a sentence length.
    """
    directory = root / "music_networks" / "data" / "processed" / "corpus"
    count = 0
    for path in sorted(directory.glob("decade_*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                text = (json.loads(line).get("text") or "").strip()
                if not text:
                    continue
                yield text
                count += 1
                if limit is not None and count >= limit:
                    return


LOCAL_REGISTERS = {
    "parlamonitor": (
        "Hungarian parliamentary speeches, 2022-",
        parlamonitor_sentences,
        True,
    ),
    "kmdb": ("Hungarian corruption journalism (K-Monitor)", kmdb_texts, False),
    "lyrics": ("Hungarian song lyrics, 1950-2010s", lyrics_texts, False),
}


def available(root: Path) -> dict[str, bool]:
    """Which tier-2 corpora are present under ``root``."""
    return {
        "parlamonitor": (
            root / "parlamonitor" / "data" / "raw" / "cycle43-speeches.jsonl"
        ).exists(),
        "kmdb": (root / "kmdb_dashboard" / "data" / "kmdb.sqlite").exists(),
        "lyrics": (root / "music_networks" / "data" / "processed" / "corpus").is_dir(),
    }
