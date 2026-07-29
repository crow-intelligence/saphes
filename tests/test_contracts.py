"""The two-opposite-contracts guard.

This file deliberately breaks the one-test-file-per-module convention, because
what it tests is the relationship *between* ``saphes.readability`` and
``saphes.diversity``: they require opposite token streams, and feeding one stream
to both produces no error, no NaN, just a plausible wrong number.

If someone ever "helpfully" wires both metrics to a single token stream, the
asymmetry tests here are what fail.
"""

import pytest
from hypothesis import given, settings

from saphes import lexical_diversity, lix, word_length
from saphes.datasets import Sample, load_english, load_greek, load_hungarian
from tests.strategies import inflected_pairs

INFLECTED = [load_hungarian(), load_greek()]


def _mean_length(words: list[str]) -> float:
    return sum(word_length(w) for w in words) / len(words)


class TestUnitIsRequired:
    """The choice that changes the answer is never made silently."""

    def test_omitting_unit_raises(self) -> None:
        with pytest.raises(TypeError, match="unit"):
            lexical_diversity(["a", "b"])  # type: ignore[call-arg]

    def test_lix_takes_no_unit(self) -> None:
        """A lix() call never carries unit=, which is what makes guard 1 work."""
        with pytest.raises(TypeError):
            lix("some text", unit="surface")  # type: ignore[call-arg]


class TestRawStringRefused:
    """A string can only yield surface forms, so it cannot stand in for lemmas."""

    def test_refused_as_lemmas(self) -> None:
        with pytest.raises(TypeError, match="raw string"):
            lexical_diversity("ház házak házban", unit="lemma")

    def test_accepted_as_surface(self) -> None:
        assert lexical_diversity("ház házak házban", unit="surface").tokens == 3


class TestNoCrossWiring:
    """The parameter names differ, so crossing the two calls fails loudly."""

    def test_lix_rejects_lemmas_keyword(self) -> None:
        with pytest.raises(TypeError):
            lix(lemmas=["a", "b"], sentences=1)  # type: ignore[call-arg]

    def test_lexical_diversity_rejects_words_keyword(self) -> None:
        with pytest.raises(TypeError):
            lexical_diversity(words=["a", "b"], unit="lemma")  # type: ignore[call-arg]


class TestAsymmetry:
    """On inflected languages, lemma-TTR is measurably lower than surface-TTR.

    The gap is the morphology the lemmas removed. These are pinned *floors*, not
    just ``>``: a refactor that wired both metrics to one stream would produce a
    gap of exactly 0.0, and a bare ``>`` would be the only thing standing between
    that and a green suite.
    """

    @pytest.mark.parametrize("sample", INFLECTED, ids=lambda s: s.language)
    def test_lemma_ttr_is_lower_than_surface_ttr(self, sample: Sample) -> None:
        surface = lexical_diversity(sample.forms, unit="surface", case_fold=True).ttr
        lemma = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True).ttr
        assert surface - lemma >= 0.05

    def test_hungarian_gap_is_large(self) -> None:
        """Agglutination should show up as more than a rounding difference."""
        sample = load_hungarian()
        surface = lexical_diversity(sample.forms, unit="surface", case_fold=True).ttr
        lemma = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True).ttr
        assert surface - lemma >= 0.10

    def test_english_gap_is_smaller_than_hungarian(self) -> None:
        """Light inflection, small gap — the asymmetry scales with morphology."""

        def gap(sample: Sample) -> float:
            surface = lexical_diversity(
                sample.forms, unit="surface", case_fold=True
            ).ttr
            lemma = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True).ttr
            return surface - lemma

        assert gap(load_english()) < gap(load_hungarian())

    def test_hungarian_words_are_longer_than_their_lemmas(self) -> None:
        """The LIX-side mirror: házakban is 8 characters, ház is 3."""
        sample = load_hungarian()
        assert _mean_length(sample.forms) - _mean_length(sample.lemmas) >= 1.0

    @pytest.mark.parametrize("sample", INFLECTED, ids=lambda s: s.language)
    def test_lix_on_lemmas_understates_the_score(self, sample: Sample) -> None:
        """Lemmatising before LIX destroys the measurement it is meant to make."""
        correct = lix(sample.forms, sentences=3)
        wrong = lix(sample.lemmas, sentences=3)
        assert wrong.score < correct.score

    @pytest.mark.parametrize("sample", INFLECTED, ids=lambda s: s.language)
    def test_every_result_records_its_unit(self, sample: Sample) -> None:
        """So a serialised table can always say which stream produced each number."""
        assert lix(sample.forms, sentences=3).unit == "surface"
        assert lexical_diversity(sample.lemmas, unit="lemma").unit == "lemma"


class TestContractProperties:
    """Property-based contracts over the surface/lemma asymmetry.

    Not a sample but a theorem: lemmatisation is a function on tokens, so it can
    only merge types, never split them. With the token count held equal, the
    lemma stream can never have more types than the surface stream — and so can
    never have the higher TTR.
    """

    @settings(max_examples=200, deadline=None)
    @given(inflected_pairs())
    def test_lemma_ttr_never_exceeds_surface_ttr(
        self, pairs: list[tuple[str, str]]
    ) -> None:
        forms = [form for form, _ in pairs]
        lemmas = [lemma for _, lemma in pairs]
        surface = lexical_diversity(forms, unit="surface").ttr
        lemma = lexical_diversity(lemmas, unit="lemma").ttr
        # `<=` not `<`: every suffix may have been drawn empty.
        assert lemma <= surface + 1e-12

    @settings(max_examples=200, deadline=None)
    @given(inflected_pairs())
    def test_surface_words_are_never_shorter_than_their_lemmas(
        self, pairs: list[tuple[str, str]]
    ) -> None:
        forms = [form for form, _ in pairs]
        lemmas = [lemma for _, lemma in pairs]
        assert _mean_length(forms) >= _mean_length(lemmas)

    @settings(max_examples=200, deadline=None)
    @given(inflected_pairs())
    def test_token_counts_stay_equal_across_the_two_streams(
        self, pairs: list[tuple[str, str]]
    ) -> None:
        """The premise the theorem rests on: lemmatisation does not drop tokens."""
        forms = [form for form, _ in pairs]
        lemmas = [lemma for _, lemma in pairs]
        assert (
            lexical_diversity(forms, unit="surface").tokens
            == lexical_diversity(lemmas, unit="lemma").tokens
        )
