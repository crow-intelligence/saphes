"""Tests for Hungarian letter counting.

The counter has to be right about three separate things — maximal munch,
doubled spellings, and morpheme boundaries — and getting one right while
getting another wrong still produces a plausible number. So the failures the
old collapser made are pinned here explicitly, with the wrong answer in a
comment, rather than only the right ones being asserted.
"""

import math

from hypothesis import given, settings

from saphes.calibration import collapse_digraphs
from saphes.hungarian import (
    HU_LETTERS,
    hungarian_letter_count,
    hungarian_letters,
)
from tests.strategies import hungarian_multigraph_word, hungarian_word


class TestPlainWords:
    """Words with no multi-character letter are just their characters."""

    def test_no_multigraph(self) -> None:
        assert hungarian_letter_count("alma") == 4

    def test_empty(self) -> None:
        assert hungarian_letter_count("") == 0
        assert hungarian_letters("") == []

    def test_case_folded(self) -> None:
        assert hungarian_letter_count("Ország") == hungarian_letter_count("ország")


class TestMultigraphs:
    """One letter, however many characters it is written with."""

    def test_digraph(self) -> None:
        assert hungarian_letter_count("ország") == 5  # o r sz á g

    def test_trigraph(self) -> None:
        """The dzs trigraph is one letter, not dz plus s."""
        assert hungarian_letter_count("bridzs") == 4  # b r i dzs

    def test_trigraph_initial(self) -> None:
        """The spec asked for 7 here; dzs u n g e l is 6."""
        assert hungarian_letter_count("dzsungel") == 6

    def test_segmentation_is_returned(self) -> None:
        assert hungarian_letters("ország") == ["o", "r", "sz", "á", "g"]


class TestGeminates:
    """A doubled letter is written short: long sz is ssz, not szsz."""

    def test_doubled_digraph(self) -> None:
        assert hungarian_letters("meggyes") == ["m", "e", "gy", "gy", "e", "s"]

    def test_doubled_at_word_end(self) -> None:
        assert hungarian_letter_count("gally") == 4  # g a ly ly

    def test_doubled_trigraph(self) -> None:
        assert hungarian_letter_count("eddzük") == 5  # e dz dz ü k

    def test_doubled_zs(self) -> None:
        assert hungarian_letters("rizzsel") == ["r", "i", "zs", "zs", "e", "l"]

    def test_geminate_reading_is_count_neutral(self) -> None:
        """The word vasszeg is vas + szeg, so its ssz is s + sz, not a long sz.

        The segmentation below is wrong and the count is right, because both
        readings are two letters. That is why compound seams at a doubled
        spelling need no table entry.
        """
        assert hungarian_letters("vasszeg") == ["v", "a", "sz", "sz", "e", "g"]
        assert hungarian_letter_count("vasszeg") == 6  # v a s sz e g


class TestCascade:
    """Scanning consumes; it does not rewrite, so no digraph is manufactured."""

    def test_z_before_sz(self) -> None:
        assert hungarian_letter_count("vízszint") == 7  # collapse_digraphs says 6
        assert len(collapse_digraphs("vízszint")) == 6

    def test_z_before_sz_inflected(self) -> None:
        assert hungarian_letter_count("tűzszünet") == 8  # collapse_digraphs says 7

    def test_long_compound(self) -> None:
        assert hungarian_letter_count("közszolgálati") == 12  # collapser says 11

    def test_zsz_reads_as_z_plus_sz(self) -> None:
        """Attested: every frequent zsz in the Webcorpus is a z + sz seam."""
        assert hungarian_letters("vízszint") == ["v", "í", "z", "sz", "i", "n", "t"]

    def test_geminate_does_not_outrank_a_shorter_letter(self) -> None:
        """kulcsszó is kulcs + szó. ssz must not win over cs here."""
        assert hungarian_letters("kulcsszó") == ["k", "u", "l", "cs", "sz", "ó"]

    def test_szsz_is_two_letters(self) -> None:
        assert hungarian_letter_count("húszszor") == 6  # h ú sz sz o r


