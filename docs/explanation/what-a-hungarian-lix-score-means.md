# What a Hungarian LIX score means

Calibrating the threshold bought a number that is comparable between Hungarian texts. It did
not buy a number anyone could read. At `long_word_threshold=8` a Hungarian LIX of 43 was not
on Björnsson's scale, so `LixResult.band` returned `None`, and the study ended with a figure
and no interpretation.

This is how the labels were carried across, and what the result does and does not claim.

## Retuning the threshold could never have been enough

LIX is `A/B + 100·C/A`: mean sentence length, plus the share of long words. The threshold
calibration acts on the **second** term only. It says nothing about the first.

And the first term differs between the two languages on its own account. Measured on a
million sentences of news from each, under the same pipeline:

| | words per sentence | long-word share | LIX |
|---|---:|---:|---:|
| Swedish, threshold 6 | 15.37 | 27.07% | 42.44 |
| Hungarian, threshold 8, letters | 18.30 | 23.81% | 42.11 |

Hungarian news writes sentences about three words longer. So even with the second term matched
exactly, a Hungarian score would sit above a Swedish one for prose of the same kind — and the
threshold calibration has no way to know that, because a frequency list has no sentences in it.

That is the gap the bands have to absorb, and it is why the answer could not be read off the
threshold study.

## The same argument, one level up

The threshold was found by equipercentile matching: the Hungarian threshold whose long-word
share equals the share Björnsson's 6 picks out in Swedish. The bands are found the same way.
For each Swedish boundary, measure what fraction of running Swedish text falls below it, then
read off the Hungarian score with that same fraction below it.

A mapped band therefore holds **the share of running text its Swedish original held**. That is
a real, checkable property, and it is the whole of the claim.

| Swedish boundary | `hu-letters` | shift |
|---:|---:|---:|
| 30 | 32.63 | +2.63 |
| 40 | 40.18 | +0.18 |
| 50 | 48.19 | −1.81 |
| 60 | *not placed* | — |

Under the character policy the same boundaries land at 35.45, 42.95 and 51.16 — further out,
and for a reason that follows from the table above. Counting letters rather than characters
brings the Hungarian long-word share down closer to the Swedish one, which leaves less for the
bands to absorb.

## What it does not claim

**Nobody checked whether Hungarian readers find these texts correspondingly hard.** That would
need a corpus graded by difficulty, and there is not one here. The mapping is a statement about
distributions of text, not about readers. It is the same species of claim as the threshold, and
it is worth being explicit that neither is a validation against comprehension.

**The top boundary is not published.** Swedish news puts about 0.04% of its text above LIX 60,
so that boundary is read off five windows out of twelve thousand. It is not that Hungarian
misbehaves up there; it is that the reference corpus has almost nothing up there to map from. A
corpus of harder writing would place it. So above the `standard` band, `interpret` returns
`None`, and the honest reading is "harder than ordinary news, and this study cannot say how
much".

**The reference is news.** Both sides are 2022 newswire. A mapping built from literary prose or
from legal writing would land somewhere else, and the register panel below is the check on how
much that matters.

## What the index can and cannot separate

Four Hungarian registers, all at threshold 8 with the letter count:

| register | words per sentence | LIX | band |
|---|---:|---:|---|
| song lyrics | 17.56 | 23.56 | `very easy` |
| parliamentary speech | 18.21 | 41.09 | `standard` |
| news | 18.30 | 42.11 | `standard` |
| investigative journalism | 22.63 | 46.71 | `standard` |

Lyrics separate cleanly. The three prose registers do not: they sit within six points of one
another and all land in the same band, even though one is spoken oratory and another is dense
investigative writing about public procurement.

That is worth knowing before reaching for LIX. It distinguishes **prose from non-prose**
robustly, and it ranks prose registers in a sensible order — but the spread between them is
small enough that a difference of a few points between two Hungarian corpora is not, on its
own, evidence of anything.

## See also

- [Why the threshold moves](why-the-threshold-moves.md) — the first half of this argument.
- [LIX bands](../reference/lix-bands.md) — the mapped table, and the supporting counts.
- [Use a calibrated threshold](../how-to/use-a-calibrated-threshold.md) — how to ask for a
  label.
- `experiments/lix_registers/` — the measurement, including the window-length ladder each
  boundary was checked against.
