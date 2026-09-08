"""The two-opposite-contracts guard.

This file deliberately breaks the one-test-file-per-module convention, because
what it tests is the relationship *between* ``saphes.readability`` and
``saphes.diversity``: they require opposite token streams, and feeding one stream
to both produces no error, no NaN, just a plausible wrong number.

If someone ever "helpfully" wires both metrics to a single token stream, the
asymmetry tests here are what fail.

``saphes.syntax`` adds a third stream that is not a token stream at all — it
needs head indices, which no tokeniser produces. ``saphes.loanwords`` wants
lemmas, like ``diversity`` and unlike ``readability``. Both guards are at the
bottom.
"""

import pytest
from hypothesis import given, settings

from saphes import (
    DepToken,
    hungarian_stems,
    lexical_diversity,
    lix,
    loanword_ratio,
    mean_dependency_distance,
    word_length,
)
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

    def test_stem_ttr_is_lower_than_surface_ttr(self) -> None:
        """A theorem, given a margin. Stemming merges types and adds none.

        Pinned as a floor rather than ``<=`` for the same reason as the lemma
        gap above: a stemmer that silently stopped stemming would return the
        surface stream unchanged and a bare ``<=`` would still pass.
        """
        sample = load_hungarian()
        forms = list(sample.forms)
        surface = lexical_diversity(forms, unit="surface", case_fold=True).ttr
        stem = lexical_diversity(hungarian_stems(forms), unit="stem").ttr
        assert surface - stem >= 0.05

    def test_lemma_ttr_is_lower_than_stem_ttr(self) -> None:
        """MEASURED, not a theorem. Do not read this as a property of stemming.

        Neither map refines the other. Snowball under-stems (``kutya`` and
        ``kutyák`` reach different stems though they share a lemma, pushing
        stem-TTR up) and over-stems (``fánál`` becomes ``fá``, merging what a
        lemmatiser keeps apart, pushing it down). Which wins is an empirical
        fact about this stemmer on this sample, and it is pinned so that a
        Snowball upgrade that changes it is visible.

        If this fails, read the stemmer's diff. Do not relax it to a bare ``>``.
        """
        sample = load_hungarian()
        stem = lexical_diversity(hungarian_stems(sample.forms), unit="stem").ttr
        lemma = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True).ttr
        assert stem - lemma >= 0.05

    def test_lix_on_stems_understates_the_score(self) -> None:
        """Stemming destroys the length signal, exactly as lemmatising does."""
        sample = load_hungarian()
        correct = lix(sample.forms, sentences=3)
        wrong = lix(hungarian_stems(sample.forms), sentences=3)
        assert wrong.score < correct.score

    @pytest.mark.parametrize("sample", INFLECTED, ids=lambda s: s.language)
    def test_every_result_records_its_unit(self, sample: Sample) -> None:
        """So a serialised table can always say which stream produced each number."""
        assert lix(sample.forms, sentences=3).unit == "surface"
        assert lexical_diversity(sample.lemmas, unit="lemma").unit == "lemma"
        assert lexical_diversity(sample.forms, unit="stem").unit == "stem"


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
    def test_stem_ttr_never_exceeds_surface_ttr(
        self, pairs: list[tuple[str, str]]
    ) -> None:
        """The same theorem as for lemmas: stemming merges types, never splits."""
        forms = [form for form, _ in pairs]
        surface = lexical_diversity(forms, unit="surface").ttr
        stem = lexical_diversity(hungarian_stems(forms), unit="stem").ttr
        assert stem <= surface + 1e-12

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