class TestSuffixRule:
    """The productive -ság/-ség suffix after a stem-final z or c."""

    def test_z_stem(self) -> None:
        assert hungarian_letter_count("igazságos") == 9  # i g a z s á g o s

    def test_z_stem_bare(self) -> None:
        assert hungarian_letter_count("község") == 6  # the old counter said 5

    def test_c_stem(self) -> None:
        assert hungarian_letter_count("malacság") == 8  # m a l a c s á g

    def test_compound_of_a_covered_stem(self) -> None:
        """A rule, not a list, so words nobody enumerated are covered too."""
        assert hungarian_letter_count("nagyközség") == 9  # n a gy k ö z s é g
        assert hungarian_letter_count("féligazság") == 10

    def test_self_correcting_when_sz_binds_leftward(self) -> None:
        """egészség is egész + ség; the sz is real, so the rule must not fire."""
        assert hungarian_letters("egészség") == ["e", "g", "é", "sz", "s", "é", "g"]

    def test_self_correcting_bare(self) -> None:
        assert hungarian_letter_count("készség") == 6  # k é sz s é g

    def test_rule_can_be_switched_off(self) -> None:
        """It changes the number, so it is a parameter and not a constant."""
        assert hungarian_letter_count("község", suffix_rule=False) == 5


class TestBoundaries:
    """The compound table, and the residual failure it does not remove."""

    def test_table_entry_marks_the_seam(self) -> None:
        assert hungarian_letter_count("házsor", boundaries={"házsor": "ház-sor"}) == 6

    def test_table_covers_inflected_forms(self) -> None:
        """Substring replacement, so one entry covers the paradigm."""
        table = {"házsor": "ház-sor"}
        assert hungarian_letter_count("házsorokban", boundaries=table) == 11

    def test_unlisted_compound_is_silently_short(self) -> None:
        """The residual failure. vadzab is vad + zab, six letters.

        Pinned with an empty table to show what the module does *not* fix: a
        compound outside the table gets no error and no warning, just a number
        that is one too low.
        """
        assert hungarian_letter_count("vadzab", boundaries={}) == 5  # truly 6


class TestHyphens:
    """A hyphen is not a letter, and letters do not form across it."""

    def test_hyphen_is_not_counted(self) -> None:
        assert hungarian_letter_count("e-mail") == 5  # e m a i l

    def test_hyphen_blocks_a_digraph(self) -> None:
        assert hungarian_letter_count("gáz-számla") == 8  # g á z sz á m l a


class TestProperties:
    """Contracts over generated letter sequences.

    Subadditivity is deliberately absent: ``count("va") + count("dzab")`` is 5
    but ``count("vadzab")`` under a table entry is 6, so any boundary table
    breaks it. Monotonicity under append is absent for the same reason — an
    appended character can complete a ``BOUNDARY_EXCEPTIONS`` entry, which
    switches the suffix rule off and lowers the count.
    """

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_never_exceeds_the_character_count(self, word: str) -> None:
        assert hungarian_letter_count(word) <= len(word)

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_no_letter_spans_more_than_three_characters(self, word: str) -> None:
        """The dzs trigraph is the longest single letter, so this is the floor."""
        assert hungarian_letter_count(word) >= math.ceil(len(word) / 3)

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_every_entry_is_a_letter(self, word: str) -> None:
        for letter in hungarian_letters(word):
            assert letter in HU_LETTERS or len(letter) == 1

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_count_is_the_length_of_the_segmentation(self, word: str) -> None:
        assert hungarian_letter_count(word) == len(hungarian_letters(word))

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_case_insensitive(self, word: str) -> None:
        assert hungarian_letter_count(word) == hungarian_letter_count(word.upper())

    @settings(max_examples=300, deadline=None)
    @given(hungarian_multigraph_word)
    def test_sits_between_the_collapser_and_the_character_count(
        self, word: str
    ) -> None:
        """The ordering that makes the calibration argument a proof.

        The collapser over-merges and the character count under-merges, so any
        correct letter count is trapped between them — which is why the
        calibrated threshold cannot move outside the range the study already
        published.
        """
        assert len(collapse_digraphs(word)) <= hungarian_letter_count(word) <= len(word)

    @settings(max_examples=300, deadline=None)
    @given(hungarian_word)
    def test_holds_on_the_character_alphabet_too(self, word: str) -> None:
        assert hungarian_letter_count(word) <= len(word)
