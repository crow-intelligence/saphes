# saphes

Readability and lexical diversity — two metrics, done carefully, with the parameters other
implementations hardcode.

*saphes* — σαφής, "clear, plain, distinct". Aristotle makes clarity the chief virtue of
λέξις (style); the other classical axis is ποικιλία, variety. The two metrics here are
exactly those axes: **LIX measures clarity, TTR measures variety.**

## Why this exists

`textstat`, `textdescriptives`, `lexicalrichness` and `taaled` already cover this ground.
Two reasons to still build it:

1. **The LIX long-word threshold is hardcoded at 6 everywhere.** That 6 comes from
   Björnsson's Swedish original. It is wrong for agglutinative and heavily inflected
   languages, where nearly every token counts as "long" and the index saturates into a flat
   line. Measured over the Hungarian Webcorpus — 493 million running tokens — **38.9% of
   tokens are longer than 6**, against a Germanic norm nearer 20–25%. Parameterising the
   threshold is the whole point.
2. **Implementations disagree.** They count words, sentences and long words differently, so
   they rank the same texts differently. Every function here returns the counts and the
   parameters alongside the score. See [Troubleshooting](troubleshooting.md) for a worked
   comparison against `textstat`.

## Core concepts

**The two metrics require opposite token streams.** This is the one thing to get right.

| Metric | Required input | Why |
|---|---|---|
| `lexical_diversity` | **lemmas** | Surface variation is *noise* — it measures morphology, not vocabulary. |
| `lix` | **surface forms** | Word length *is* the signal, and lemmatising erases it. |

Feed the same list to both and exactly one of them is silently wrong. See
[The two contracts](tutorials/two_contracts.md).

**Counts, not just scores.** A bare float is unauditable. Every result carries *A*, *B*, *C*
(or types and tokens), every parameter used, and the saphes version.

**Nothing is decided silently.** `unit` is required on `lexical_diversity`. A raw string is
refused where it could only produce the wrong kind of token. `LixResult.band` returns `None`
once the threshold moves off the value Björnsson's bands were calibrated at.

## Quick links

- [Quickstart](quickstart.md)
- [The two contracts](tutorials/two_contracts.md) — the asymmetry, and the guards against it
- [Threshold and saturation](tutorials/threshold_saturation.md) — why 6 is the wrong default
- [Troubleshooting](troubleshooting.md) — why your score differs from `textstat`
- [API reference](api/readability.md)

---

Made by [Crow Intelligence](https://crowintelligence.org/)
