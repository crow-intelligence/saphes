"""Tests for LIX, RIX, and word-length policy."""

import unicodedata

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from saphes import interpret_lix, lix, lix_from_counts, rix, word_length
from tests.strategies import positive_threshold, word_list

CANONICAL = "The cat sat on it. Complicated sentences generally frighten us."


class TestHandComputed:
    """The worked example from the module docstring, verified by hand."""

    def test_counts(self) -> None:
        result = lix(CANONICAL)
        assert (result.words, result.sentences, result.long_words) == (10, 2, 4)

    def test_score(self) -> None:
        # 10/2 + (4 * 100)/10 = 5.0 + 40.0
        assert lix(CANONICAL).score == 45.0

    def test_kernel_agrees(self) -> None:
        assert lix_from_counts(words=10, sentences=2, long_words=4) == 45.0


class TestOffByOne:
    """A long word is longer than the threshold, so 6 means seven letters or more."""

    def test_six_letter_word_is_not_long(self) -> None:
        assert lix(["houses"], sentences=1).long_words == 0

    def test_seven_letter_word_is_long(self) -> None:
        assert lix(["housing"], sentences=1).long_words == 1

    def test_threshold_is_the_boundary(self) -> None:
        assert lix(["abcdefg"], sentences=1, long_word_threshold=7).long_words == 0
        assert lix(["abcdefg"], sentences=1, long_word_threshold=6).long_words == 1


class TestThresholdBehaviour:
    """Sweeping the threshold moves the score in the expected direction."""

    def test_threshold_zero_makes_every_word_long(self) -> None:
        result = lix(CANONICAL, long_word_threshold=0)
        assert result.long_words == result.words
        assert result.score - result.avg_sentence_length == pytest.approx(100.0)

    def test_huge_threshold_makes_no_word_long(self) -> None:
        result = lix(CANONICAL, long_word_threshold=1000)
        assert result.long_words == 0
        assert result.score == pytest.approx(result.avg_sentence_length)

    def test_sweep_is_monotone_non_increasing(self) -> None:
        scores = [lix(CANONICAL, long_word_threshold=t).score for t in range(0, 15)]
        assert scores == sorted(scores, reverse=True)

    def test_hungarian_saturates_at_the_swedish_default(self) -> None:
        """The package's reason for existing, as a test."""
        hu = "A gyermekeknek megmutatták a településeken található nevezetességeket."
        saturated = lix(hu, sentences=1).long_word_share
        discriminating = lix(hu, sentences=1, long_word_threshold=9).long_word_share
        assert saturated > 0.7
        assert discriminating < saturated


class TestBands:
    """Bands are Björnsson's, and only mean anything at threshold 6."""

    def test_band_at_calibrated_threshold(self) -> None:
        assert lix(CANONICAL).band == "standard"

    def test_band_is_none_off_the_calibrated_threshold(self) -> None:
        assert lix(CANONICAL, long_word_threshold=8).band is None
        assert lix(CANONICAL, long_word_threshold=5).band is None

    def test_interpret_lix_stays_callable(self) -> None:
        assert interpret_lix(lix(CANONICAL, long_word_threshold=8).score) is not None

    def test_bands_cover_the_range(self) -> None:
        for score in (0.0, 29.9, 30.0, 45.0, 59.9, 60.0, 200.0):
            assert interpret_lix(score) is not None

    def test_band_bounds_are_exclusive_upper(self) -> None:
        """A score exactly on a bound belongs to the band above it."""
        assert interpret_lix(29.9) == "very easy"
        assert interpret_lix(30.0) == "easy"
        assert interpret_lix(39.9) == "easy"
        assert interpret_lix(40.0) == "standard"
        assert interpret_lix(59.9) == "difficult"
        assert interpret_lix(60.0) == "very difficult"


class TestSentenceSources:
    """B has three sources, and the result records which one was used."""

    def test_segmented_from_raw_text(self) -> None:
        result = lix(CANONICAL)
        assert result.sentence_source == "segmented"
        assert result.token_source == "segmented"
        assert result.sentencer is not None

    def test_presegmented(self) -> None:
        result = lix(CANONICAL, sentences=["The cat sat on it.", "And so on."])
        assert result.sentence_source == "presegmented"
        assert result.sentences == 2
        assert result.sentencer is None

    def test_explicit_count(self) -> None:
        result = lix(CANONICAL.split(), sentences=2)
        assert result.sentence_source == "explicit"
        assert result.token_source == "provided"
        assert result.sentences == 2

    def test_custom_sentencer_is_recorded(self) -> None:
        def by_linebreak(text: str) -> list[str]:
            return [line for line in text.splitlines() if line.strip()]

        result = lix("one two three\nfour five six", sentencer=by_linebreak)
        assert result.sentences == 2
        assert "by_linebreak" in (result.sentencer or "")

    def test_tokens_without_sentences_is_an_error(self) -> None:
        with pytest.raises(TypeError, match="cannot be recovered"):
            lix(["some", "tokens"])

    def test_bool_sentences_rejected(self) -> None:
        """`sentences=True` would silently become B=1, since bool subclasses int."""
        with pytest.raises(TypeError, match="count or a sequence"):
            lix(CANONICAL, sentences=True)

    def test_bare_string_sentences_rejected(self) -> None:
        with pytest.raises(TypeError, match="ambiguous"):
            lix(CANONICAL, sentences="One sentence.")


