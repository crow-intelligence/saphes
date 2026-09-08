"""Convert a parser's output into the token model :mod:`saphes.syntax` measures.

saphes does not parse. It measures parses, and every parser hands them over in a
different shape — so this module is the seam, and it is deliberately thin.

**Nothing here imports spaCy, HuSpaCy, emtsv or a CoNLL-U library.**
:func:`from_spacy` is duck-typed: it reads the attributes a spaCy ``Doc``
exposes and never asks what class it is, so it works on a real ``Doc``, on a
HuSpaCy ``Doc``, and on any object presenting the same handful of attributes.
:func:`from_conllu` is a plain text reader over the CoNLL-U specification. Both
therefore run in a CI job with no NLP stack installed, which is the only way the
package can keep ``dependencies = []``.

Three conversions matter, and each is a place a hand-written adapter goes wrong:

**spaCy marks the root with a self-loop.** ``token.head is token`` is how spaCy
says "no governor"; CoNLL-U writes ``0``. :func:`from_spacy` translates it. Left
alone it reaches :func:`saphes.syntax.mean_dependency_distance` as a token
governing itself, which raises — loudly, but for a confusing reason.

**spaCy indices are document-global; saphes wants them sentence-local.** A
five-sentence document numbers its last sentence's tokens from wherever it
starts, and dependency distance is a within-sentence measure.

**Punctuation is what the parser says it is, not what the tag says.** In real
HuSpaCy output a bracket comes back tagged ``PROPN`` with ``is_punct=True``, and
other tokens hang off it. :func:`from_spacy` therefore reads ``is_punct``;
:func:`from_conllu`, which has no such attribute, falls back to the UPOS tag and
says so.

Neither function computes anything. They rename and renumber; the arithmetic is
in :mod:`saphes.syntax`, and the structural validation happens there too, so a
malformed parse is caught in one place rather than two.
"""

from __future__ import annotations

from typing import Any

from saphes.syntax import DepToken

__all__ = ["from_conllu", "from_spacy"]

_MULTIWORD = "-"
_EMPTY_NODE = "."
DEFAULT_PUNCT_TAGS = frozenset({"PUNCT"})
"""UPOS tags :func:`from_conllu` treats as punctuation, by default just ``PUNCT``."""


def from_spacy(doc: Any) -> list[list[DepToken]]:  # noqa: ANN401 - a spaCy Doc, which we cannot import
    """Convert a spaCy or HuSpaCy ``Doc`` into parsed sentences.

    Duck-typed. The ``Doc`` is never imported, only read: this function needs
    ``doc.sents``, and on each token ``i``, ``head``, ``is_punct`` and ``pos_``.
    Any object supplying those works, which is what makes the tests able to
    replay a recorded parse without spaCy installed.

    Args:
        doc: A parsed ``Doc``. The pipeline must include a parser — a
            ``senter``-only pipeline has no ``head`` to read, and a
            parser-less one silently makes every token its own root.

    Returns:
        One list of :class:`~saphes.syntax.DepToken` per sentence, indices
        renumbered from 1 within each sentence, ready for
        :func:`saphes.syntax.mean_dependency_distance`.

    Raises:
        TypeError: If ``doc`` has no ``sents`` attribute.
        ValueError: If a token's head lies outside its own sentence, which
            means the sentence boundaries and the parse disagree.

    Contract:
        Preconditions:

        - ``doc.sents`` must be available. On a spaCy ``Doc`` that needs a
          parser or a ``senter`` in the pipeline; without one spaCy raises
          its own error, which is left to propagate rather than wrapped.

        Guarantees:

        - Indices in each returned sentence run 1..n in order.
        - The root, which spaCy marks by making a token its own head, comes
          back as ``head=0``.
        - Token order and count are preserved exactly; no token is dropped,
          including punctuation. Dropping is
          :func:`~saphes.syntax.mean_dependency_distance`'s job, under a
          policy the caller chooses.

        Silences:

        - ``pos_`` is copied but never checked. A model with an unusual
          tagset passes through unaltered.
        - Whether a token is punctuation is taken from ``is_punct`` alone.
          Real HuSpaCy output tags ``(`` as ``PROPN`` while setting
          ``is_punct=True``, so reading the tag instead would give a
          different — and wrong — answer.

    Examples:
        A stand-in for a parsed ``Doc``, which is all this function requires:

        >>> from types import SimpleNamespace
        >>> def token(i, head, pos, punct=False):
        ...     return SimpleNamespace(i=i, head=None, pos_=pos, is_punct=punct)
        >>> toks = [token(0, 1, "DET"), token(1, 2, "NOUN"),
        ...         token(2, 2, "VERB"), token(3, 2, "PUNCT", True)]
        >>> for tok, head in zip(toks, [1, 2, 2, 2]):
        ...     tok.head = toks[head]
        >>> doc = SimpleNamespace(sents=[SimpleNamespace(start=0, __iter__=None)])
        >>> doc = SimpleNamespace(sents=[toks])
        >>> from_spacy(doc)
        [[DepToken(index=1, head=2, is_punct=False, pos='DET'), \
DepToken(index=2, head=3, is_punct=False, pos='NOUN'), \
DepToken(index=3, head=0, is_punct=False, pos='VERB'), \
DepToken(index=4, head=3, is_punct=True, pos='PUNCT')]]

        The verb is its own head in spaCy's encoding and becomes ``head=0``.
    """
    sents = getattr(doc, "sents", None)
    if sents is None:
        msg = (
            "from_spacy() needs an object with .sents, such as a parsed spaCy "
            "or HuSpaCy Doc. Got an object without it; if this is a Doc, its "
            "pipeline has no parser and no senter."
        )
        raise TypeError(msg)

    parses: list[list[DepToken]] = []
    for sentence in sents:
        tokens = list(sentence)
        if not tokens:
            continue
        offset = tokens[0].i
        local = {token.i: position for position, token in enumerate(tokens, start=1)}
        converted: list[DepToken] = []
        for token in tokens:
            head_i = token.head.i
            if head_i == token.i:
                head = 0  # spaCy's self-loop is CoNLL-U's 0
            elif head_i in local:
                head = local[head_i]
            else:
                msg = (
                    f"token {token.i} has head {head_i}, which is outside its "
                    f"own sentence (tokens {offset}..{tokens[-1].i}). The "
                    "sentence boundaries and the parse disagree; re-run the "
                    "pipeline with the parser enabled before the senter."
                )
                raise ValueError(msg)
            converted.append(
                DepToken(local[token.i], head, bool(token.is_punct), token.pos_)
            )
        parses.append(converted)
    return parses


