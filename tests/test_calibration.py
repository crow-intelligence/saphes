"""Tests for the threshold calibration machinery."""

import pytest
from hypothesis import given, settings

from saphes.calibration import (
    HU_DIGRAPHS,
    collapse_digraphs,
    hungarian_letter_count,
    length_curve,
    match_threshold,
    recommended_threshold,
)
from tests.strategies import frequency_counts

# Three types, twenty running tokens, lengths 1, 4 and 9.
DEMO = {"a": 10, "abcd": 5, "abcdefghi": 5}


class TestLengthCurve:
    """Token-weighted cumulative shares, computed by hand."""

    def test_totals(self) -> None:
        curve = length_curve(DEMO, label="demo")
        assert (curve.tokens, curve.types) == (20, 3)

    def test_mean_length(self) -> None:
        # (1*10 + 4*5 + 9*5) / 20
        assert length_curve(DEMO, label="demo").mean_length == 3.75

    def test_shares(self) -> None:
        curve = length_curve(DEMO, label="demo")
        assert curve.share_above(0) == 1.0
        assert curve.share_above(1) == 0.5
        assert curve.share_above(4) == 0.25
        assert curve.share_above(9) == 0.0

    def test_label_and_parameters_recorded(self) -> None:
        curve = length_curve(DEMO, label="demo", min_frequency=2)
        assert curve.label == "demo"
        assert curve.min_frequency == 2
        assert curve.length_policy == "nfc"

    def test_min_frequency_drops_rare_types(self) -> None:
        counts = {"a": 100, "abcdefghij": 1}
        assert length_curve(counts, label="d", min_frequency=5).tokens == 100
        assert length_curve(counts, label="d", min_frequency=1).tokens == 101

    def test_share_above_outside_the_curve_raises(self) -> None:
        curve = length_curve(DEMO, label="demo", max_threshold=5)
        with pytest.raises(KeyError, match="no share at threshold"):
            curve.share_above(9)

    def test_custom_length_policy(self) -> None:
        """The digraph-aware count shortens Hungarian words."""
        counts = {"ország": 10}
        plain = length_curve(counts, label="chars")
        letters = length_curve(
            counts, label="letters", length_policy=hungarian_letter_count
        )
        assert plain.mean_length == 6.0
        assert letters.mean_length == 5.0
        assert letters.length_policy.startswith("custom:")


class TestTokenWeighting:
    """The study's most likely silent failure, guarded by the signature."""

    def test_type_weighting_gives_a_different_answer(self) -> None:
        """Discarding frequencies inflates the curve — plausibly, and wrongly."""
        weighted = length_curve(DEMO, label="right")
        flat = length_curve(dict.fromkeys(DEMO, 1), label="wrong", min_frequency=1)
        assert weighted.share_above(1) == 0.5
        assert flat.share_above(1) == pytest.approx(2 / 3)
        assert flat.mean_length > weighted.mean_length

    def test_frequencies_actually_weight_the_result(self) -> None:
        """Doubling one word's frequency moves the curve toward its length."""
        base = length_curve({"a": 10, "abcdefghi": 10}, label="base")
        skewed = length_curve({"a": 10, "abcdefghi": 90}, label="skewed")
        assert skewed.share_above(1) > base.share_above(1)


class TestDegenerateInput:
    """Bad input raises rather than producing an empty or misleading curve."""

    def test_everything_filtered_out(self) -> None:
        with pytest.raises(ValueError, match="no tokens survived"):
            length_curve({"a": 1}, label="empty", min_frequency=5)

    def test_negative_count(self) -> None:
        with pytest.raises(ValueError, match="is negative"):
            length_curve({"a": -1}, label="bad", min_frequency=0)

    def test_negative_max_threshold(self) -> None:
        with pytest.raises(ValueError, match="max_threshold cannot be negative"):
            length_curve(DEMO, label="bad", max_threshold=-1)

    def test_negative_min_frequency(self) -> None:
        with pytest.raises(ValueError, match="min_frequency cannot be negative"):
            length_curve(DEMO, label="bad", min_frequency=-1)


