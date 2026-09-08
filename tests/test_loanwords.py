"""Tests for the loan-word ratio and the phonotactic heuristic.

The metric's silent failure is a surface stream: inflected forms miss the
lexicon, so a wrong token stream reports a plausible *low* ratio rather than an
error. `TestSurfaceFormsAreTheTrap` pins that, and `tests/test_contracts.py`
guards the parameter names that make it hard to reach by accident.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saphes import (
    FOREIGN_PATTERNS,
    HEURISTIC_EXCEPTIONS,
    loan_ratio_from_counts,
    loanword_ratio,
)
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


class TestHeuristic:
    """The spelling fallback, which carries no evidence and says so."""

    def test_it_is_off_by_default(self) -> None:
        assert loanword_ratio(["taxi"], lexicon=set()).matched == 0

    def test_it_catches_what_the_lexicon_misses(self) -> None:
        result = loanword_ratio(["absztrakt", "taxi", "kutya"], heuristic=True)
        assert result.matched == 2
        assert result.matched_by_heuristic == 2
        assert result.matched_by_lexicon == 0

    def test_pattern_counts_name_what_fired(self) -> None:
        result = loanword_ratio(["absztrakt", "taxi"], heuristic=True)
        assert result.pattern_counts == (("absz", 1), ("x", 1))

    def test_lexicon_wins_over_heuristic_so_counts_do_not_double(self) -> None:
        result = loanword_ratio(["taxi"], lexicon={"taxi"}, heuristic=True)
        assert result.matched == 1
        assert result.matched_by_lexicon == 1
        assert result.matched_by_heuristic == 0
        assert result.pattern_counts == ()

    def test_the_two_sources_sum_to_the_total(self) -> None:
        result = loanword_ratio(
            ["komputer", "taxi", "kutya"], lexicon={"komputer"}, heuristic=True
        )
        assert result.matched == result.matched_by_lexicon + result.matched_by_heuristic

    @pytest.mark.parametrize(
        "word,pattern",
        [
            ("taxi", "x"),
            ("watt", "w"),
            ("quart", "q"),
            ("technika", "ch"),
            ("philosophia", "ph"),
            ("theologia", "th"),
            ("sztrada", "initial-sztr"),
            ("strategia", "initial-str"),
            ("spray", "initial-spr"),
            ("absztrakt", "absz"),
        ],
    )
    def test_each_pattern_fires(self, word: str, pattern: str) -> None:
        result = loanword_ratio([word], heuristic=True)
        assert pattern in dict(result.pattern_counts)

    @pytest.mark.parametrize(
        "word", ["gyors", "nyelv", "tyúk", "lyuk", "asztal", "ablak", "király"]
    )
    def test_native_words_do_not_fire(self, word: str) -> None:
        """`y` is half of gy/ly/ny/ty, so it must never be a marker on its own."""
        assert loanword_ratio([word], heuristic=True).matched == 0

    def test_assimilated_slavic_loans_are_not_flagged_by_spelling(self) -> None:
        """These are jövevényszavak: borrowed, but not felt as idegen szavak."""
        result = loanword_ratio(["ablak", "király", "pénz"], heuristic=True)
        assert result.matched == 0

    def test_patterns_are_substitutable(self) -> None:
        result = loanword_ratio(["kutya"], heuristic=True, patterns={"ku": r"^ku"})
        assert result.matched == 1
        assert result.pattern_counts == (("ku", 1),)

    def test_a_proper_noun_outside_the_exceptions_still_trips(self) -> None:
        """The residual failure: an unlisted surname is still flagged."""
        assert loanword_ratio(["Wagnerné"], heuristic=True).matched == 1


class TestExclusions:
    """saphes does no NER; proper nouns are excluded only when tags are supplied."""

    def test_propn_is_excluded_when_tagged(self) -> None:
        result = loanword_ratio(
            ["Wesselényi", "taxi"], heuristic=True, pos_tags=["PROPN", "NOUN"]
        )
        assert result.excluded == 1
        assert result.total_lemmas == 1
        assert result.matched == 1
        assert result.matches == ("taxi",)

    def test_exclude_tags_is_a_parameter(self) -> None:
        result = loanword_ratio(
            ["taxi", "watt"],
            heuristic=True,
            pos_tags=["NOUN", "X"],
            exclude_tags={"X"},
        )
        assert result.excluded == 1
        assert result.total_lemmas == 1

    def test_an_explicit_exclude_set(self) -> None:
        result = loanword_ratio(["taxi", "watt"], heuristic=True, exclude={"watt"})
        assert result.excluded == 1
        assert result.total_lemmas == 1

    def test_mismatched_tag_length_raises(self) -> None:
        with pytest.raises(ValueError, match="must be parallel"):
            loanword_ratio(["a", "b"], heuristic=True, pos_tags=["NOUN"])

    def test_excluding_everything_raises(self) -> None:
        with pytest.raises(ValueError, match="every lemma was excluded"):
            loanword_ratio(["Wesselényi"], heuristic=True, pos_tags=["PROPN"])


class TestRefusals:
    """Empty and under-specified input raises rather than returning a number."""

    def test_a_raw_string_raises(self) -> None:
        with pytest.raises(TypeError, match="raw string"):
            loanword_ratio("komputer és internet", lexicon=LEXICON)  # type: ignore[arg-type]

    def test_empty_input_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one lemma"):
            loanword_ratio([], lexicon=LEXICON)

    def test_neither_lexicon_nor_heuristic_raises(self) -> None:
        """Reporting 0.0 for every text would be a number about nothing."""
        with pytest.raises(ValueError, match="needs a lexicon"):
            loanword_ratio(["komputer"])

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

    def test_repr_warns_when_the_heuristic_did_the_work(self) -> None:
        text = repr(loanword_ratio(["taxi"], heuristic=True))
        assert "matched by spelling alone" in text

    def test_repr_omits_the_warning_without_heuristic_matches(self) -> None:
        text = repr(loanword_ratio(["komputer"], lexicon={"komputer"}))
        assert "matched by spelling alone" not in text

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
        result = loanword_ratio(
            ["komputer", "taxi", "kutya"], lexicon={"komputer"}, heuristic=True
        )
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
        result = loanword_ratio(lemmas, lexicon=LEXICON, heuristic=True)
        assert 0.0 <= result.ratio <= 1.0

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=40))
    def test_the_sources_partition_the_matches(self, lemmas: list[str]) -> None:
        result = loanword_ratio(lemmas, lexicon=LEXICON, heuristic=True)
        assert result.matched == (
            result.matched_by_lexicon + result.matched_by_heuristic
        )

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=40))
    def test_enabling_the_heuristic_never_lowers_the_ratio(
        self, lemmas: list[str]
    ) -> None:
        without = loanword_ratio(lemmas, lexicon=LEXICON).ratio
        with_it = loanword_ratio(lemmas, lexicon=LEXICON, heuristic=True).ratio
        assert with_it >= without

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=40))
    def test_matches_are_unique_and_bounded_by_the_count(
        self, lemmas: list[str]
    ) -> None:
        result = loanword_ratio(lemmas, lexicon=LEXICON, heuristic=True)
        assert len(set(result.matches)) == len(result.matches)
        assert len(result.matches) <= result.matched

    @settings(max_examples=200, deadline=None)
    @given(st.lists(hungarian_word, min_size=1, max_size=20))
    def test_the_letter_patterns_never_fire_on_native_letters(
        self, lemmas: list[str]
    ) -> None:
        """x, w and q are not in the Hungarian alphabet, so they cannot occur.

        Only the *letter* patterns can be claimed this strongly. Hypothesis
        found the counter-example for the broader claim in one draw: `ch`, `ph`,
        `th` and the initial clusters are all spellable from native letters, so
        a native-alphabet word can and does trip them. See
        `TestHungarianSurnamesTripTheHeuristic`.
        """
        result = loanword_ratio(lemmas, heuristic=True)
        letters = {"x", "w", "q"}
        assert not letters & set(dict(result.pattern_counts))


class TestHungarianSurnamesAreExcepted:
    """Archaic surname orthography is the heuristic's worst false positive.

    `th` spells a plain `t` in Hungarian surnames, and those surnames are not
    rare — Tóth and Németh are among the commonest in the country. They are
    listed in `HEURISTIC_EXCEPTIONS`, with MOKK Webcorpus frequencies, so the
    list is attested rather than remembered.
    """

    SURNAMES = ["Tóth", "Horváth", "Németh", "Kossuth", "Széchenyi", "Wesselényi"]

    @pytest.mark.parametrize("surname", SURNAMES)
    def test_a_common_surname_is_not_flagged(self, surname: str) -> None:
        result = loanword_ratio([surname], heuristic=True, lexicon=set())
        assert result.matched == 0
        assert result.exceptions_applied == 1

    def test_the_exceptions_can_be_disabled(self) -> None:
        """They are a parameter, so the old behaviour is one argument away."""
        result = loanword_ratio(
            ["Tóth"], heuristic=True, lexicon=set(), exceptions=frozenset()
        )
        assert result.matched == 1

    def test_they_do_not_suppress_lexicon_evidence(self) -> None:
        """An exception says a spelling misleads, not that a word is native."""
        result = loanword_ratio(["Tóth"], lexicon={"tóth"}, heuristic=True)
        assert result.matched == 1
        assert result.matched_by_lexicon == 1

    def test_gh_surnames_need_no_exception(self) -> None:
        """`gh` is not a pattern, so Balogh and Végh are already safe."""
        for surname in ("Balogh", "Végh", "Országh", "Virágh"):
            assert loanword_ratio([surname], heuristic=True, lexicon=set()).matched == 0
        assert "balogh" not in HEURISTIC_EXCEPTIONS


class TestMorphemeSeamsDoNotFire:
    """Hungarian manufactures these digraphs across a suffix boundary.

    The potential suffix `-hat`/`-het` and the allative `-hoz`/`-hez`/`-höz`
    put an `h` straight after a stem, so any stem ending in `t`, `p` or `c`
    produces `th`, `ph` or `ch` at the seam. On the MOKK Webcorpus that is
    1,187 word forms and 2.5 million tokens — far more damage than the
    surnames do, and productive, so no list could ever cover it.
    """

    @pytest.mark.parametrize(
        "word,seam",
        [
            ("látható", "lát + ható"),
            ("tekinthető", "tekint + hető"),
            ("letölthető", "letölt + hető"),
            ("fenntartható", "fenntart + ható"),
            ("kapható", "kap + ható"),
            ("állathoz", "állat + hoz"),
            ("kalaphoz", "kalap + hoz"),
            ("táncház", "tánc + ház"),
        ],
    )
    def test_a_seam_does_not_fire(self, word: str, seam: str) -> None:
        result = loanword_ratio([word], heuristic=True, lexicon=set())
        assert result.matched == 0, seam

    @pytest.mark.parametrize(
        "word", ["mintha", "otthon", "itthon", "hátha", "szentháromság", "kétharmad"]
    )
    def test_lexicalised_compounds_are_excepted(self, word: str) -> None:
        """A rule cannot reach these, so they are listed instead."""
        result = loanword_ratio([word], heuristic=True, lexicon=set())
        assert result.matched == 0
        assert result.exceptions_applied == 1

    @pytest.mark.parametrize(
        "word", ["thriller", "theológia", "philosophia", "technológia", "pszichológia"]
    )
    def test_real_foreign_spellings_still_fire(self, word: str) -> None:
        """The lookahead must not cost the words the heuristic exists for."""
        assert loanword_ratio([word], heuristic=True, lexicon=set()).matched == 1


class TestBoundaries:
    """Cases found by mutation testing, each pinning something the docs promise."""

    def test_pattern_counts_are_ordered_by_frequency(self) -> None:
        """Most frequent first, so the dominant rule is visible at a glance."""
        result = loanword_ratio(["taxi", "maximum", "absztrakt"], heuristic=True)
        assert result.pattern_counts == (("x", 2), ("absz", 1))

    def test_pattern_counts_break_ties_alphabetically(self) -> None:
        """Not by insertion order: `w` fires first here but sorts after `absz`."""
        result = loanword_ratio(["watt", "absztrakt"], heuristic=True)
        assert result.pattern_counts == (("absz", 1), ("w", 1))

    def test_exclude_matches_the_lemma_or_the_raw_form(self) -> None:
        """Case folding must not defeat an exclusion written in original case."""
        result = loanword_ratio(["Watt", "taxi"], heuristic=True, exclude={"Watt"})
        assert result.excluded == 1
        assert result.total_lemmas == 1
        assert result.matches == ("taxi",)

    def test_exclusions_accumulate(self) -> None:
        result = loanword_ratio(
            ["watt", "quart", "taxi"], heuristic=True, exclude={"watt", "quart"}
        )
        assert result.excluded == 2
        assert result.total_lemmas == 1

    def test_tagged_exclusions_accumulate(self) -> None:
        result = loanword_ratio(
            ["Tóth", "Németh", "taxi"],
            heuristic=True,
            pos_tags=["PROPN", "PROPN", "NOUN"],
        )
        assert result.excluded == 2

    def test_an_excluded_lemma_does_not_stop_the_scan(self) -> None:
        """The exclusion skips one token, it does not end the loop."""
        result = loanword_ratio(["watt", "taxi"], heuristic=True, exclude={"watt"})
        assert result.matched == 1
        assert result.matches == ("taxi",)

    def test_a_tagged_exclusion_does_not_stop_the_scan(self) -> None:
        result = loanword_ratio(
            ["Tóth", "taxi"], heuristic=True, pos_tags=["PROPN", "NOUN"]
        )
        assert result.matched == 1

    def test_lexicon_matches_accumulate(self) -> None:
        result = loanword_ratio(
            ["komputer", "internet", "kutya"], lexicon={"komputer", "internet"}
        )
        assert result.matched_by_lexicon == 2

    def test_heuristic_matches_accumulate(self) -> None:
        result = loanword_ratio(["taxi", "watt", "kutya"], heuristic=True)
        assert result.matched_by_heuristic == 2

    def test_the_heuristic_flag_is_recorded(self) -> None:
        assert loanword_ratio(["taxi"], heuristic=True).heuristic is True
        assert loanword_ratio(["taxi"], lexicon=set()).heuristic is False


def test_every_default_pattern_is_a_valid_regex() -> None:
    import re

    for name, pattern in FOREIGN_PATTERNS.items():
        assert re.compile(pattern), name
