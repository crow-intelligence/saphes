"""Tests for mean dependency distance and the syntax result record.

The two published anchors — Jing & Liu (2015: 164) and Zhang & Zhou (2023) — are
the regression guard for the arithmetic. Everything else here guards the three
conventions that make an MDD implementation disagree with the literature without
raising: the excluded root, the re-indexing of punctuation, and macro rather
than micro aggregation.
"""

import pytest
from hypothesis import given, settings

from saphes import (
    DepToken,
    dependency_distances,
    mdd_from_counts,
    mean_dependency_distance,
)
from tests.strategies import dependency_tree

# Jing & Liu (2015: 164), "Mr. Nixon was to leave China today ."
# was -> to -> leave -> {China, today}; was -> Nixon -> Mr.
NIXON = [
    DepToken(1, 2, False, "PROPN"),
    DepToken(2, 3, False, "PROPN"),
    DepToken(3, 0, False, "AUX"),
    DepToken(4, 3, False, "PART"),
    DepToken(5, 4, False, "VERB"),
    DepToken(6, 5, False, "PROPN"),
    DepToken(7, 5, False, "NOUN"),
    DepToken(8, 3, True, "PUNCT"),
]

# Zhang & Zhou (2023), "The quick brown fox jumped over the lazy dog."
FOX = [
    DepToken(1, 4, False, "DET"),
    DepToken(2, 4, False, "ADJ"),
    DepToken(3, 4, False, "ADJ"),
    DepToken(4, 5, False, "NOUN"),
    DepToken(5, 0, False, "VERB"),
    DepToken(6, 9, False, "ADP"),
    DepToken(7, 9, False, "DET"),
    DepToken(8, 9, False, "ADJ"),
    DepToken(9, 5, False, "NOUN"),
    DepToken(10, 5, True, "PUNCT"),
]

# A two-token sentence: one arc of length 1, so MDD is exactly 1.0.
SHORT = [DepToken(1, 2, False, "DET"), DepToken(2, 0, False, "NOUN")]


class TestPublishedAnchors:
    """The numbers the papers print, reproduced from the trees behind them."""

    def test_jing_liu_2015_mdd(self) -> None:
        assert round(mean_dependency_distance([NIXON]).mdd, 2) == 1.17

    def test_jing_liu_2015_counts(self) -> None:
        """Seven words give six pairs: the root is excluded from the denominator."""
        result = mean_dependency_distance([NIXON])
        assert result.total_distance == 7
        assert result.pairs == 6
        assert result.tokens == 7

    def test_jing_liu_2015_distances(self) -> None:
        assert dependency_distances(NIXON) == [1, 1, 1, 1, 1, 2]

    def test_zhang_zhou_2023_mdd(self) -> None:
        assert mean_dependency_distance([FOX]).mdd == 2.125

    def test_zhang_zhou_2023_counts(self) -> None:
        result = mean_dependency_distance([FOX])
        assert result.total_distance == 17
        assert result.pairs == 8

    def test_including_the_root_would_give_the_wrong_answer(self) -> None:
        """The trap this test exists for: 7/7 is not the published 7/6."""
        result = mean_dependency_distance([NIXON])
        assert result.mdd != pytest.approx(7 / 7)
        assert result.mdd == pytest.approx(7 / 6)


class TestKernel:
    """mdd_from_counts validates rather than returning a plausible number."""

    def test_worked_value(self) -> None:
        assert mdd_from_counts(total_distance=7, pairs=6) == pytest.approx(7 / 6)

    def test_zero_pairs_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one dependency pair"):
            mdd_from_counts(total_distance=0, pairs=0)

    def test_negative_total_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            mdd_from_counts(total_distance=-1, pairs=2)

    def test_transposed_arguments_raise(self) -> None:
        """Every distance is >= 1, so total < pairs means the args were swapped."""
        with pytest.raises(ValueError, match="probably transposed"):
            mdd_from_counts(total_distance=6, pairs=7)

    def test_keyword_only(self) -> None:
        with pytest.raises(TypeError):
            mdd_from_counts(7, 6)  # type: ignore[misc]