class TestMatchThreshold:
    """Equipercentile matching."""

    def _spread(self, n: int, label: str):  # noqa: ANN202 - a LengthCurve
        """A curve with one word of each length 1..n, so shares are distinct."""
        return length_curve({"a" * i: 10 for i in range(1, n + 1)}, label=label)

    def test_longer_language_needs_a_higher_threshold(self) -> None:
        target = self._spread(10, "long")
        reference = self._spread(5, "short")
        match = match_threshold(target, reference, reference_threshold=3)
        assert match.reference_share == pytest.approx(0.4)
        assert match.threshold == 6
        assert match.residual == pytest.approx(0.0)

    def test_keeping_the_literal_threshold_would_mean_something_else(self) -> None:
        target = self._spread(10, "long")
        assert target.share_above(3) == pytest.approx(0.7)

    def test_bracket_spans_the_reference_share(self) -> None:
        target = self._spread(10, "target")
        reference = length_curve({"ab": 11, "abcd": 9}, label="ref")
        match = match_threshold(target, reference, reference_threshold=3)
        assert match.reference_share == pytest.approx(0.45)
        assert match.bracket == (5, 6)

    def test_contested_match_is_flagged(self) -> None:
        target = self._spread(10, "target")
        reference = length_curve({"ab": 11, "abcd": 9}, label="ref")
        assert match_threshold(target, reference, reference_threshold=3).is_boundary

    def test_clear_match_is_not_flagged(self) -> None:
        match = match_threshold(
            self._spread(10, "target"), self._spread(5, "ref"), reference_threshold=3
        )
        assert not match.is_boundary

    def test_carries_the_whole_curve(self) -> None:
        """The deliverable is the table, not just the winner."""
        target = self._spread(10, "target")
        match = match_threshold(target, self._spread(5, "ref"), reference_threshold=3)
        assert match.table == target.shares

    def test_labels_are_recorded(self) -> None:
        match = match_threshold(
            self._spread(10, "hu"), self._spread(5, "sv"), reference_threshold=3
        )
        assert (match.target_label, match.reference_label) == ("hu", "sv")

    def test_unknown_reference_threshold_raises(self) -> None:
        target = self._spread(10, "target")
        reference = length_curve({"ab": 5}, label="ref", max_threshold=3)
        with pytest.raises(KeyError, match="no share at threshold"):
            match_threshold(target, reference, reference_threshold=9)


class TestDigraphs:
    """Hungarian letters are not Hungarian characters."""

    def test_single_digraph(self) -> None:
        assert hungarian_letter_count("ország") == 5

    def test_longest_first(self) -> None:
        """The dzs trigraph is one letter, not dz plus s."""
        assert hungarian_letter_count("bridzs") == 4

    def test_no_digraph_is_unchanged(self) -> None:
        assert collapse_digraphs("ember") == "ember"

    def test_case_folded(self) -> None:
        assert hungarian_letter_count("Ország") == hungarian_letter_count("ország")

    def test_known_failure_at_a_morpheme_boundary(self) -> None:
        """község is köz + ség, so its zs is not the digraph.

        Pinned deliberately. This is the reason character counting stays the
        default and this is only ever a sensitivity check.
        """
        assert hungarian_letter_count("község") == 5  # the true count is 6

    def test_never_lengthens(self) -> None:
        for word in ("ország", "község", "bridzs", "ember", ""):
            assert len(collapse_digraphs(word)) <= len(word)

    def test_digraph_table_is_longest_first(self) -> None:
        lengths = [len(d) for d in HU_DIGRAPHS]
        assert lengths == sorted(lengths, reverse=True)


