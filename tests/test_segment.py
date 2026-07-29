"""Tests for the bundled word and sentence splitters."""

from hypothesis import given
from hypothesis import strategies as st

from saphes import segment


class TestWords:
    """Tokenisation keeps words whole and drops punctuation."""

    def test_basic(self) -> None:
        assert segment.words("One two three.") == ["One", "two", "three"]

    def test_internal_apostrophe_and_hyphen_kept(self) -> None:
        assert segment.words("It's good-humoured.") == ["It's", "good-humoured"]

    def test_trailing_elision_apostrophe_dropped(self) -> None:
        """Greek elision must not inflate the letter count."""
        assert segment.words("μυρί’ ἄλγε’ ἔθηκε") == ["μυρί", "ἄλγε", "ἔθηκε"]

    def test_hungarian_diacritics_are_word_characters(self) -> None:
        assert segment.words("őrült űrhajósok") == ["őrült", "űrhajósok"]

    def test_empty_text(self) -> None:
        assert segment.words("") == []


class TestSentences:
    """Sentence splitting guards the cases that silently corrupt B."""

    def test_basic(self) -> None:
        assert segment.sentences("One. Two.") == ["One.", "Two."]

    def test_abbreviation_not_a_boundary(self) -> None:
        assert segment.sentences("Mr. Bennet replied. He left.") == [
            "Mr. Bennet replied.",
            "He left.",
        ]

    def test_initial_not_a_boundary(self) -> None:
        assert segment.sentences("A. Bennet arrived. He left.") == [
            "A. Bennet arrived.",
            "He left.",
        ]

    def test_multi_letter_acronym_is_still_a_boundary(self) -> None:
        """Only a *single* capital is an initial; NASA ends a sentence."""
        assert segment.sentences("He works at NASA. Next sentence here.") == [
            "He works at NASA.",
            "Next sentence here.",
        ]

    def test_lowercase_continuation_not_a_boundary(self) -> None:
        assert segment.sentences('"Is it let?" she asked. He nodded.') == [
            '"Is it let?" she asked.',
            "He nodded.",
        ]

    def test_short_sentences_are_kept(self) -> None:
        """Textstat discards sentences of two words or fewer; saphes does not."""
        assert segment.sentences("He ran. She sang. They left.") == [
            "He ran.",
            "She sang.",
            "They left.",
        ]

    def test_unterminated_tail_is_a_sentence(self) -> None:
        assert segment.sentences("One. Two") == ["One.", "Two"]

    def test_empty_text(self) -> None:
        assert segment.sentences("") == []


class TestSegmentProperties:
    """Property-based contracts over arbitrary text."""

    @given(st.text())
    def test_sentences_are_stripped_and_nonempty(self, text: str) -> None:
        for sentence in segment.sentences(text):
            assert sentence == sentence.strip()
            assert sentence != ""

    @given(st.text())
    def test_words_are_nonempty_and_whitespace_free(self, text: str) -> None:
        for word in segment.words(text):
            assert word != ""
            assert word == "".join(word.split())

    @given(st.text())
    def test_words_appear_in_source_order(self, text: str) -> None:
        cursor = 0
        for word in segment.words(text):
            found = text.find(word, cursor)
            assert found >= 0
            cursor = found + len(word)
