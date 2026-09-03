"""Tests for TTR, MATTR, and the diversity result record."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saphes import lexical_diversity, mattr, ttr_from_counts
from tests.strategies import ascii_word, word_list


class TestTtr:
    """Type-token ratio arithmetic."""

    def test_basic(self) -> None:
        assert lexical_diversity(["a", "b", "a"], unit="lemma").ttr == pytest.approx(
            2 / 3
        )

    def test_all_unique_is_one(self) -> None:
        assert lexical_diversity(["a", "b", "c"], unit="lemma").ttr == 1.0

    def test_single_repeated_token_is_one_over_n(self) -> None:
        for n in (1, 2, 5, 50):
            assert lexical_diversity(["a"] * n, unit="lemma").ttr == pytest.approx(
                1 / n
            )

    def test_kernel(self) -> None:
        assert ttr_from_counts(types=2, tokens=4) == 0.5


class TestUnit:
    """The token unit is required, validated, and recorded."""

    def test_unit_is_required(self) -> None:
        with pytest.raises(TypeError, match="unit"):
            lexical_diversity(["a", "b"])  # type: ignore[call-arg]

    def test_unit_is_validated(self) -> None:
        with pytest.raises(ValueError, match="must be 'lemma', 'surface' or 'stem'"):
            lexical_diversity(["a", "b"], unit="token")  # type: ignore[arg-type]

    def test_unit_is_recorded(self) -> None:
        assert lexical_diversity(["a"], unit="lemma").unit == "lemma"
        assert lexical_diversity(["a"], unit="surface").unit == "surface"


class TestRawString:
    """A raw string can only ever yield surface forms, so it is refused otherwise."""

    def test_refused_with_lemma_unit(self) -> None:
        with pytest.raises(TypeError, match="raw string"):
            lexical_diversity("ház házak házban", unit="lemma")

    def test_error_explains_why(self) -> None:
        with pytest.raises(TypeError, match="upstream analysis"):
            lexical_diversity("ház házak", unit="lemma")

    def test_accepted_with_surface_unit(self) -> None:
        result = lexical_diversity("ház házak házban", unit="surface")
        assert result.tokens == 3
        assert result.token_source == "segmented"

    def test_token_list_is_recorded_as_provided(self) -> None:
        assert lexical_diversity(["a"], unit="lemma").token_source == "provided"


class TestCaseFolding:
    """Case folding is opt-in, and never applied behind the caller's back."""

    def test_default_is_case_sensitive(self) -> None:
        result = lexical_diversity(["Ház", "ház"], unit="lemma")
        assert result.types == 2
        assert result.case_folded is False

    def test_case_fold_merges_types(self) -> None:
        result = lexical_diversity(["Ház", "ház"], unit="lemma", case_fold=True)
        assert result.types == 1
        assert result.case_folded is True

    def test_case_fold_merges_greek_final_sigma(self) -> None:
        """casefold() merges ς with σ; lower() does not."""
        assert lexical_diversity(["ὅς", "ὅσ"], unit="lemma").types == 2
        assert lexical_diversity(["ὅς", "ὅσ"], unit="lemma", case_fold=True).types == 1


class TestMattr:
    """The moving-average TTR, absorbed verbatim from its two duplicate homes."""

    def test_every_window_all_distinct(self) -> None:
        assert mattr(["a", "b", "a", "b"], window=2) == 1.0

    def test_every_window_one_type(self) -> None:
        assert mattr(["a", "a", "a"], window=2) == 0.5

    def test_shorter_than_window_degrades_to_ttr(self) -> None:
        assert mattr(["a", "b", "c"], window=10) == 1.0

    def test_empty_returns_zero_not_an_error(self) -> None:
        """The historical contract; lexical_diversity raises instead."""
        assert mattr([], window=5) == 0.0

    def test_exposed_through_lexical_diversity(self) -> None:
        result = lexical_diversity(["a", "b", "a", "b"], unit="lemma", window=2)
        assert result.mattr == 1.0
        assert result.window == 2

    def test_absent_without_a_window(self) -> None:
        result = lexical_diversity(["a", "b"], unit="lemma")
        assert result.mattr is None
        assert result.window is None

    def test_window_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="window must be positive"):
            lexical_diversity(["a"], unit="lemma", window=0)

    def test_default_window_is_100(self) -> None:
        """Pins the default, which downstream call sites rely on."""
        tokens = ["a", "b"] * 60 + ["c"] * 60
        assert mattr(tokens) == mattr(tokens, window=100)
        assert mattr(tokens) != mattr(tokens, window=101)

    def test_repeats_inside_the_priming_window(self) -> None:
        """The sliding counter must survive a token repeating in the first window.

        Windows of ["a","a","b","c"] at width 2 hold 1, 2 and 2 distinct types,
        so the mean is 5/6. Getting the priming loop's increment wrong shows up
        only here — when a token repeats before the window starts sliding.
        """
        assert mattr(["a", "a", "b", "c"], window=2) == pytest.approx(5 / 6)