class TestLengthPolicy:
    """Word length is normalised, and the policy is recorded."""

    def test_nfc_is_the_default(self) -> None:
        assert lix(CANONICAL).length_policy == "nfc"

    def test_decomposed_input_does_not_inflate_length(self) -> None:
        decomposed = unicodedata.normalize("NFD", "ἐϋκνήμιδες")
        assert word_length(decomposed) == 10
        assert word_length(decomposed, policy="codepoints") == 13

    def test_graphemes_drops_combining_marks(self) -> None:
        decomposed = unicodedata.normalize("NFD", "házakban")
        assert word_length(decomposed, policy="graphemes") == 8

    def test_graphemes_differs_from_nfc_where_nfc_cannot_compose(self) -> None:
        """Alpha with macron and smooth breathing: NFC leaves a residual mark.

        This is the case the two policies actually disagree on, and the reason
        "graphemes" exists at all — metrical editions and lexicon forms carry
        marks NFC has no precomposed character for.
        """
        macron_breathing = "ᾱ̓"
        assert word_length(macron_breathing) == 2
        assert word_length(macron_breathing, policy="graphemes") == 1

    def test_custom_callable_is_recorded(self) -> None:
        def letters(word: str) -> int:
            return len(word) - word.count("sz")

        result = lix(["ország"], sentences=1, length_policy=letters)
        assert result.length_policy.startswith("custom:")
        assert result.length_policy.endswith("letters")

    def test_custom_policy_actually_changes_the_long_word_count(self) -> None:
        """Recording the policy is not enough; it has to be the one applied."""
        inflate = lix(["ország"], sentences=1, length_policy=lambda w: len(w) + 10)
        assert inflate.long_words == 1
        assert lix(["ország"], sentences=1).long_words == 0

    def test_callable_without_a_qualname_is_still_labelled(self) -> None:
        """functools.partial has no __qualname__, so the fallback must hold."""
        import functools

        result = lix(["ország"], sentences=1, length_policy=functools.partial(len))
        assert result.length_policy.startswith("custom:")
        assert "partial" in result.length_policy

    def test_unknown_policy_raises(self) -> None:
        with pytest.raises(ValueError, match="policy must be"):
            word_length("word", policy="glyphs")  # type: ignore[arg-type]

    def test_empty_word_has_zero_length(self) -> None:
        for policy in ("nfc", "graphemes", "codepoints"):
            assert word_length("", policy=policy) == 0  # type: ignore[arg-type]