class TestPunctuationPolicy:
    """Method B re-indexes; Method A does not. A medial comma is the difference."""

    # "it , stops" — the comma sits between the dependent and its governor.
    MEDIAL = [
        DepToken(1, 3, False, "PRON"),
        DepToken(2, 1, True, "PUNCT"),
        DepToken(3, 0, False, "VERB"),
    ]

    def test_collapse_reindexes(self) -> None:
        assert dependency_distances(self.MEDIAL, punctuation="collapse") == [1]

    def test_ignore_keeps_the_index_space(self) -> None:
        assert dependency_distances(self.MEDIAL, punctuation="ignore") == [2]

    def test_keep_counts_punctuation_too(self) -> None:
        assert sorted(dependency_distances(self.MEDIAL, punctuation="keep")) == [1, 2]

    def test_a_trailing_period_does_not_discriminate(self) -> None:
        """Why the Nixon anchor alone cannot catch a Method A/B mix-up."""
        assert dependency_distances(NIXON, punctuation="collapse") == (
            dependency_distances(NIXON, punctuation="ignore")
        )

    def test_ignore_is_never_smaller_than_collapse(self) -> None:
        collapse = mean_dependency_distance([self.MEDIAL], punctuation="collapse")
        ignore = mean_dependency_distance([self.MEDIAL], punctuation="ignore")
        assert ignore.mdd > collapse.mdd

    def test_punctuation_dropped_is_recorded(self) -> None:
        assert mean_dependency_distance([NIXON]).punctuation_dropped == 1

    def test_an_arc_into_punctuation_is_orphaned_and_counted(self) -> None:
        """Rare under UD, where punctuation is a leaf, but it must not vanish."""
        parse = [
            DepToken(1, 3, False, "X"),
            DepToken(2, 3, True, "PUNCT"),
            DepToken(3, 0, False, "VERB"),
            DepToken(4, 2, False, "X"),
        ]
        result = mean_dependency_distance([parse])
        assert result.orphaned_arcs == 1
        assert result.pairs == 1

    def test_unknown_policy_raises(self) -> None:
        with pytest.raises(ValueError, match="punctuation must be"):
            mean_dependency_distance([NIXON], punctuation="drop")  # type: ignore[arg-type]


class TestAggregation:
    """Macro and micro are different numbers, not different roundings."""

    def test_macro_is_the_default(self) -> None:
        assert mean_dependency_distance([SHORT, FOX]).aggregation == "macro"

    def test_macro_averages_sentence_means(self) -> None:
        assert mean_dependency_distance([SHORT, FOX]).mdd == pytest.approx(
            (1.0 + 2.125) / 2
        )

    def test_micro_pools_every_pair(self) -> None:
        result = mean_dependency_distance([SHORT, FOX], aggregation="micro")
        assert result.mdd == pytest.approx(18 / 9)

    def test_they_disagree_on_uneven_sentences(self) -> None:
        macro = mean_dependency_distance([SHORT, FOX]).mdd
        micro = mean_dependency_distance([SHORT, FOX], aggregation="micro").mdd
        assert macro != pytest.approx(micro)

    def test_they_agree_on_one_sentence(self) -> None:
        macro = mean_dependency_distance([FOX]).mdd
        micro = mean_dependency_distance([FOX], aggregation="micro").mdd
        assert macro == pytest.approx(micro)

    def test_unknown_aggregation_raises(self) -> None:
        with pytest.raises(ValueError, match="aggregation must be"):
            mean_dependency_distance([FOX], aggregation="mean")  # type: ignore[arg-type]


class TestMalformedInput:
    """Every structural violation raises; none returns a plausible number."""

    def test_a_flat_token_list_is_refused(self) -> None:
        """Read as sentences it would be silently empty of pairs."""
        with pytest.raises(TypeError, match="not tokens"):
            mean_dependency_distance(NIXON)  # type: ignore[arg-type]

    def test_a_flat_list_of_bare_tuples_is_refused(self) -> None:
        with pytest.raises(TypeError, match="not tokens"):
            mean_dependency_distance([(1, 2, False, "DET"), (2, 0, False, "N")])  # type: ignore[arg-type]

    def test_no_sentences_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one sentence"):
            mean_dependency_distance([])

    def test_an_empty_sentence_raises(self) -> None:
        with pytest.raises(ValueError, match="is empty"):
            mean_dependency_distance([[]])

    def test_gapped_indices_raise(self) -> None:
        """Punctuation removed without re-indexing: the silent-failure case."""
        gapped = [DepToken(1, 3, False, "PRON"), DepToken(3, 0, False, "VERB")]
        with pytest.raises(ValueError, match="must run 1..n"):
            mean_dependency_distance([gapped])

    def test_head_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="out of range"):
            mean_dependency_distance([[DepToken(1, 9, False, "X")]])

    def test_self_governing_token_raises(self) -> None:
        with pytest.raises(ValueError, match="own governor"):
            mean_dependency_distance([[DepToken(1, 1, False, "X")]])

    def test_a_rootless_sentence_raises(self) -> None:
        cycle = [DepToken(1, 2, False, "X"), DepToken(2, 1, False, "X")]
        with pytest.raises(ValueError, match="no root"):
            mean_dependency_distance([cycle])

    def test_a_non_token_raises(self) -> None:
        with pytest.raises(TypeError, match="4-tuple"):
            mean_dependency_distance([["not a token"]])

    def test_a_single_word_sentence_alone_raises(self) -> None:
        with pytest.raises(ValueError, match="no sentence yielded"):
            mean_dependency_distance([[DepToken(1, 0, False, "INTJ")]])

    def test_negative_min_sentence_length_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            mean_dependency_distance([FOX], min_sentence_length=-1)


