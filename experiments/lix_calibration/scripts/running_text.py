"""Reading running text, and measuring a real LIX on it.

The frequency lists give word-length distributions, which is all the threshold
calibration needs. They cannot give *B*. Every LIX score in this study therefore
came from one source — a MOKK crawl part — and the Swedish reference had no LIX
score at all, only a length curve.

The Leipzig archives already on disk fix that. Alongside the ``-words.txt`` this
study has always read, each carries a ``-sentences.txt``: one million sentences,
``id<TAB>text``, UTF-8. So *A*, *B* and *C* are available for **both** languages,
from the same project, under the same sampling.

Two things about that source decide whether a number from it means anything.

**The sentences are a sample, not a text.** Leipzig collections are sampled and
deduplicated, so there are no documents and no discourse order. Both LIX terms
are ratios — mean sentence length and long-word share — and a random sentence
sample estimates both without bias, so the *point estimates* are sound. What is
not sound is treating a window of sentences as a document: windows drawn from
shuffled sentences are more alike than real texts are, so the spread is too
narrow. Compare the two languages to each other, not the spread to a corpus of
real documents.

**The tar is opened in stream mode, so members are not seekable.** Wrapping one
in ``TextIOWrapper`` raises ``AttributeError: '_Stream' object has no attribute
'seekable'``. The same trap is documented in ``leipzig.py``; the fix here is an
incremental decoder over fixed-size chunks, which also keeps memory flat on a
146 MB member.
"""

from __future__ import annotations

import codecs
import statistics
import tarfile
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from saphes.readability import lix_from_counts, word_length
from saphes.segment import words as split_words

CHUNK = 1 << 20
DEFAULT_WINDOW = 25


@dataclass(frozen=True, slots=True)
class CorpusLix:
    """LIX measured on running text, with the counts that produced it.

    Attributes:
        label: Which corpus, and under which policy.
        words: *A*.
        sentences: *B*.
        long_words: *C*.
        threshold: The long-word threshold used.
        length_policy: How letters were counted.
        score: ``A/B + 100*C/A``.
        window: Sentences per window, or ``None`` if windows were not collected.
        windows: One LIX score per window.
        spans: ``(words, long_words)`` per sentence, kept so a different window
            size can be formed without re-reading the corpus. The window length
            is an arbitrary choice, so being able to vary it cheaply is what
            makes the stability check affordable.
    """

    label: str
    words: int
    sentences: int
    long_words: int
    threshold: int
    length_policy: str
    score: float
    window: int | None
    windows: tuple[float, ...] = field(repr=False, default=())
    spans: tuple[tuple[int, int], ...] = field(repr=False, default=())

    def windows_at(self, size: int) -> tuple[float, ...]:
        """Re-window the per-sentence counts at a different size.

        Args:
            size: Sentences per window.

        Returns:
            One LIX score per complete window. A trailing partial window is
            dropped rather than scored on fewer sentences.

        Raises:
            ValueError: If ``size`` is not positive, or no spans were kept.
        """
        if size <= 0:
            msg = f"size must be positive, got {size}"
            raise ValueError(msg)
        if not self.spans:
            msg = (
                f"{self.label!r} kept no per-sentence spans to re-window; "
                "pass keep_spans=True to corpus_lix"
            )
            raise ValueError(msg)
        scores = []
        for start in range(0, len(self.spans) - size + 1, size):
            chunk = self.spans[start : start + size]
            words = sum(w for w, _ in chunk)
            long_words = sum(c for _, c in chunk)
            scores.append(
                lix_from_counts(words=words, sentences=size, long_words=long_words)
            )
        return tuple(scores)

    @property
    def mean_sentence_length(self) -> float:
        """*A/B*."""
        return self.words / self.sentences

    @property
    def long_word_share(self) -> float:
        """*C/A*."""
        return self.long_words / self.words

    def quantile(self, fraction: float) -> float:
        """The window-LIX at a given fraction of the distribution.

        Raises:
            ValueError: If no windows were collected, or ``fraction`` is not in
                ``[0, 1]``.
        """
        if not self.windows:
            msg = f"{self.label!r} has no window distribution to take a quantile of"
            raise ValueError(msg)
        if not 0.0 <= fraction <= 1.0:
            msg = f"fraction must be in [0, 1], got {fraction}"
            raise ValueError(msg)
        ordered = sorted(self.windows)
        index = round(fraction * (len(ordered) - 1))
        return ordered[index]

    def summary(self) -> str:
        """One line for the log."""
        return (
            f"{self.label}: A={self.words:,} B={self.sentences:,} "
            f"A/B={self.mean_sentence_length:.2f} "
            f"C/A={self.long_word_share:.4f} LIX={self.score:.2f}"
        )


