"""Tests for the bundled samples."""

import unicodedata

import pytest

from saphes.datasets import Sample, load_english, load_greek, load_hungarian

ALL_SAMPLES = [load_english(), load_hungarian(), load_greek()]


class TestSamples:
    """Every sample is well formed and NFC-normalised."""

    @pytest.mark.parametrize("sample", ALL_SAMPLES, ids=lambda s: s.language)
    def test_streams_have_equal_length(self, sample: Sample) -> None:
        assert len(sample.forms) == len(sample.lemmas) == len(sample.pairs)

    @pytest.mark.parametrize("sample", ALL_SAMPLES, ids=lambda s: s.language)
    def test_no_empty_tokens(self, sample: Sample) -> None:
        assert all(form.strip() for form in sample.forms)
        assert all(lemma.strip() for lemma in sample.lemmas)

    @pytest.mark.parametrize("sample", ALL_SAMPLES, ids=lambda s: s.language)
    def test_normalised_to_nfc(self, sample: Sample) -> None:
        assert sample.text == unicodedata.normalize("NFC", sample.text)
        for form, lemma in sample.pairs:
            assert form == unicodedata.normalize("NFC", form)
            assert lemma == unicodedata.normalize("NFC", lemma)

    @pytest.mark.parametrize("sample", ALL_SAMPLES, ids=lambda s: s.language)
    def test_tokens_carry_no_punctuation(self, sample: Sample) -> None:
        """Forms are stored bare, so length counts letters and nothing else."""
        for form in sample.forms:
            assert not any(char in form for char in ".,;:!?’'\"")

    @pytest.mark.parametrize("sample", ALL_SAMPLES, ids=lambda s: s.language)
    def test_has_a_source(self, sample: Sample) -> None:
        assert sample.source

    def test_languages(self) -> None:
        assert [s.language for s in ALL_SAMPLES] == ["en", "hu", "grc"]

    def test_greek_text_matches_its_tokens(self) -> None:
        """The running text and the annotation describe the same passage."""
        from saphes import segment

        sample = load_greek()
        assert len(segment.words(sample.text)) == len(sample.pairs)

    def test_hungarian_text_matches_its_tokens(self) -> None:
        from saphes import segment

        sample = load_hungarian()
        assert len(segment.words(sample.text)) == len(sample.pairs)
