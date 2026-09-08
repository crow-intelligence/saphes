# Changes summary — saphes v2

Five branches off `main`, opened as a **stack of draft PRs**. None merged, `main` untouched.
Each was verified green on its own before it was opened, so the stack bisects.

| PR | branch | base | what it adds |
|---:|---|---|---|
| [#4](https://github.com/crow-intelligence/saphes/pull/4) | `syntax-mean-dependency-distance` | `main` | `saphes.syntax` — mean dependency distance |
| [#5](https://github.com/crow-intelligence/saphes/pull/5) | `adapters-huspacy-and-conllu` | #4 | `saphes.adapters` — HuSpaCy and CoNLL-U/emtsv |
| [#6](https://github.com/crow-intelligence/saphes/pull/6) | `hierarchical-distance` | #5 | mean hierarchical distance |
| [#7](https://github.com/crow-intelligence/saphes/pull/7) | `loanword-ratio` | #6 | `saphes.loanwords` — idegenszó-arány |
| [#8](https://github.com/crow-intelligence/saphes/pull/8) | `loanword-lexicon-study` | #7 | the lexicon coverage study |

`make ci` green at every tip: **614 tests**, the three new modules at **100%** coverage,
`mkdocs build --strict` clean, `ty` clean.

(The previous iteration's summary — the Hungarian letter-counting round — is in git history
at `6282e72..164b4f9`.)

---

## 1. The literature was read, and it corrected the specification

`papers/` held the sources. Both worked examples in the MDD literature are pinned as
doctests and reproduce exactly:

| source | sentence | published | ours |
|---|---|---:|---:|
| Jing & Liu 2015: 164 | *Mr. Nixon was to leave China today .* | 1.17 | 7/6 |
| Jing & Liu 2015: 164 | same sentence, MHD | 2 | 12/6 |
| Zhang & Zhou 2023 | *The quick brown fox jumped over the lazy dog.* | 2.125 | 17/8 |

**Neither paper prints the tree behind its number.** Both were reconstructed by hand and
both close. The Nixon analysis is `was → to → leave → {China, today}`, `was → Nixon → Mr.`

Three corrections to the spec, all from the papers:

1. **The spec's "Method A" has no basis in the literature.** All three MDD papers strip
   punctuation *before* distances are computed, which re-indexes. Method A ships as
   `punctuation="ignore"`, but as the non-default, and the docstring says which one the
   papers mean. Backwards, it inflates MDD for every sentence containing a comma.
2. **Text-level aggregation is a fork the spec did not mention.** Jing & Liu's equations
   (3)/(4) are a *macro* average of per-sentence means. A naive implementation produces
   *micro* by accident. Both ship; macro is the default; the choice is on the receipt.
3. **Futrell et al. argue *against* MDD**, preferring summed dependency length regressed on
   sentence length. Citing them as support would misrepresent them; they are cited for the
   arc-length definition and their objection is stated in the explanation page.

**The licensing directive could not be carried out as written.** Neither `textdescriptives`
nor `QuanSyn` is installed or checked out anywhere on this machine, so nothing was read,
nothing adapted, and no attribution is owed.

## 2. Real parser output changed the adapter design

HuSpaCy (`hu_core_news_md` 3.8.0 on spaCy 3.8.16) and emtsv (`mtaril/emtsv`) were installed
and run locally. Three findings hand-written fixtures would not have produced:

- **spaCy marks the root with a self-loop** — `token.head is token`, not `head = 0`.
- **emtsv's default output is not CoNLL-U.** It has a header row and the order `form wsafter
  anas lemma xpostag upostag feats id deprel head`. The `tok-dep-conll` task emits the real
  format. The plan assumed the default already was CoNLL-U.
- **`is_punct` and the POS tag disagree** — HuSpaCy tags `(` as `PROPN` while setting
  `is_punct=True`, and hangs tokens off it. This also made `orphaned_arcs`, added
  defensively in #4, a real case: one sentence of ordinary legal Hungarian produces one.

A fourth is pinned as a test rather than smoothed over: emtsv attaches sentence-final
punctuation to `0`, giving every sentence two roots, where HuSpaCy attaches it to the verb.
`require_single_root=True` therefore discards the **entire** emtsv corpus and **none** of
the HuSpaCy one, from the same fifteen sentences.

**The two engines invert between the metrics** — HuSpaCy higher MDD (1.6845 vs 1.5328),
lower MHD (1.5492 vs 1.8128), emtsv two levels deeper. That is the case MHD exists to
expose, and it comes from the annotation schemes, not the text.

## 3. Decisions that change the numbers

| decision | default | why |
|---|---|---|
| `punctuation` | `"collapse"` | the only policy in the literature; `"ignore"` reports larger, `"keep"` larger still |
| `aggregation` | `"macro"` | Jing & Liu eq. (3)/(4); `"micro"` is what a naive loop produces |
| `min_sentence_length` | `0` (off) | Jing & Liu used 3, but it is corpus preparation, not the metric |
| `require_single_root` | `False` (off) | Futrell excludes them; destroys emtsv corpora if applied blind |
| `punct_tags` (CoNLL-U) | `{"PUNCT"}` | CoNLL-U has no `is_punct`; the tag is the only signal |
| `heuristic` (loan words) | `False` (off) | cannot tell a foreign word from a foreign name |
| `case_fold` (loan words) | `True` | **opposite of `lexical_diversity`** — a lexicon is dictionary forms, and matching it is the whole operation |
| `patterns` | `FOREIGN_PATTERNS` | substitutable; `th` alone changes the number a lot |

## 4. Needs a human call

**1. Should `th` ship in `FOREIGN_PATTERNS`?** It flags **Tóth, Horváth, Németh and
Kossuth** — among the commonest surnames in Hungary — because `th` survives in surnames as
an archaic spelling of plain *t*. It is a genuine marker in common nouns (*thriller*). Right
for common nouns, wrong for proper ones, and no spelling rule separates them. Found by a
Hypothesis property that claimed native-alphabet words never trip the heuristic; the claim
was false and the counter-example arrived in one draw. Mitigations: off by default,
`pos_tags` excludes proper nouns, `__repr__` warns, `patterns=` makes dropping it one line.

**2. ~~Which vocabulary counts as *idegen szó*?~~ Decided: Bakos.** The authority is Bakos
Ferenc, *Idegen szavak és kifejezések szótára* (Akadémiai Kiadó) — a word is an idegen szó
if Bakos lists it. The data made clear this could not be a rule: ranked by frequency the
"modern donor" stratum opens with every Latin month name plus `iskola`, `autó` and `pont`,
sitting beside `internet` and `regisztráció`. **Bakos is in copyright**, and in the EU its
headword selection carries database right, so it is used as a *criterion, never a source*:
`candidates.tsv` (2,506 rows, frequency-ordered) is adjudicated by hand and `decisions.tsv`
is the work product. **What remains is the adjudication itself**, plus how deep to take
it — the frequency distribution is Zipfian, so a few hundred entries cover most running
text, and `apply_decisions.py` reports what share of candidate token frequency the accepted
set carries.

**3. ~~Does a CC BY-SA asset belong in an MIT repository?~~ Resolved another way.** The
shipped list is no longer Wiktionary-derived at all. `experiments/loanwords/results/idegenszavak.txt`
holds **15,203 lemmas** selected by frequency rank from the MOKK Hungarian Webcorpus and
*verified* against Bakos. The corpus chooses, the dictionary checks, and Bakos is not
redistributed in whole or in part. Neither the scan nor the pipeline that reads it is in the
repository, and a full-history sweep confirms neither ever was.

The list is **not** inside `saphes.datasets`, and that is deliberate. Every other bundled
dataset regenerates from a script in this repository; this one cannot, because its generator
reads a copyrighted dictionary that is not here. A generated literal nobody can reproduce
would be worse than a file loaded explicitly, so `loanword_ratio` stays lexicon-agnostic and
`how-to/customise-the-loanword-lexicon.md` carries the one-line recipe.

**4. Should `parse_source` record the annotation *scheme*?** It records the *format*
(`conllu`/`spacy`). Whether preverbs attach to their verbs, Stanford vs content-head
coordination — each moves MDD across a whole corpus and is invisible in the score. Futrell
normalises his treebanks for this and says so; we never see the corpus. Written up in
`PRE-MORTEM.md`.

## 5. A correction to my own earlier claim

PR #4 originally reported that the three original modules had regressed from 37 mutation
survivors to 58, flagged as needing investigation. **That regression does not exist.**
`mutmut results` lists the 22 "no covering test" mutants alongside the survivors, and all 22
are in `segment.py`'s untested `punkt` branch; counting every line rather than only the
`: survived` ones inflates `segment` from 2 to 24. Measured correctly those modules stand at
**36** against the recorded **37**. `MUTATION-TESTING.md` is corrected, PR #4's body edited,
and the document now says how to count.

## 6. Mutation testing, and what it caught

Scoped to the five arithmetic modules. **1,245 mutants, ~89%**, and it earned its place —
every new module went in with a suite that looked complete and was not:

| module | non-string survivors, first pass → now |
|---|---|
| `syntax` (MDD) | 16 → 2 (both equivalent) |
| `syntax` (+MHD) | 32 → 4 (all equivalent) |
| `adapters` | 5 → 0 |
| `loanwords` | 10 → 0 |

Recurring classes, all invisible by inspection: **boundary values one step off a
comparison** (`total_distance < pairs` → `<=` would reject an ordinary all-adjacent
sentence; `len(content) < min_sentence_length` → `<=` would drop exactly the three-word
sentences Jing & Liu keep); **accumulators asserted on a single item**; and **a filter that
keeps the wrong half** — `require_single_root and sentence_roots != 1` → `== 1` survived
because the test asserted counts, which hold whichever sentence was dropped. *A count-only
assertion cannot tell a filter from its inverse.*

Two needed a shape of input the suite did not contain at all: `sum/len` → `sum*len` agrees
on one sentence, and the "an ancestor was punctuation" propagation only runs when several
uncached ancestors are walked in one pass, which needs a **head-final** tree. One find was
dead code rather than a gap — `.rstrip("\n")` after `splitlines()`, deleted.

## 7. Deliberately left alone

- **Dependency motifs** (Jing & Liu 2017). The plan made them conditional on PR #6 staying
  reviewable; it did not. On the README roadmap.
- **`syrupy`** was not added. The plan proposed it for the corpus comparison, but the
  disagreements worth pinning turned out to be specific and nameable — root counts,
  punctuation counts, which engine survives a filter — and explicit assertions say what they
  mean where a snapshot diff would not. One less dev dependency.
- **No lexicon is shipped**, and no generated literal exists under `src/`, because there is
  nothing to generate until decisions 2 and 3 are made.
- **`saphes.datasets.download()`** was not built. The package touches no network, no
  filesystem and no cache; `TestDependencyFreedom` enforces it and the tutorial promises it.
  The pipeline lives in `experiments/` instead, as `lix_calibration` does.
- **NER**. The spec asked for proper nouns to be ignored via NER. saphes cannot do NER and
  does not pretend to: `pos_tags` is supplied by the caller, like lemmas and sentence counts.
- **The five pre-existing lint errors under `experiments/`**, outside this work. `make ci`
  lints `src tests` only.
- **`main`**, and the pending PR #3 on `findings-reproducibility`. The stack is off `main`
  and independent of it.