class TestDegenerateInput:
    """Empty input raises a clear error rather than dividing by zero."""

    def test_empty_sequence(self) -> None:
        with pytest.raises(ValueError, match="at least one token"):
            lexical_diversity([], unit="lemma")

    def test_empty_string_with_surface_unit(self) -> None:
        with pytest.raises(ValueError, match="at least one token"):
            lexical_diversity("", unit="surface")

    def test_kernel_rejects_zero_tokens(self) -> None:
        with pytest.raises(ValueError, match="at least one token"):
            ttr_from_counts(types=0, tokens=0)

    def test_kernel_rejects_more_types_than_tokens(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            ttr_from_counts(types=5, tokens=3)

    def test_kernel_rejects_zero_types(self) -> None:
        with pytest.raises(ValueError, match="at least one type"):
            ttr_from_counts(types=0, tokens=3)


class TestResultRecord:
    """The result carries everything needed to interpret it."""

    def test_repr_carries_the_length_warning(self) -> None:
        text = repr(lexical_diversity(["a", "b"], unit="lemma"))
        assert "TTR falls as text grows" in text
        assert "window=" in text

    def test_repr_drops_the_warning_once_mattr_is_present(self) -> None:
        """MATTR is the length-robust number, so the caveat no longer applies."""
        text = repr(lexical_diversity(["a", "b"], unit="lemma", window=2))
        assert "TTR falls as text grows" not in text
        assert "mattr=" in text

    def test_repr_omits_the_version(self) -> None:
        import saphes

        assert saphes.__version__ not in repr(
            lexical_diversity(["a", "b"], unit="lemma")
        )

    def test_pos_filter_is_provenance_only(self) -> None:
        result = lexical_diversity(["a"], unit="lemma", pos_filter="content words")
        assert result.pos_filter == "content words"
        assert result.tokens == 1

    def test_to_dict(self) -> None:
        record = lexical_diversity(["a", "b"], unit="lemma", window=2).to_dict()
        assert record["unit"] == "lemma"
        assert record["window"] == 2

    def test_records_the_saphes_version(self) -> None:
        import saphes

        result = lexical_diversity(["a", "b"], unit="lemma")
        assert result.saphes_version == saphes.__version__


class TestDiversityProperties:
    """Property-based contracts over random token lists."""

    @settings(max_examples=200, deadline=None)
    @given(word_list)
    def test_ttr_lies_in_the_unit_interval(self, tokens: list[str]) -> None:
        ttr = lexical_diversity(tokens, unit="lemma").ttr
        assert 0.0 < ttr <= 1.0

    @settings(max_examples=200, deadline=None)
    @given(st.lists(ascii_word, min_size=1, max_size=60, unique=True))
    def test_all_unique_gives_exactly_one(self, tokens: list[str]) -> None:
        assert lexical_diversity(tokens, unit="lemma").ttr == 1.0

    @settings(max_examples=200, deadline=None)
    @given(ascii_word, st.integers(min_value=1, max_value=200))
    def test_one_repeated_token_gives_one_over_n(self, token: str, n: int) -> None:
        assert lexical_diversity([token] * n, unit="lemma").ttr == pytest.approx(1 / n)

    @settings(max_examples=200, deadline=None)
    @given(word_list, st.integers(min_value=1, max_value=50))
    def test_mattr_lies_in_the_unit_interval(
        self, tokens: list[str], window: int
    ) -> None:
        assert 0.0 <= mattr(tokens, window=window) <= 1.0

    @settings(max_examples=200, deadline=None)
    @given(word_list)
    def test_mattr_at_full_length_equals_ttr(self, tokens: list[str]) -> None:
        result = lexical_diversity(tokens, unit="lemma", window=len(tokens))
        assert result.mattr == pytest.approx(result.ttr)

    @settings(max_examples=200, deadline=None)
    @given(word_list)
    def test_case_folding_never_increases_types(self, tokens: list[str]) -> None:
        plain = lexical_diversity(tokens, unit="lemma").types
        folded = lexical_diversity(tokens, unit="lemma", case_fold=True).types
        assert folded <= plain