class TestDegenerateInput:
    """Empty input raises a clear error rather than dividing by zero."""

    def test_empty_text(self) -> None:
        with pytest.raises(ValueError, match="at least one word"):
            lix("")

    def test_whitespace_only_text(self) -> None:
        with pytest.raises(ValueError, match="at least one word"):
            lix("   \n  ")

    def test_empty_token_list(self) -> None:
        with pytest.raises(ValueError, match="at least one word"):
            lix([], sentences=1)

    def test_zero_sentences(self) -> None:
        with pytest.raises(ValueError, match="at least one sentence"):
            lix(["word"], sentences=0)

    def test_negative_threshold(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            lix(CANONICAL, long_word_threshold=-1)

    def test_long_words_cannot_exceed_words(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed"):
            lix_from_counts(words=3, sentences=1, long_words=4)

    def test_long_words_cannot_be_negative(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            lix_from_counts(words=3, sentences=1, long_words=-1)

    def test_empty_tokens_are_dropped_and_counted(self) -> None:
        result = lix(["real", "", "  ", "words"], sentences=1)
        assert result.words == 2
        assert result.dropped_empty == 2


class TestRix:
    """RIX is long words per sentence."""

    def test_value(self) -> None:
        assert rix(CANONICAL) == 2.0

    def test_matches_the_result_property(self) -> None:
        assert rix(CANONICAL) == lix(CANONICAL).rix

    def test_honours_the_default_threshold(self) -> None:
        """Seven-letter "housing" is long at threshold 6, but not at 7."""
        assert rix(["housing"], sentences=1) == 1.0
        assert rix(["housing"], sentences=1, long_word_threshold=7) == 0.0

    def test_forwards_the_length_policy(self) -> None:
        assert rix(["ország"], sentences=1, length_policy=lambda w: len(w) + 10) == 1.0
        assert rix(["ország"], sentences=1) == 0.0

    def test_forwards_the_sentencer(self) -> None:
        def by_linebreak(text: str) -> list[str]:
            return [line for line in text.splitlines() if line.strip()]

        # Four long words. The line splitter sees B=2; the bundled splitter,
        # finding no terminal punctuation, sees B=1.
        text = "complicated sentences\nfrighten beginners"
        assert rix(text, sentencer=by_linebreak) == 2.0
        assert rix(text) == 4.0


class TestResultRecord:
    """The result carries everything needed to reproduce it."""

    def test_unit_is_always_surface(self) -> None:
        assert lix(CANONICAL).unit == "surface"

    def test_to_dict_round_trips_the_parameters(self) -> None:
        record = lix(CANONICAL, long_word_threshold=8).to_dict()
        assert record["long_word_threshold"] == 8
        assert record["unit"] == "surface"
        assert record["sentence_source"] == "segmented"

    def test_repr_shows_the_counts(self) -> None:
        text = repr(lix(CANONICAL))
        assert "A=10" in text
        assert "B=2" in text
        assert "C=4" in text

    def test_repr_omits_the_version(self) -> None:
        """Else every release would break every doctest that prints a result."""
        import saphes

        assert saphes.__version__ not in repr(lix(CANONICAL))

    def test_derived_terms(self) -> None:
        result = lix(CANONICAL)
        assert result.avg_sentence_length == 5.0
        assert result.long_word_share == 0.4

    def test_records_the_saphes_version(self) -> None:
        """The record is only reproducible if it says which version made it."""
        import saphes

        assert lix(CANONICAL).saphes_version == saphes.__version__


class TestTextstatParity:
    """Cross-check against the one available reference implementation."""

    TEXTS = (
        "The quick brown fox jumps over the lazy dog. "
        "It was a remarkably uneventful afternoon.",
        "He ran. She sang. The committee deliberated extensively yesterday.",
        "Mr. Bennet replied that he had not. He said no more.",
        "Readability formulas attempt to quantify comprehension difficulty. "
        "Bjornsson introduced the index in Sweden. Subsequent implementations "
        "disagreed considerably about tokenisation.",
        CANONICAL,
    )

    def test_exact_parity_given_the_same_sentence_count(self) -> None:
        """A, C and the arithmetic are identical; only B ever differs."""
        textstat = pytest.importorskip("textstat")
        for text in self.TEXTS:
            reference = textstat.lix(text)
            ours = lix(text, sentences=textstat.sentence_count(text)).score
            assert ours == pytest.approx(reference, abs=1e-9), text

    def test_end_to_end_divergence_is_bounded_and_is_segmentation(self) -> None:
        """Free-running, we differ from textstat only where B differs."""
        textstat = pytest.importorskip("textstat")
        for text in self.TEXTS:
            ours = lix(text)
            reference = textstat.lix(text)
            if ours.sentences == textstat.sentence_count(text):
                assert ours.score == pytest.approx(reference, abs=1e-9), text
            else:
                # textstat silently discards sentences of two words or fewer.
                assert abs(ours.score - reference) < 10.0, text


class TestLixProperties:
    """Property-based contracts over random token lists and thresholds."""

    @settings(max_examples=200, deadline=None)
    @given(word_list, st.integers(min_value=1, max_value=20), positive_threshold)
    def test_score_is_non_negative(
        self, words: list[str], sentences: int, threshold: int
    ) -> None:
        assert lix(words, sentences=sentences, long_word_threshold=threshold).score >= 0

    @settings(max_examples=200, deadline=None)
    @given(word_list, st.integers(min_value=1, max_value=20))
    def test_threshold_zero_gives_a_second_term_of_exactly_100(
        self, words: list[str], sentences: int
    ) -> None:
        result = lix(words, sentences=sentences, long_word_threshold=0)
        assert result.long_words == result.words
        assert result.score - result.avg_sentence_length == pytest.approx(100.0)

    @settings(max_examples=200, deadline=None)
    @given(word_list, st.integers(min_value=1, max_value=20), positive_threshold)
    def test_raising_the_threshold_never_raises_the_score(
        self, words: list[str], sentences: int, threshold: int
    ) -> None:
        lower = lix(words, sentences=sentences, long_word_threshold=threshold).score
        higher = lix(
            words, sentences=sentences, long_word_threshold=threshold + 1
        ).score
        assert higher <= lower + 1e-9

    @settings(max_examples=200, deadline=None)
    @given(word_list, st.integers(min_value=1, max_value=20), positive_threshold)
    def test_counts_reconstruct_the_score(
        self, words: list[str], sentences: int, threshold: int
    ) -> None:
        """The recorded counts are the ones that produced the score."""
        result = lix(words, sentences=sentences, long_word_threshold=threshold)
        assert lix_from_counts(
            words=result.words,
            sentences=result.sentences,
            long_words=result.long_words,
        ) == pytest.approx(result.score)