def from_conllu(
    text: str, *, punct_tags: frozenset[str] = DEFAULT_PUNCT_TAGS
) -> list[list[DepToken]]:
    r"""Parse CoNLL-U text into sentences of :class:`~saphes.syntax.DepToken`.

    A plain reader over the CoNLL-U specification: ten tab-separated columns,
    ``#`` comment lines, blank lines between sentences. This is the path for
    treebanks and for emtsv's ``tok-dep-conll`` output.

    Args:
        text: The contents of a ``.conllu`` file.
        punct_tags: UPOS tags to treat as punctuation. Defaults to
            ``{"PUNCT"}``. Widen it for a tagset that marks punctuation
            differently; the choice changes the score, so it is a parameter
            rather than a constant.

    Returns:
        One list of tokens per sentence, in file order. Sentences that end up
        empty are omitted.

    Raises:
        ValueError: If a line has fewer than 10 columns, or if ``ID`` or
            ``HEAD`` is not an integer where one is required.

    Contract:
        Preconditions:

        - Columns are positional, per the specification: ``ID FORM LEMMA
          UPOS XPOS FEATS HEAD DEPREL DEPS MISC``. **A header row is not
          part of CoNLL-U**; a file that has one is not read by this
          function, and emtsv's *native* TSV output — which does carry a
          header, in a different column order — must be produced as
          ``tok-dep-conll`` instead.

        Guarantees:

        - Multi-word token ranges (``1-2``) and empty nodes (``1.1``) are
          skipped, as the specification requires, leaving the integer-ID
          tokens that carry the dependency tree.
        - Indices are used exactly as the file gives them and are not
          renumbered, so a malformed file fails
          :func:`~saphes.syntax.mean_dependency_distance`'s contiguity check
          rather than being quietly repaired here.

        Silences:

        - Punctuation is inferred from the UPOS tag, because CoNLL-U has no
          equivalent of spaCy's ``is_punct``. A treebank that tags a bracket
          as ``PROPN`` — as HuSpaCy does — will have it counted as a word.
          This is a real difference between the two adapters, not an
          oversight.
        - ``DEPREL``, ``FEATS``, ``DEPS`` and ``MISC`` are read past and
          discarded. Only position, head and tag reach saphes.

    Examples:
        >>> conllu = '''# sent_id = 1
        ... # text = A kutya ugat.
        ... 1\tA\ta\tDET\t_\t_\t2\tdet\t_\t_
        ... 2\tkutya\tkutya\tNOUN\t_\t_\t3\tnsubj\t_\t_
        ... 3\tugat\tugat\tVERB\t_\t_\t0\troot\t_\t_
        ... 4\t.\t.\tPUNCT\t_\t_\t3\tpunct\t_\t_
        ... '''
        >>> parses = from_conllu(conllu)
        >>> len(parses)
        1
        >>> parses[0][2]
        DepToken(index=3, head=0, is_punct=False, pos='VERB')
        >>> parses[0][3].is_punct
        True

        A multi-word range is skipped in favour of its parts:

        >>> mwt = '''1-2\tvamos\t_\t_\t_\t_\t_\t_\t_\t_
        ... 1\tvamos\tir\tVERB\t_\t_\t0\troot\t_\t_
        ... 2\tnos\tnos\tPRON\t_\t_\t1\tobj\t_\t_
        ... '''
        >>> [token.index for token in from_conllu(mwt)[0]]
        [1, 2]
    """
    parses: list[list[DepToken]] = []
    current: list[DepToken] = []
    for number, line in enumerate(text.splitlines(), start=1):
        # splitlines() has already removed the line terminator, so nothing here
        # strips one; a stray \r would be part of the last field and is the
        # caller's to deal with.
        if not line.strip():
            if current:
                parses.append(current)
                current = []
            continue
        if line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 10:
            msg = (
                f"line {number}: CoNLL-U needs 10 tab-separated columns, found "
                f"{len(fields)}. If this file has a header row or a different "
                "column order it is not CoNLL-U — emtsv's native output is not, "
                "and must be produced with the tok-dep-conll task instead."
            )
            raise ValueError(msg)
        token_id = fields[0]
        if _MULTIWORD in token_id or _EMPTY_NODE in token_id:
            continue  # a range or an empty node, neither of which bears an arc
        try:
            index = int(token_id)
            head = int(fields[6])
        except ValueError as exc:
            msg = (
                f"line {number}: ID and HEAD must be integers, got "
                f"{token_id!r} and {fields[6]!r}"
            )
            raise ValueError(msg) from exc
        upos = fields[3]
        current.append(DepToken(index, head, upos in punct_tags, upos))
    if current:
        parses.append(current)
    return parses