class TestParseIsAThirdStream:
    """MDD needs head indices; no token stream, lemma or surface, can supply them.

    The failure this guards is worse than the lemma/surface mix-up, because a
    parse stripped of its punctuation without re-indexing still *looks* like a
    parse and still returns a number.
    """

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

    def test_no_cross_wiring_from_the_readability_side(self) -> None:
        with pytest.raises(TypeError):
            lix(parses=[self.NIXON])  # type: ignore[call-arg]

    def test_no_cross_wiring_from_the_diversity_side(self) -> None:
        with pytest.raises(TypeError):
            lexical_diversity(parses=[self.NIXON], unit="lemma")  # type: ignore[call-arg]

    def test_mdd_takes_no_words_parameter(self) -> None:
        """The parameter name is the enforcement mechanism, as it is for lix()."""
        with pytest.raises(TypeError):
            mean_dependency_distance(words=["a", "b"])  # type: ignore[call-arg]

    def test_mdd_takes_no_unit_parameter(self) -> None:
        with pytest.raises(TypeError):
            mean_dependency_distance([self.NIXON], unit="surface")  # type: ignore[call-arg]

    def test_a_lemma_stream_cannot_reach_mdd(self) -> None:
        sample = load_hungarian()
        with pytest.raises((TypeError, ValueError)):
            mean_dependency_distance([sample.lemmas])  # type: ignore[arg-type]

    def test_a_surface_stream_cannot_reach_mdd(self) -> None:
        sample = load_hungarian()
        with pytest.raises((TypeError, ValueError)):
            mean_dependency_distance([sample.forms])  # type: ignore[arg-type]

    def test_a_hand_stripped_parse_is_refused(self) -> None:
        """Punctuation removed without renumbering is the silent-failure case."""
        stripped = [token for token in self.NIXON if not token.is_punct]
        assert stripped == self.NIXON[:-1]  # the period was last, so nothing shifts
        gapped = [token for token in self.NIXON if token.index != 3]
        with pytest.raises(ValueError, match="must run 1..n"):
            mean_dependency_distance([gapped])

    def test_the_parse_carries_information_no_token_stream_has(self) -> None:
        """Shuffling heads changes MDD while leaving every token untouched."""
        rewired = [
            DepToken(
                t.index, 0 if t.head == 0 else 1 + (t.index % 2), t.is_punct, t.pos
            )
            for t in self.NIXON
        ]
        original = mean_dependency_distance([self.NIXON]).mdd
        assert mean_dependency_distance([rewired]).mdd != pytest.approx(original)


class TestLoanwordsNeedLemmas:
    """The loan-word ratio wants the same stream as diversity, not readability.

    Its silent failure is the mirror of the LIX one: an inflected form misses
    the lexicon, so a surface stream reports a plausible *low* ratio rather than
    an error.
    """

    # A stand-in, not a claim: these are native Hungarian words, chosen because
    # they appear in the bundled sample in inflected form. The contract under
    # test is which token stream reaches the lookup, not what a real
    # idegenszó lexicon would contain. The samples are far too small to
    # support any claim about Hungarian, as PRE-MORTEM.md item 2 records.
    LEXICON = {"kutya", "kert", "fa", "eszik"}

    def test_no_cross_wiring_from_the_readability_side(self) -> None:
        with pytest.raises(TypeError):
            lix(lemmas=["ház", "kutya"])  # type: ignore[call-arg]

    def test_loanword_ratio_takes_no_words_parameter(self) -> None:
        with pytest.raises(TypeError):
            loanword_ratio(words=["ház"], lexicon=self.LEXICON)  # type: ignore[call-arg]

    def test_loanword_ratio_takes_no_unit_parameter(self) -> None:
        """Unlike lexical_diversity: this metric has exactly one legal stream."""
        with pytest.raises(TypeError):
            loanword_ratio(["ház"], unit="lemma", lexicon=self.LEXICON)  # type: ignore[call-arg]

    def test_a_raw_string_is_refused(self) -> None:
        with pytest.raises(TypeError, match="raw string"):
            loanword_ratio("ház és kutya", lexicon=self.LEXICON)  # type: ignore[arg-type]

    @pytest.mark.parametrize("sample", INFLECTED, ids=lambda s: s.language)
    def test_the_lemma_stream_never_finds_fewer(self, sample: Sample) -> None:
        """Lemmatisation can only reveal lexicon entries, never hide them."""
        surface = loanword_ratio(
            sample.forms, lexicon=self.LEXICON, case_fold=True
        ).matched
        lemma = loanword_ratio(
            sample.lemmas, lexicon=self.LEXICON, case_fold=True
        ).matched
        assert lemma >= surface

    def test_the_asymmetry_is_real_on_hungarian(self) -> None:
        """Pinned as a floor: a merged stream would give a gap of exactly 0.

        Hungarian inflection hides four of the five occurrences here. Do not
        relax this to a bare ``>``; the failure being guarded is a gap of
        exactly zero, which ``>=`` would let through.
        """
        sample = load_hungarian()
        surface = loanword_ratio(sample.forms, lexicon=self.LEXICON).matched
        lemma = loanword_ratio(sample.lemmas, lexicon=self.LEXICON).matched
        assert surface == 1
        assert lemma == 6
        assert lemma - surface >= 4

    def test_the_result_records_which_stream_it_measured(self) -> None:
        assert loanword_ratio(["ház"], lexicon=self.LEXICON).unit == "lemma"
