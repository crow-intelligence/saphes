"""Inline sample texts with parallel surface/lemma annotation.

The data lives inline as Python literals so it is always importable in doctests
with no package-data or ``importlib.resources`` machinery — the same convention
as ``keyflux.datasets`` and ``lexograph.datasets``.

Each sample pairs every surface form with its lemma, so both token streams come
from a single source of truth. That is what makes the surface-versus-lemma gap a
property of the *language* rather than of two independently typed lists.

Forms are stored bare: no punctuation, and no Greek elision apostrophe, which is
what any tokenisation yields and what an honest letter count should use.
"""

from __future__ import annotations

ENGLISH_TEXT = (
    "The cat sat on it. Complicated sentences generally frighten us. "
    "The cats sat on the mats, and the sitting cat watched."
)

ENGLISH_PAIRS: tuple[tuple[str, str], ...] = (
    ("The", "the"), ("cat", "cat"), ("sat", "sit"), ("on", "on"), ("it", "it"),
    ("Complicated", "complicated"), ("sentences", "sentence"),
    ("generally", "generally"), ("frighten", "frighten"), ("us", "we"),
    ("The", "the"), ("cats", "cat"), ("sat", "sit"), ("on", "on"),
    ("the", "the"), ("mats", "mat"), ("and", "and"), ("the", "the"),
    ("sitting", "sit"), ("cat", "cat"), ("watched", "watch"),
)  # fmt: skip

HUNGARIAN_TEXT = (
    "A kutya futott a kertben. A kutyák megálltak a fánál. A kutyáknak enni adtam."
)

HUNGARIAN_PAIRS: tuple[tuple[str, str], ...] = (
    ("A", "a"), ("kutya", "kutya"), ("futott", "fut"), ("a", "a"),
    ("kertben", "kert"),
    ("A", "a"), ("kutyák", "kutya"), ("megálltak", "megáll"), ("a", "a"),
    ("fánál", "fa"),
    ("A", "a"), ("kutyáknak", "kutya"), ("enni", "eszik"), ("adtam", "ad"),
)  # fmt: skip

# Iliad 1.1-7. Public domain; the lemmatisation follows the Ancient Greek
# Dependency Treebank's conventions.
GREEK_TEXT = (
    "μῆνιν ἄειδε θεὰ Πηληϊάδεω Ἀχιλῆος "
    "οὐλομένην, ἣ μυρί’ Ἀχαιοῖς ἄλγε’ ἔθηκε, "
    "πολλὰς δ’ ἰφθίμους ψυχὰς Ἄϊδι προΐαψεν "
    "ἡρώων, αὐτοὺς δὲ ἑλώρια τεῦχε κύνεσσιν "
    "οἰωνοῖσί τε πᾶσι, Διὸς δ’ ἐτελείετο βουλή, "
    "ἐξ οὗ δὴ τὰ πρῶτα διαστήτην ἐρίσαντε "
    "Ἀτρεΐδης τε ἄναξ ἀνδρῶν καὶ δῖος Ἀχιλλεύς."
)

GREEK_PAIRS: tuple[tuple[str, str], ...] = (
    ("μῆνιν", "μῆνις"), ("ἄειδε", "ἀείδω"), ("θεὰ", "θεά"),
    ("Πηληϊάδεω", "Πηληϊάδης"), ("Ἀχιλῆος", "Ἀχιλλεύς"),
    ("οὐλομένην", "οὐλόμενος"), ("ἣ", "ὅς"), ("μυρί", "μυρίος"),
    ("Ἀχαιοῖς", "Ἀχαιός"), ("ἄλγε", "ἄλγος"), ("ἔθηκε", "τίθημι"),
    ("πολλὰς", "πολύς"), ("δ", "δέ"), ("ἰφθίμους", "ἴφθιμος"),
    ("ψυχὰς", "ψυχή"), ("Ἄϊδι", "Ἀΐδης"), ("προΐαψεν", "προϊάπτω"),
    ("ἡρώων", "ἥρως"), ("αὐτοὺς", "αὐτός"), ("δὲ", "δέ"),
    ("ἑλώρια", "ἑλώριον"), ("τεῦχε", "τεύχω"), ("κύνεσσιν", "κύων"),
    ("οἰωνοῖσί", "οἰωνός"), ("τε", "τε"), ("πᾶσι", "πᾶς"), ("Διὸς", "Ζεύς"),
    ("δ", "δέ"), ("ἐτελείετο", "τελείω"), ("βουλή", "βουλή"),
    ("ἐξ", "ἐκ"), ("οὗ", "ὅς"), ("δὴ", "δή"), ("τὰ", "ὁ"),
    ("πρῶτα", "πρῶτος"), ("διαστήτην", "διΐστημι"), ("ἐρίσαντε", "ἐρίζω"),
    ("Ἀτρεΐδης", "Ἀτρεΐδης"), ("τε", "τε"), ("ἄναξ", "ἄναξ"),
    ("ἀνδρῶν", "ἀνήρ"), ("καὶ", "καί"), ("δῖος", "δῖος"),
    ("Ἀχιλλεύς", "Ἀχιλλεύς"),
)  # fmt: skip