class TestRecommendedThreshold:
    """The shipped calibration, and its provenance."""

    def test_hungarian(self) -> None:
        assert recommended_threshold("hu").threshold == 8

    def test_usable_as_an_int(self) -> None:
        assert int(recommended_threshold("hu")) == 8

    def test_matches_the_reference_share(self) -> None:
        rec = recommended_threshold("hu")
        assert rec.matched_share == pytest.approx(rec.reference_share, abs=0.03)
        assert rec.residual == pytest.approx(
            abs(rec.matched_share - rec.reference_share), abs=1e-6
        )

    def test_every_source_agrees(self) -> None:
        """Unanimity across six independent curves is the actual evidence."""
        rec = recommended_threshold("hu")
        assert len(rec.agreement) >= 5
        assert {threshold for _, threshold in rec.agreement} == {rec.threshold}

    def test_not_contested(self) -> None:
        assert recommended_threshold("hu").is_boundary is False
        assert recommended_threshold("hu").runner_up != 8

    def test_carries_its_caveats(self) -> None:
        """A calibrated threshold is a default, not a truth — say so."""
        rec = recommended_threshold("hu")
        assert rec.caveats
        assert any("not a truth" in c for c in rec.caveats)
        assert any("Register" in c for c in rec.caveats)

    def test_names_its_sources(self) -> None:
        rec = recommended_threshold("hu")
        assert any("mokk" in s for s in rec.sources)
        assert any("leipzig" in s for s in rec.sources)
        assert "leipzig" in rec.reference_id

    def test_uncalibrated_language_raises(self) -> None:
        with pytest.raises(KeyError, match="no calibration for 'grc'"):
            recommended_threshold("grc")

    def test_error_lists_what_is_available(self) -> None:
        with pytest.raises(KeyError, match="calibrated languages: hu"):
            recommended_threshold("de")

    def test_to_dict(self) -> None:
        assert recommended_threshold("hu").to_dict()["threshold"] == 8

    def test_repr_omits_the_version(self) -> None:
        import saphes

        assert saphes.__version__ not in repr(recommended_threshold("hu"))


class TestCalibrationProperties:
    """Property-based contracts over arbitrary frequency lists."""

    @settings(max_examples=200, deadline=None)
    @given(frequency_counts())
    def test_shares_are_non_increasing(self, counts: dict[str, int]) -> None:
        curve = length_curve(counts, label="prop", min_frequency=1)
        shares = [share for _, share in curve.shares]
        assert shares == sorted(shares, reverse=True)

    @settings(max_examples=200, deadline=None)
    @given(frequency_counts())
    def test_shares_lie_in_the_unit_interval(self, counts: dict[str, int]) -> None:
        curve = length_curve(counts, label="prop", min_frequency=1)
        assert all(0.0 <= share <= 1.0 for _, share in curve.shares)

    @settings(max_examples=200, deadline=None)
    @given(frequency_counts())
    def test_share_above_zero_is_one(self, counts: dict[str, int]) -> None:
        """Every surviving word has at least one letter."""
        curve = length_curve(counts, label="prop", min_frequency=1)
        assert curve.share_above(0) == pytest.approx(1.0)

    @settings(max_examples=200, deadline=None)
    @given(frequency_counts())
    def test_mean_length_is_within_the_observed_range(
        self, counts: dict[str, int]
    ) -> None:
        curve = length_curve(counts, label="prop", min_frequency=1)
        lengths = [len(w) for w in counts]
        assert min(lengths) <= curve.mean_length <= max(lengths)

    @settings(max_examples=200, deadline=None)
    @given(frequency_counts())
    def test_tokens_equal_the_sum_of_kept_frequencies(
        self, counts: dict[str, int]
    ) -> None:
        curve = length_curve(counts, label="prop", min_frequency=1)
        assert curve.tokens == sum(counts.values())

    @settings(max_examples=100, deadline=None)
    @given(frequency_counts())
    def test_matching_a_curve_against_itself_returns_the_same_threshold(
        self, counts: dict[str, int]
    ) -> None:
        """The identity case: no rescaling needed when the languages agree."""
        curve = length_curve(counts, label="self", min_frequency=1)
        match = match_threshold(curve, curve, reference_threshold=6)
        assert match.residual == pytest.approx(0.0)
        assert curve.share_above(match.threshold) == pytest.approx(curve.share_above(6))
