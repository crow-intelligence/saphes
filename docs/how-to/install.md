# Install saphes

```bash
uv add saphes
```

The core has no runtime dependencies — plain Python and the standard library.

## With the NLTK Punkt sentence splitter

Only needed if you want `sentences(text, punkt=True)` instead of the bundled splitter.

```bash
uv add 'saphes[punkt]'
```

The Punkt model itself is downloaded on first use, not at install time. If that download
fails you will see a `LookupError` about a missing resource rather than a network error — see
[Plug in a sentence splitter](plug-in-a-sentence-splitter.md).

## For development

```bash
git clone https://github.com/crow-intelligence/saphes
cd saphes
pyenv local 3.12
uv sync --all-extras
make ci
```

`--all-extras` pulls in the test, docs and experiment dependencies. `make ci` runs format
check, lint, type check and the full test suite, which is what CI runs.