class TestFilters:
    """The literature's sentence filters are available, off, and recorded."""

    def test_no_filter_by_default(self) -> None:
        assert mean_dependency_distance([FOX]).min_sentence_length == 0

    def test_min_sentence_length_skips_and_counts(self) -> None:
        result = mean_dependency_distance([SHORT, FOX], min_sentence_length=3)
        assert result.sentences == 1
        assert result.skipped_sentences == 1
        assert result.mdd == pytest.approx(2.125)

    def test_a_one_word_sentence_is_skipped_not_fatal(self) -> None:
        result = mean_dependency_distance([[DepToken(1, 0, False, "INTJ")], FOX])
        assert result.skipped_sentences == 1
        assert result.sentences == 1

    def test_require_single_root_skips_fragmented_parses(self) -> None:
        fragment = [
            DepToken(1, 0, False, "VERB"),
            DepToken(2, 1, False, "X"),
            DepToken(3, 0, False, "VERB"),
        ]
        kept = mean_dependency_distance([fragment, FOX])
        assert kept.sentences == 2
        filtered = mean_dependency_distance([fragment, FOX], require_single_root=True)
        assert filtered.sentences == 1
        assert filtered.skipped_sentences == 1

    def test_roots_are_counted(self) -> None:
        assert mean_dependency_distance([NIXON]).roots == 1


class TestResultRecord:
    """The result carries everything needed to recompute and interpret it."""

    def test_repr_shows_the_counts(self) -> None:
        text = repr(mean_dependency_distance([NIXON]))
        assert "mdd=1.1667" in text
        assert "pairs=6" in text
        assert "punctuation='collapse'" in text

    def test_repr_omits_the_version(self) -> None:
        import saphes

        assert saphes.__version__ not in repr(mean_dependency_distance([NIXON]))

    def test_records_the_saphes_version(self) -> None:
        import saphes

        assert mean_dependency_distance([NIXON]).saphes_version == saphes.__version__

    def test_to_dict(self) -> None:
        record = mean_dependency_distance([NIXON]).to_dict()
        assert record["pairs"] == 6
        assert record["total_distance"] == 7
        assert record["aggregation"] == "macro"

    def test_micro_score_is_recomputable_from_the_record(self) -> None:
        """The point of carrying the counts: the number can be checked."""
        result = mean_dependency_distance([SHORT, FOX], aggregation="micro")
        record = result.to_dict()
        assert record["total_distance"] / record["pairs"] == pytest.approx(result.mdd)

    def test_avg_sentence_length(self) -> None:
        assert mean_dependency_distance([NIXON]).avg_sentence_length == 7.0

    def test_parse_source_is_provenance_only(self) -> None:
        plain = mean_dependency_distance([NIXON])
        labelled = mean_dependency_distance([NIXON], parse_source="conllu")
        assert labelled.parse_source == "conllu"
        assert labelled.mdd == plain.mdd


class TestSyntaxProperties:
    """Properties that must hold for every well-formed parse."""

    @settings(max_examples=200, deadline=None)
    @given(dependency_tree())
    def test_distances_are_at_least_one(self, parse: list[DepToken]) -> None:
        assert all(distance >= 1 for distance in dependency_distances(parse))

    @settings(max_examples=200, deadline=None)
    @given(dependency_tree())
    def test_mdd_is_at_least_one_when_defined(self, parse: list[DepToken]) -> None:
        try:
            result = mean_dependency_distance([parse])
        except ValueError:
            return  # no countable pair; the contract says this raises
        assert result.mdd >= 1.0

    @settings(max_examples=200, deadline=None)
    @given(dependency_tree())
    def test_collapse_never_exceeds_ignore(self, parse: list[DepToken]) -> None:
        """Removing tokens from the index space can only shorten arcs."""
        collapse = dependency_distances(parse, punctuation="collapse")
        ignore = dependency_distances(parse, punctuation="ignore")
        if len(collapse) == len(ignore):
            assert sum(collapse) <= sum(ignore)

    @settings(max_examples=200, deadline=None)
    @given(dependency_tree())
    def test_pairs_never_exceed_content_tokens(self, parse: list[DepToken]) -> None:
        """One root has no governor, so pairs < non-punctuation tokens."""
        try:
            result = mean_dependency_distance([parse])
        except ValueError:
            return
        assert result.pairs < result.tokens or result.orphaned_arcs > 0

    @settings(max_examples=200, deadline=None)
    @given(dependency_tree())
    def test_bare_tuples_and_deptokens_agree(self, parse: list[DepToken]) -> None:
        """The adapter contract: a plain 4-tuple is as good as a DepToken."""
        bare = [tuple(token) for token in parse]
        assert dependency_distances(bare) == dependency_distances(parse)
