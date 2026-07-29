"""Reader for a Hungarian Webcorpus crawl part.

The frequency lists give word lengths but cannot give *B*, the sentence count —
so they can calibrate the threshold but cannot check what it does to an actual
LIX score. The crawl parts can: they are segmented into sentences *and* words,
and carry a partial morphological analysis.

The markup is rough pseudo-XML and is **not well-formed** (unescaped ``&``,
stray hyphens, unclosed tags), so this is a line-oriented scanner rather than an
XML parser. The shape, verified against the archive::

    <s>Ön most a Tanyacsárda Kft. 2000-es évi ártájékoztatóját olvashatja.
    <w>Ön
    </w>
    <w>program-
    <ana>
    <msd><lemma>program-</lemma><mscat>[Oh]</mscat></msd>
    </ana>
    </w>
    <c>.</c>
    </s>

``<s>`` opens a sentence, ``<w>`` a word token whose surface form follows on the
same line, ``<c>`` is punctuation, and ``<lemma>`` inside ``<ana>`` gives the
lemma where the analyser produced one. Members are ``content/NNNNNNNNNN``,
ISO-8859-2.
"""

from __future__ import annotations

import re
import tarfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

_SENTENCE_OPEN = "<s>"
_WORD_OPEN = "<w>"
_WORD_CLOSE = "</w>"
_LEMMA_RE = re.compile(r"<lemma>(.*?)</lemma>")


@dataclass
class Document:
    """One crawled document, segmented.

    Attributes:
        name: The archive member name.
        sentences: Number of ``<s>`` elements — *B*, straight from the corpus.
        forms: Every surface word form in document order — the stream LIX wants.
        pairs: ``(form, lemma)`` for the tokens the analyser actually resolved.

    ``pairs`` is deliberately a list of *pairs* rather than a bare lemma list.
    Only a small, non-random fraction of tokens carry an ``<ana>`` block, so
    comparing a lemma list against the full surface list would compare two
    different samples and the resulting "asymmetry" would mean nothing. Pairing
    keeps both streams over the same tokens, which is the only way the
    comparison is honest.
    """

    name: str
    sentences: int = 0
    forms: list[str] = field(default_factory=list)
    pairs: list[tuple[str, str]] = field(default_factory=list)


def iter_documents(path: Path, *, limit: int | None = None) -> Iterator[Document]:
    """Stream documents out of a crawl part.

    Args:
        path: Path to ``web2-4p-N.tar.gz``.
        limit: Stop after this many documents. ``None`` reads the whole part.

    Yields:
        One :class:`Document` per archive member.
    """
    seen = 0
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            text = handle.read().decode("iso-8859-2", errors="replace")
            yield _parse(member.name, text)
            seen += 1
            if limit is not None and seen >= limit:
                return


def _parse(name: str, text: str) -> Document:
    """Scan one document's markup, pairing each lemma with its own surface form."""
    doc = Document(name=name)
    current: str | None = None
    for line in text.splitlines():
        if line.startswith(_SENTENCE_OPEN):
            doc.sentences += 1
        elif line.startswith(_WORD_OPEN):
            form = line[len(_WORD_OPEN) :].strip()
            current = form or None
            if form:
                doc.forms.append(form)
        elif line.startswith(_WORD_CLOSE):
            current = None
        elif current is not None and "<lemma>" in line:
            match = _LEMMA_RE.search(line)
            if match and match.group(1).strip():
                doc.pairs.append((current, match.group(1).strip()))
                # One analysis per token: ignore any further readings.
                current = None
    return doc
