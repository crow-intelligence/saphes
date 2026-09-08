"""Tests for the loan-word ratio and the phonotactic heuristic.

The metric's silent failure is a surface stream: inflected forms miss the
lexicon, so a wrong token stream reports a plausible *low* ratio rather than an
error. `TestSurfaceFormsAreTheTrap` pins that, and `tests/test_contracts.py`
guards the parameter names that make it hard to reach by accident.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saphes import loan_ratio_from_counts, loanword_ratio
from tests.strategies import hungarian_word

LEXICON = {"komputer", "internet", "absztrakt", "szoftver"}


class TestKernel:
    """loan_ratio_from_counts validates rather than returning a plausible number."""

    def test_worked_value(self) -> None:
        assert loan_ratio_from_counts(matched=1, total=4) == 0.25

    def test_none_matched(self) -> None:
        assert loan_ratio_from_counts(matched=0, total=4) == 0.0

    def test_all_matched(self) -> None:
        assert loan_ratio_from_counts(matched=4, total=4) == 1.0

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one lemma"):
            loan_ratio_from_counts(matched=0, total=0)

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            loan_ratio_from_counts(matched=-1, total=4)

    def test_transposed_arguments_raise(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed total"):
            loan_ratio_from_counts(matched=4, total=1)

    def test_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            loan_ratio_from_counts(1, 4)  # type: ignore[misc]


class TestLexiconMatching:
    """The dictionary path, which is the one that carries evidence."""

    def test_worked_example(self) -> None:
        result = loanword_ratio(
            ["a", "komputer", "gyors", "lenni"], lexicon={"komputer"}
        )
        assert result.ratio == 0.25
        assert result.matched == 1
        assert result.total_lemmas == 4
        assert result.matches == ("komputer",)

    def test_case_is_folded_by_default(self) -> None:
        assert loanword_ratio(["Komputer"], lexicon={"komputer"}).matched == 1

    def test_case_folding_can_be_turned_off(self) -> None:
        result = loanword_ratio(["Komputer"], lexicon={"komputer"}, case_fold=False)
        assert result.matched == 0
        assert result.case_folded is False

    def test_decomposed_input_still_matches(self) -> None:
        """NFC first, so a decomposed lemma finds a composed lexicon entry."""
        decomposed = "elóad́as".replace("́", "́")
        assert (
            loanword_ratio(
                [decomposed],
                lexicon={__import__("unicodedata").normalize("NFC", decomposed)},
            ).matched
            == 1
        )

    def test_repeated_lemmas_are_token_weighted(self) -> None:
        result = loanword_ratio(["komputer"] * 3 + ["kutya"], lexicon={"komputer"})
        assert result.matched == 3
        assert result.total_lemmas == 4
        assert result.matches == ("komputer",)
        assert result.ratio == 0.75

    def test_lexicon_size_is_recorded(self) -> None:
        assert loanword_ratio(["kutya"], lexicon=LEXICON).lexicon_size == 4

    def test_a_non_sized_container_reports_no_size(self) -> None:
        class Everything:
            def __contains__(self, item: object) -> bool:
                return True

        result = loanword_ratio(["kutya"], lexicon=Everything())
        assert result.lexicon_size is None
        assert result.matched == 1


class TestExclusions:
    """saphes does no NER; proper nouns are excluded only when tags are supplied."""

    def test_propn_is_excluded_when_tagged(self) -> None:
        result = loanword_ratio(
            ["Wesselényi", "taxi"], lexicon={"taxi"}, pos_tags=["PROPN", "NOUN"]
        )
        assert result.excluded == 1
        assert result.total_lemmas == 1
        assert result.matched == 1
        assert result.matches == ("taxi",)

    def test_exclude_tags_is_a_parameter(self) -> None:
        result = loanword_ratio(
            ["taxi", "watt"],
            lexicon={"taxi", "watt"},
            pos_tags=["NOUN", "X"],
            exclude_tags={"X"},
        )
        assert result.excluded == 1
        assert result.total_lemmas == 1

    def test_an_explicit_exclude_set(self) -> None:
        result = loanword_ratio(["taxi", "watt"], lexicon=LEXICON, exclude={"watt"})
        assert result.excluded == 1
        assert result.total_lemmas == 1

    def test_mismatched_tag_length_raises(self) -> None:
        with pytest.raises(ValueError, match="must be parallel"):
            loanword_ratio(["a", "b"], lexicon=LEXICON, pos_tags=["NOUN"])

    def test_excluding_everything_raises(self) -> None:
        with pytest.raises(ValueError, match="every lemma was excluded"):
            loanword_ratio(["Wesselényi"], lexicon=LEXICON, pos_tags=["PROPN"])


class TestRefusals:
    """Empty and under-specified input raises rather than returning a number."""

    def test_a_raw_string_raises(self) -> None:
        with pytest.raises(TypeError, match="raw string"):
            loanword_ratio("komputer és internet", lexicon=LEXICON)  # type: ignore[arg-type]

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one lemma"):
            loanword_ratio([], lexicon=LEXICON)

    def test_a_missing_lexicon_is_a_type_error(self) -> None:
        """There is no fallback: the argument is required, not defaulted."""
        with pytest.raises(TypeError):
            loanword_ratio(["komputer"])  # type: ignore[call-arg]

    def test_an_empty_lexicon_is_allowed(self) -> None:
        """Explicitly supplying nothing is a choice; omitting it is not."""
        assert loanword_ratio(["komputer"], lexicon=set()).ratio == 0.0


class TestSurfaceFormsAreTheTrap:
    """The failure that produces no error and a plausible number."""

    def test_an_inflected_form_misses_the_lexicon(self) -> None:
        assert loanword_ratio(["komputerekkel"], lexicon={"komputer"}).ratio == 0.0

    def test_the_lemma_finds_it(self) -> None:
        assert loanword_ratio(["komputer"], lexicon={"komputer"}).ratio == 1.0

    def test_a_surface_stream_understates_the_ratio(self) -> None:
        surface = ["komputerekkel", "internetes", "kutyák"]
        lemma = ["komputer", "internet", "kutya"]
        assert (
            loanword_ratio(surface, lexicon=LEXICON).ratio
            < loanword_ratio(lemma, lexicon=LEXICON).ratio
        )

    def test_the_unit_is_recorded_so_the_mistake_is_visible(self) -> None:
        assert loanword_ratio(["kutya"], lexicon=LEXICON).unit == "lemma"


class TestResultRecord:
    """The result carries everything needed to audit the ratio."""

    def test_repr_shows_the_counts(self) -> None:
        text = repr(loanword_ratio(["komputer", "kutya"], lexicon={"komputer"}))
        assert "ratio=0.5000" in text
        assert "unit='lemma'" in text

    def test_repr_omits_the_version(self) -> None:
        import saphes

        assert saphes.__version__ not in repr(
            loanword_ratio(["kutya"], lexicon=LEXICON)
        )

    def test_records_the_saphes_version(self) -> None:
        import saphes

        result = loanword_ratio(["kutya"], lexicon=LEXICON)
        assert result.saphes_version == saphes.__version__

    def test_to_dict(self) -> None:
        record = loanword_ratio(["komputer"], lexicon={"komputer"}).to_dict()
        assert record["matched"] == 1
        assert record["unit"] == "lemma"

    def test_the_ratio_is_recomputable_from_the_record(self) -> None:
        result = loanword_ratio(["komputer", "taxi", "kutya"], lexicon={"komputer"})
        record = result.to_dict()
        assert record["matched"] / record["total_lemmas"] == pytest.approx(result.ratio)

    def test_lexicon_id_is_provenance_only(self) -> None:
        plain = loanword_ratio(["komputer"], lexicon={"komputer"})
        labelled = loanword_ratio(
            ["komputer"], lexicon={"komputer"}, lexicon_id="wiktionary-2026"
        )
        assert labelled.lexicon_id == "wiktionary-2026"
        assert labelled.ratio == plain.ratio


class TestLoanwordProperties:
    """Properties that must hold for any lemma stream."""

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=40))
    def test_the_ratio_is_a_proportion(self, lemmas: list[str]) -> None:
        result = loanword_ratio(lemmas, lexicon=LEXICON)
        assert 0.0 <= result.ratio <= 1.0

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=40))
    def test_matches_are_unique_and_bounded_by_the_count(
        self, lemmas: list[str]
    ) -> None:
        result = loanword_ratio(lemmas, lexicon=LEXICON)
        assert len(set(result.matches)) == len(result.matches)
        assert len(result.matches) <= result.matched


class TestBoundaries:
    """Cases found by mutation testing, each pinning something the docs promise."""

    def test_exclude_matches_the_lemma_or_the_raw_form(self) -> None:
        """Case folding must not defeat an exclusion written in original case."""
        result = loanword_ratio(
            ["Watt", "taxi"], lexicon={"taxi", "watt"}, exclude={"Watt"}
        )
        assert result.excluded == 1
        assert result.total_lemmas == 1
        assert result.matches == ("taxi",)

    def test_exclusions_accumulate(self) -> None:
        result = loanword_ratio(
            ["watt", "quart", "taxi"],
            lexicon={"taxi", "watt", "quart"},
            exclude={"watt", "quart"},
        )
        assert result.excluded == 2
        assert result.total_lemmas == 1

    def test_tagged_exclusions_accumulate(self) -> None:
        result = loanword_ratio(
            ["Tóth", "Németh", "taxi"],
            lexicon={"taxi"},
            pos_tags=["PROPN", "PROPN", "NOUN"],
        )
        assert result.excluded == 2

    def test_an_excluded_lemma_does_not_stop_the_scan(self) -> None:
        """The exclusion skips one token, it does not end the loop."""
        result = loanword_ratio(
            ["watt", "taxi"], lexicon={"taxi", "watt"}, exclude={"watt"}
        )
        assert result.matched == 1
        assert result.matches == ("taxi",)

    def test_a_tagged_exclusion_does_not_stop_the_scan(self) -> None:
        result = loanword_ratio(
            ["Tóth", "taxi"], lexicon={"taxi"}, pos_tags=["PROPN", "NOUN"]
        )
        assert result.matched == 1

    def test_lexicon_matches_accumulate(self) -> None:
        result = loanword_ratio(
            ["komputer", "internet", "kutya"], lexicon={"komputer", "internet"}
        )
        assert result.matched == 2
