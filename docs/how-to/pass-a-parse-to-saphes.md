# How to pass a HuSpaCy doc or an emtsv stream to saphes

You have a Hungarian parser and want a dependency-distance score out of it. saphes does not
parse; it measures parses. This is the conversion.

## From HuSpaCy or spaCy

```python
import hu_core_news_md
from saphes import from_spacy, mean_dependency_distance

nlp = hu_core_news_md.load()
doc = nlp("János tegnap reggel a barátaival együtt elment a moziba.")

result = mean_dependency_distance(
    from_spacy(doc), parser="huspacy hu_core_news_md 3.8.0"
)
print(result.mdd)
```

`from_spacy` never imports spaCy — it reads `doc.sents` and, per token, `i`, `head`,
`is_punct` and `pos_`. Anything exposing those works, so you can pass a HuSpaCy `Doc`, a
plain spaCy `Doc`, or your own object.

Two conversions happen for you: spaCy marks the root by making a token its own head, which
becomes `head=0`; and spaCy numbers tokens across the whole document, which becomes
per-sentence numbering. Both matter, and neither is something you should do yourself before
calling.

!!! warning "Your pipeline needs a parser"
    A pipeline running with `parser` disabled gives every token itself as a head. That is
    not an error and produces no warning — you simply get a document of one-token roots and
    an exception about there being no dependency pairs. Check `nlp.pipe_names`.

## From emtsv

Use the **`tok-dep-conll`** task, not the default `tok-dep`:

```bash
docker run --rm -i mtaril/emtsv tok-dep-conll < corpus.txt > corpus.conllu
```

```python
from saphes import from_conllu, mean_dependency_distance

parses = from_conllu(open("corpus.conllu").read())
result = mean_dependency_distance(parses, parser="emtsv tok-dep-conll")
```

emtsv's default output is **not** CoNLL-U. It carries a header row and orders its columns
`form wsafter anas lemma xpostag upostag feats id deprel head`, so `from_conllu` rejects it
rather than reading the wrong columns. `tok-dep-conll` emits the real ten-column format.

The same reader takes any CoNLL-U file, so a Universal Dependencies treebank works
unchanged.

## Check what you got

Both adapters hand back plain data, so you can look at it:

```pycon
>>> from saphes import from_conllu
>>> conllu = (
...     "1\tA\ta\tDET\t_\t_\t2\tdet\t_\t_\n"
...     "2\tkutya\tkutya\tNOUN\t_\t_\t3\tnsubj\t_\t_\n"
...     "3\tugat\tugat\tVERB\t_\t_\t0\troot\t_\t_\n"
...     "4\t.\t.\tPUNCT\t_\t_\t3\tpunct\t_\t_\n"
... )
>>> from_conllu(conllu)[0]
[DepToken(index=1, head=2, is_punct=False, pos='DET'), DepToken(index=2, head=3, is_punct=False, pos='NOUN'), DepToken(index=3, head=0, is_punct=False, pos='VERB'), DepToken(index=4, head=3, is_punct=True, pos='PUNCT')]

```

## Do not use `require_single_root` on emtsv output

emtsv attaches sentence-final punctuation to `0`, so **every** emtsv sentence has two roots.
HuSpaCy attaches it to the main verb, so its sentences have one. Turning on
`require_single_root` therefore discards the entire emtsv corpus and none of the HuSpaCy
one — from the same sentences.

The default `punctuation="collapse"` removes the punctuation before any of this matters,
which is why it is the default. If you want the filter, apply it to a corpus you have
checked, and read `skipped_sentences` on the result.

## Two engines will not give you the same number

They are different annotation schemes, not two attempts at one answer. On the fifteen
sentences in `experiments/adapter_fixtures/corpus.txt`, HuSpaCy and emtsv disagree about
where punctuation attaches, about bracket tagging, and consequently about MDD.

**Record which parser produced your trees** — that is what `parser=` is for, and it is the
field most worth filling. A parser carries the annotation convention of the treebank it was
trained on, and the convention decides which word is the head, which is the entire input to
a distance measure.

On one sentence of the fixture corpus the two engines agree about every word except three:

| token | HuSpaCy (UD) | emtsv (Prague) |
|---|---|---|
| `és` | → kötelezi | → elutasítja |
| `kötelezi` | → elutasítja | → **és** |
| `.` | → elutasítja | → **ROOT** |
| **MDD** | **1.600** | **1.500** |

Where you have a choice and no reason to prefer otherwise, use the spaCy model for the
language — for Hungarian, HuSpaCy. Choosing emtsv means choosing Prague-style trees, and
numbers that will not line up with anyone else's. See [what dependency distance
measures](../explanation/what-dependency-distance-measures.md).
