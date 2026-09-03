"""Smoke tests for the saphes package scaffold."""

import subprocess
import sys

import saphes


class TestPackage:
    """The package imports and exposes its version."""

    def test_importable(self) -> None:
        assert saphes is not None

    def test_has_version(self) -> None:
        assert isinstance(saphes.__version__, str)
        assert saphes.__version__.count(".") == 2

    def test_public_api_is_reachable(self) -> None:
        for name in saphes.__all__:
            assert hasattr(saphes, name), name


class TestDependencyFreedom:
    """The core is dependency-free; heavy libraries stay optional."""

    def test_importing_saphes_pulls_in_no_third_party_module(self) -> None:
        """A fresh interpreter importing saphes must not load nltk or numpy.

        The guard against someone adding a convenience import that quietly makes
        a deliberately tiny package depend on a large one.
        """
        code = (
            "import sys, saphes;"
            "loaded = {m.split('.')[0] for m in sys.modules};"
            "heavy = loaded & {'nltk', 'numpy', 'spacy', 'pandas', 'textstat',"
            " 'snowballstemmer'};"
            "assert not heavy, heavy"
        )
        subprocess.run([sys.executable, "-c", code], check=True)

    def test_importing_the_optional_modules_pulls_in_nothing_either(self) -> None:
        """saphes.stem must not import snowballstemmer until it is called.

        The lazy import belongs to the function, not the module. mkdocstrings
        imports every module while building the docs, and that CI job syncs
        only the docs extra — a module-scope import would fail the build there
        rather than here.
        """
        code = (
            "import sys, saphes.stem, saphes.hungarian;"
            "loaded = {m.split('.')[0] for m in sys.modules};"
            "heavy = loaded & {'nltk', 'snowballstemmer'};"
            "assert not heavy, heavy"
        )
        subprocess.run([sys.executable, "-c", code], check=True)
