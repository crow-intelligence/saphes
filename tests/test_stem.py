"""Tests for the optional Snowball stemmer.

The stemmer's job is to be a *degraded* substitute for lemmatisation, so the
tests pin the degradation as carefully as the benefit. A stemmer that quietly
stopped stemming would still pass a test that only checked the output length.
"""

import pytest
from hypothesis import given, settings

from saphes.stem import hungarian_stems
from tests.strategies import inflected_pairs


class TestStemming:
    """Inflectional suffixes come off."""

    def test_paradigm_collapses(self) -> None:
        assert hungarian_stems(["ház", "házban", "házak", "házakat"]) == [
            "ház",
            "ház",
            "ház",
            "ház",
        ]

    def test_one_stem_per_token(self) -> None:
        tokens = ["a", "kutya", "futott", "a", "kertben"]
        assert len(hungarian_stems(tokens)) == len(tokens)

    def test_empty_input(self) -> None:
        assert hungarian_stems([]) == []

    def test_identical_tokens_get_identical_stems(self) -> None:
        """The premise behind stem-TTR never exceeding surface-TTR."""
        assert len(set(hungarian_stems(["kertben"] * 5))) == 1


class TestCaseFolding:
    """The algorithm is defined on lowercase input and fails silently above it."""

    def test_folded_by_default(self) -> None:
        assert hungarian_stems(["KUTYÁK"]) == hungarian_stems(["kutyák"])

    def test_unfolded_input_under_stems(self) -> None:
        """Pinned to show what case_fold=False costs: nothing is stripped."""
        assert hungarian_stems(["KUTYÁK"], case_fold=False) == ["KUTYÁK"]


class TestRawStringRefused:
    """A string is a sequence of characters, so stemming one is a silent error."""

    def test_raw_string_raises(self) -> None:
        with pytest.raises(TypeError, match="got a raw string"):
            hungarian_stems("kutya kert")

    def test_the_message_names_the_fix(self) -> None:
        with pytest.raises(TypeError, match="segment.words"):
            hungarian_stems("kutya kert")


class TestKnownDegradation:
    """Pinned failures. A stem is not a lemma and must not be read as one."""

    def test_over_stems_a_bare_noun(self) -> None:
        """The bare noun kert has no suffix to strip, and loses a letter anyway."""
        assert hungarian_stems(["kert"]) == ["ker"]

    def test_one_lemma_reaches_two_stems(self) -> None:
        """All three are the lemma kutya. The merge is partial, not wrong-free."""
        assert hungarian_stems(["kutya", "kutyák", "kutyáknak"]) == [
            "kuty",
            "kutya",
            "kutya",
        ]

    def test_stems_are_not_words(self) -> None:
        assert hungarian_stems(["fánál", "adtam", "enni"]) == ["fá", "adt", "enn"]

    def test_non_hungarian_input_is_stemmed_anyway(self) -> None:
        """Total function, no language check — documented, so pinned."""
        assert hungarian_stems(["running"]) == ["running"]


class TestStemProperties:
    """Stemming is a function on tokens, so it can merge types but never split."""

    @settings(max_examples=200, deadline=None)
    @given(inflected_pairs())
    def test_type_count_never_grows(self, pairs: list[tuple[str, str]]) -> None:
        forms = [form for form, _ in pairs]
        assert len(set(hungarian_stems(forms))) <= len(set(forms))

    @settings(max_examples=200, deadline=None)
    @given(inflected_pairs())
    def test_token_count_is_preserved(self, pairs: list[tuple[str, str]]) -> None:
        """The other half of the premise: no token is dropped or added."""
        forms = [form for form, _ in pairs]
        assert len(hungarian_stems(forms)) == len(forms)

    def test_stemming_is_not_idempotent(self) -> None:
        """Pinned as a failure, because the obvious property does not hold.

        Snowball strips one layer of suffix, and its output can itself look
        suffixed. Stemming twice is not stemming once, so the stems in a result
        depend on how many times they went through — which is one more reason a
        stem-TTR is comparable only within a single pipeline.
        """
        once = hungarian_stems(["kutyaak"])
        assert once == ["kutya"]
        assert hungarian_stems(once) == ["kuty"]