def _iter_lines(fobj, encoding: str = "utf-8") -> Iterator[str]:  # noqa: ANN001
    """Yield decoded lines from a non-seekable stream, in bounded memory."""
    decoder = codecs.getincrementaldecoder(encoding)()
    buffer = ""
    while chunk := fobj.read(CHUNK):
        buffer += decoder.decode(chunk)
        *complete, buffer = buffer.split("\n")
        yield from complete
    buffer += decoder.decode(b"", True)
    if buffer:
        yield buffer


def read_leipzig_sentences(path: Path, *, limit: int | None = None) -> Iterator[str]:
    """Yield sentences from a Leipzig archive's ``-sentences.txt`` member.

    Args:
        path: A ``*_1M.tar.gz`` from the Leipzig Corpora Collection.
        limit: Stop after this many sentences. ``None`` reads all of them.

    Yields:
        Sentence text, with the leading numeric id and tab removed.

    Raises:
        LookupError: If the archive has no ``-sentences.txt`` member.
    """
    with tarfile.open(path, "r|gz") as archive:
        for member in archive:
            if not member.name.endswith("-sentences.txt"):
                continue
            handle = archive.extractfile(member)
            if handle is None:  # pragma: no cover - directory entry
                continue
            for index, line in enumerate(_iter_lines(handle)):
                if limit is not None and index >= limit:
                    return
                _, _, text = line.partition("\t")
                text = text.strip()
                if text:
                    yield text
            return
    msg = f"{path.name} has no -sentences.txt member"
    raise LookupError(msg)


def corpus_lix(
    sentences: Iterable[str],
    *,
    label: str,
    threshold: int,
    length_policy: Callable[[str], int] | str = "nfc",
    window: int | None = DEFAULT_WINDOW,
    keep_spans: bool = False,
) -> CorpusLix:
    """Measure LIX over running text, one sentence at a time.

    Args:
        sentences: Sentence strings. Consumed once; a generator is fine.
        label: What to call the result.
        threshold: Long-word threshold. A word is long at ``length > threshold``.
        length_policy: Passed to ``word_length``. Defaults to ``"nfc"``.
        window: Sentences per window for the distribution, or ``None`` to skip
            it. Defaults to 25 — short-article length, and arbitrary, so it is a
            parameter.
        keep_spans: Retain the per-sentence counts so the result can be
            re-windowed later. Defaults to ``False``: a span per sentence is
            cheap for one corpus and expensive for a panel of them, and only the
            two curves in a band mapping ever need re-windowing.

    Returns:
        A :class:`CorpusLix`.

    Raises:
        ValueError: If no sentence yielded a token, or ``window`` is not
            positive.
    """
    if window is not None and window <= 0:
        msg = f"window must be positive, got {window}"
        raise ValueError(msg)

    total_words = total_sentences = total_long = 0
    windows: list[float] = []
    spans: list[tuple[int, int]] = []
    span_words = span_long = span_sentences = 0

    for sentence in sentences:
        tokens = split_words(sentence)
        if not tokens:
            continue
        long_words = sum(
            1 for t in tokens if word_length(t, policy=length_policy) > threshold
        )
        total_words += len(tokens)
        total_long += long_words
        total_sentences += 1
        if keep_spans:
            spans.append((len(tokens), long_words))
        if window is None:
            continue
        span_words += len(tokens)
        span_long += long_words
        span_sentences += 1
        if span_sentences == window:
            windows.append(
                lix_from_counts(
                    words=span_words, sentences=span_sentences, long_words=span_long
                )
            )
            span_words = span_long = span_sentences = 0

    if total_sentences == 0:
        msg = f"no sentence in {label!r} yielded a token; the score would be undefined"
        raise ValueError(msg)

    return CorpusLix(
        label=label,
        words=total_words,
        sentences=total_sentences,
        long_words=total_long,
        threshold=threshold,
        length_policy=_policy_label(length_policy),
        score=lix_from_counts(
            words=total_words, sentences=total_sentences, long_words=total_long
        ),
        window=window,
        windows=tuple(windows),
        spans=tuple(spans),
    )


def _policy_label(policy: Callable[[str], int] | str) -> str:
    """Name a length policy for the record."""
    if callable(policy):
        return f"custom:{getattr(policy, '__qualname__', None) or repr(policy)}"
    return str(policy)


def describe(result: CorpusLix) -> str:
    """A one-line distribution summary, or a note that there is none."""
    if not result.windows:
        return "no window distribution"
    return (
        f"windows={len(result.windows):,} of {result.window} sentences  "
        f"p10={result.quantile(0.10):.1f} "
        f"p50={statistics.median(result.windows):.1f} "
        f"p90={result.quantile(0.90):.1f}"
    )
