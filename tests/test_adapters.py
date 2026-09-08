"""Tests for the parser adapters, against recorded output from real parsers.

The fixtures in ``tests/fixtures/`` are **not hand-written**. They are what
HuSpaCy 3.8 (``hu_core_news_md`` 3.8.0) and emtsv actually produced for the
fifteen Hungarian sentences in
``experiments/adapter_fixtures/corpus.txt`` — legalese, statute references,
verbless clauses, distant igekötők, an em-dash aside and nested brackets. The
generators live in that experiment; neither can run in CI, so their output is
committed and replayed here.

Replaying rather than parsing is the point: ``from_spacy`` is duck-typed, so a
recording of the attributes it reads is a complete stand-in for a ``Doc``, and
these tests import neither spaCy nor Docker.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from saphes import DepToken, mean_dependency_distance, mean_hierarchical_distance
from saphes.adapters import from_conllu, from_spacy

FIXTURES = Path(__file__).parent / "fixtures"
HUSPACY = json.loads((FIXTURES / "huspacy.json").read_text())
EMTSV = (FIXTURES / "emtsv.conllu").read_text()


def replay(record: dict) -> SimpleNamespace:
    """Rebuild a duck-typed ``Doc`` from one recorded HuSpaCy sentence.

    Only the attributes ``from_spacy`` reads are reconstructed. If the adapter
    ever starts reading something else, this stops being a valid stand-in and
    the test fails with an ``AttributeError`` rather than passing hollowly.
    """
    tokens = [
        SimpleNamespace(
            i=t["i"], head=None, pos_=t["pos"], is_punct=t["is_punct"], text=t["text"]
        )
        for t in record["tokens"]
    ]
    by_index = {token.i: token for token in tokens}
    for token, raw in zip(tokens, record["tokens"], strict=True):
        token.head = by_index[raw["head_i"]]
    return SimpleNamespace(sents=[tokens])


def huspacy_parses() -> list[list[DepToken]]:
    return [from_spacy(replay(sent))[0] for sent in HUSPACY["sentences"]]


class TestFromConllu:
    """The CoNLL-U reader, on real emtsv output."""

    def test_reads_every_sentence(self) -> None:
        assert len(from_conllu(EMTSV)) == 15

    def test_indices_are_contiguous(self) -> None:
        for parse in from_conllu(EMTSV):
            assert [t.index for t in parse] == list(range(1, len(parse) + 1))

    def test_every_sentence_has_a_root(self) -> None:
        for parse in from_conllu(EMTSV):
            assert any(token.head == 0 for token in parse)

    def test_it_measures_end_to_end(self) -> None:
        result = mean_dependency_distance(from_conllu(EMTSV))
        assert result.sentences == 15
        assert result.mdd > 1.0

    def test_a_header_row_is_refused(self) -> None:
        """The default emtsv output has a header and a different column order."""
        native = (
            "form\twsafter\tanas\tlemma\txpostag\tupostag\tfeats\tid\tdeprel\thead\n"
        )
        with pytest.raises(ValueError, match="ID and HEAD must be integers"):
            from_conllu(native)

    def test_too_few_columns_names_the_line(self) -> None:
        with pytest.raises(ValueError, match="line 1: CoNLL-U needs 10"):
            from_conllu("1\tA\tDET\n")

    def test_comments_and_blank_lines_are_skipped(self) -> None:
        text = "# sent_id = 1\n1\tA\ta\tDET\t_\t_\t0\troot\t_\t_\n\n\n"
        assert len(from_conllu(text)) == 1

    def test_ranges_and_empty_nodes_are_skipped(self) -> None:
        """Per the specification, neither bears a dependency arc."""
        text = (
            "1-2\tvamos\t_\t_\t_\t_\t_\t_\t_\t_\n"
            "1\tvamos\tir\tVERB\t_\t_\t0\troot\t_\t_\n"
            "2\tnos\tnos\tPRON\t_\t_\t1\tobj\t_\t_\n"
            "2.1\t_\t_\t_\t_\t_\t_\t_\t_\t_\n"
        )
        assert [token.index for token in from_conllu(text)[0]] == [1, 2]

    def test_fields_are_split_on_tabs_not_whitespace(self) -> None:
        """A space inside a field must not shift the columns after it.

        CoNLL-U is tab-separated, and several treebanks put spaces in FORM or
        LEMMA. Splitting on whitespace would read DEPREL as HEAD here.
        """
        text = "1\tNew York\tNew York\tPROPN\t_\t_\t0\troot\t_\t_\n"
        assert from_conllu(text)[0] == [DepToken(1, 0, False, "PROPN")]

    def test_the_pos_tag_is_carried_through(self) -> None:
        text = "1\tkutya\tkutya\tNOUN\t_\t_\t0\troot\t_\t_\n"
        assert from_conllu(text)[0][0].pos == "NOUN"

    def test_punct_tags_is_a_parameter(self) -> None:
        text = "1\t(\t(\tPROPN\t_\t_\t0\troot\t_\t_\n"
        assert from_conllu(text)[0][0].is_punct is False
        widened = from_conllu(text, punct_tags=frozenset({"PUNCT", "PROPN"}))
        assert widened[0][0].is_punct is True


class TestFromSpacy:
    """The duck-typed spaCy reader, on recorded HuSpaCy output."""

    def test_reads_every_sentence(self) -> None:
        assert len(huspacy_parses()) == 15

    def test_indices_are_renumbered_from_one(self) -> None:
        for parse in huspacy_parses():
            assert [t.index for t in parse] == list(range(1, len(parse) + 1))

    def test_the_self_loop_root_becomes_zero(self) -> None:
        """The root is marked in spaCy by making a token its own head."""
        first = huspacy_parses()[0]
        assert [t.head for t in first] == [2, 3, 0, 3]

    def test_document_global_indices_are_made_local(self) -> None:
        doc = SimpleNamespace(
            sents=[
                [
                    SimpleNamespace(i=7, head=None, pos_="NOUN", is_punct=False),
                    SimpleNamespace(i=8, head=None, pos_="VERB", is_punct=False),
                ]
            ]
        )
        doc.sents[0][0].head = doc.sents[0][1]
        doc.sents[0][1].head = doc.sents[0][1]
        assert from_spacy(doc)[0] == [
            DepToken(1, 2, False, "NOUN"),
            DepToken(2, 0, False, "VERB"),
        ]

    def test_punctuation_comes_from_is_punct_not_the_tag(self) -> None:
        """Real HuSpaCy output tags '(' as PROPN while setting is_punct."""
        tagged_propn = [
            (token["text"], token["pos"], token["is_punct"])
            for sent in HUSPACY["sentences"]
            for token in sent["tokens"]
            if token["is_punct"] and token["pos"] != "PUNCT"
        ]
        assert tagged_propn, "fixture no longer covers the tag/is_punct mismatch"
        for _text, pos, _ in tagged_propn:
            assert pos != "PUNCT"
        marked = [t for parse in huspacy_parses() for t in parse if t.is_punct]
        assert any(token.pos != "PUNCT" for token in marked)

    def test_an_object_without_sents_is_refused(self) -> None:
        with pytest.raises(TypeError, match="needs an object with .sents"):
            from_spacy(SimpleNamespace())

    def test_a_head_outside_the_sentence_raises(self) -> None:
        stray = SimpleNamespace(i=99, head=None, pos_="X", is_punct=False)
        inside = SimpleNamespace(i=0, head=stray, pos_="X", is_punct=False)
        stray.head = stray
        with pytest.raises(ValueError, match=r"tokens 0\.\.0"):
            from_spacy(SimpleNamespace(sents=[[inside]]))

    def test_it_measures_end_to_end(self) -> None:
        result = mean_dependency_distance(huspacy_parses())
        assert result.sentences == 15
        assert result.mdd > 1.0

    def test_an_empty_sentence_is_skipped_not_emitted(self) -> None:
        """A Doc can carry a whitespace-only span; it is not a parse."""
        token = SimpleNamespace(i=0, head=None, pos_="VERB", is_punct=False)
        token.head = token
        doc = SimpleNamespace(sents=[[], [token]])
        assert from_spacy(doc) == [[DepToken(1, 0, False, "VERB")]]


class TestEngineParity:
    """What the two engines agree and disagree about, on the same sentences.

    These are not correctness assertions about either parser. They pin the
    *shape* of the disagreement, so that a change in either fixture shows up as
    a failing expectation rather than a silently different number.
    """

    def test_both_engines_produce_the_same_sentence_count(self) -> None:
        assert len(from_conllu(EMTSV)) == len(huspacy_parses()) == 15

    def test_emtsv_makes_final_punctuation_a_second_root(self) -> None:
        """Final punctuation goes to 0 in emtsv, and to the verb in HuSpaCy."""
        emtsv_roots = [
            sum(1 for token in parse if token.head == 0) for parse in from_conllu(EMTSV)
        ]
        spacy_roots = [
            sum(1 for token in parse if token.head == 0) for parse in huspacy_parses()
        ]
        assert all(count == 2 for count in emtsv_roots)
        assert all(count == 1 for count in spacy_roots)

    def test_require_single_root_would_discard_all_of_emtsv(self) -> None:
        """The trap: the filter must not be applied before punctuation is collapsed.

        ``require_single_root`` counts roots over *all* tokens, punctuation
        included, so on emtsv output every sentence looks fragmented.
        """
        with pytest.raises(ValueError, match="no sentence yielded"):
            mean_dependency_distance(from_conllu(EMTSV), require_single_root=True)
        kept = mean_dependency_distance(huspacy_parses(), require_single_root=True)
        assert kept.sentences == 15

    def test_the_two_engines_disagree_about_the_score(self) -> None:
        """Same sentences, same formula, different trees — so different numbers."""
        emtsv = mean_dependency_distance(from_conllu(EMTSV)).mdd
        spacy = mean_dependency_distance(huspacy_parses()).mdd
        assert emtsv != pytest.approx(spacy, abs=0.01)

    def test_the_engines_invert_between_the_two_metrics(self) -> None:
        """HuSpaCy trees are flatter with longer arcs; emtsv's are deeper with shorter.

        This is the case Jing & Liu (2015) propose MHD for: the two metrics come
        apart, and here they come apart *because of the annotation scheme* rather
        than the text, since both engines read the same fifteen sentences.
        """
        emtsv, spacy = from_conllu(EMTSV), huspacy_parses()
        assert mean_dependency_distance(spacy).mdd > mean_dependency_distance(emtsv).mdd
        assert (
            mean_hierarchical_distance(spacy).mhd
            < mean_hierarchical_distance(emtsv).mhd
        )

    def test_emtsv_builds_deeper_trees(self) -> None:
        assert (
            mean_hierarchical_distance(from_conllu(EMTSV)).max_depth
            > mean_hierarchical_distance(huspacy_parses()).max_depth
        )

    def test_both_land_in_a_plausible_range(self) -> None:
        """Published MDD for European languages sits between about 2 and 3.

        Measured here on 15 short sentences, so this is a sanity bound, not a
        finding. It exists to catch an adapter that silently halves every
        distance, which no other assertion here would notice.
        """
        for parses in (from_conllu(EMTSV), huspacy_parses()):
            assert 1.0 < mean_dependency_distance(parses).mdd < 4.0
