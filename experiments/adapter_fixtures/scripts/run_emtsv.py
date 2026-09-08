"""Parse the benchmark corpus with emtsv and record the CoNLL-U it produced.

Step 2 of two. Writes ``tests/fixtures/emtsv.conllu``.

emtsv ships as a ~10 GB Docker image and takes about two minutes to start, so
this is run once by hand and its output committed. The tests read the file; they
never invoke Docker.

Two things about emtsv that the adapter design depends on, both verified here
rather than assumed:

* Its **default** output is not CoNLL-U. ``tok-dep`` emits a header row and a
  different column order (``form wsafter anas lemma xpostag upostag feats id
  deprel head``), which :func:`saphes.adapters.from_conllu` rejects by design.
  The ``tok-dep-conll`` task emits real 10-column CoNLL-U with no header.
* It attaches sentence-final punctuation to **0**, making it a second root.
  HuSpaCy attaches it to the main verb. Neither is wrong; they are different
  annotation schemes, and the difference is why ``require_single_root`` must not
  be applied to emtsv output before punctuation is collapsed.

Usage:
    docker pull mtaril/emtsv
    docker run --rm -i mtaril/emtsv tok-dep-conll \
        < experiments/adapter_fixtures/corpus.txt \
        > tests/fixtures/emtsv.conllu
"""

import shutil
import subprocess
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
CORPUS = EXPERIMENT_DIR / "corpus.txt"
OUT = EXPERIMENT_DIR.parents[1] / "tests" / "fixtures" / "emtsv.conllu"
IMAGE = "mtaril/emtsv"
TASK = "tok-dep-conll"


def main() -> None:
    if shutil.which("docker") is None:
        sys.exit("This script needs Docker. See the module docstring.")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with CORPUS.open("rb") as stdin, OUT.open("wb") as stdout:
        result = subprocess.run(  # noqa: S603
            ["docker", "run", "--rm", "-i", IMAGE, TASK],  # noqa: S607
            stdin=stdin,
            stdout=stdout,
            check=False,
        )
    if result.returncode != 0:
        sys.exit(f"emtsv failed with exit code {result.returncode}")
    sentences = OUT.read_text().count("\n\n")
    print(f"{sentences} sentences -> {OUT}")


if __name__ == "__main__":
    main()
