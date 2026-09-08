"""Parse the benchmark corpus with HuSpaCy and record what it produced.

Step 1 of two. Writes ``tests/fixtures/huspacy.json``: one record per sentence, holding
exactly the token attributes ``saphes.adapters.from_spacy`` reads, plus the
surface forms so a human can see what was parsed.

HuSpaCy pulls in spaCy and a ~110 MB model. Neither is a saphes dependency and
neither can run in CI, so this script is run once by hand and its output is
committed. The tests replay the recording; they never import spaCy.

Usage:
    uv venv /tmp/hus-venv --python 3.12
    curl -sL -o /tmp/hu_core_news_md-3.8.0-py3-none-any.whl \
        https://huggingface.co/huspacy/hu_core_news_md/resolve/v3.8.0/hu_core_news_md-any-py3-none-any.whl
    uv pip install --python /tmp/hus-venv/bin/python spacy \
        /tmp/hu_core_news_md-3.8.0-py3-none-any.whl
    /tmp/hus-venv/bin/python experiments/adapter_fixtures/scripts/run_huspacy.py
"""

import json
import sys
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
CORPUS = EXPERIMENT_DIR / "corpus.txt"
OUT = EXPERIMENT_DIR.parents[1] / "tests" / "fixtures" / "huspacy.json"
MODEL = "hu_core_news_md"
MODEL_VERSION = "3.8.0"


def main() -> None:
    try:
        import hu_core_news_md
        import spacy
    except ImportError:
        sys.exit(
            "This script needs spaCy and hu_core_news_md, which saphes does not "
            "depend on. See the module docstring for the throwaway venv recipe."
        )

    nlp = hu_core_news_md.load()
    lines = [ln.strip() for ln in CORPUS.read_text().splitlines() if ln.strip()]

    sentences = []
    for line in lines:
        doc = nlp(line)
        for sent in doc.sents:
            sentences.append(
                {
                    "text": sent.text,
                    "tokens": [
                        {
                            # Document-global, exactly as spaCy reports them. The
                            # adapter is what makes these sentence-local, so the
                            # fixture must not do it here.
                            "i": token.i,
                            "head_i": token.head.i,
                            "text": token.text,
                            "pos": token.pos_,
                            "dep": token.dep_,
                            "is_punct": token.is_punct,
                        }
                        for token in sent
                    ],
                    "sent_start": sent.start,
                }
            )

    record = {
        "engine": "huspacy",
        "model": MODEL,
        "model_version": MODEL_VERSION,
        "spacy_version": spacy.__version__,
        "pipeline": list(nlp.pipe_names),
        "sentences": sentences,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    print(f"{len(sentences)} sentences -> {OUT}")


if __name__ == "__main__":
    main()
