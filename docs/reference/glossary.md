# Glossary

**A** — the number of words in a text. The first LIX term is *A/B*.

**B** — the number of sentences. See
[Supply a sentence count](../how-to/supply-a-sentence-count.md); many pipelines cannot
produce one.

**C** — the number of long words, i.e. words longer than `long_word_threshold`.

**Band** — a plain-language label for a LIX score (`very easy` … `very difficult`). Valid
only at threshold 6. See [LIX bands](lix-bands.md).

**Equipercentile matching** — choosing a threshold for one language so that it selects the
same *share* of running words that the reference threshold selects in another. What
`match_threshold` does.

**Lemma** — the dictionary form of a word. `houses`, `housing` and `housed` share the lemma
`house`. The stream `lexical_diversity` wants.

**Length policy** — how a word's letters are counted. Defaults to `"nfc"`: normalise to NFC,
then count code points. See `word_length` in the [readability reference](readability.md).

**LIX** — *Läsbarhetsindex*, Björnsson's readability index: `A/B + 100·C/A`.

**Long word** — a word whose length is **strictly greater than** the threshold. The default
of 6 therefore means seven letters or more.

**MATTR** — Moving-Average Type–Token Ratio. The mean TTR over every window-length span,
approximately independent of total length and therefore comparable between texts of different
sizes, unlike TTR.

**RIX** — Anderson's simplification of LIX: long words per sentence, *C/B*. No interpretation
bands ship for it.

**Stratum** — a nested sub-sample of the Hungarian Webcorpus with a known error rate. The
calibration uses the 4% stratum, which has fewer mistakes than an average print document.

**Surface form** — a word as it actually appears in the text, inflection and all. The stream
`lix` wants.

**Token** — one occurrence of a word. "the cat sat on the mat" is six tokens.

**Token-weighted** — counting each word as many times as it occurs in running text, rather
than once per distinct word. The correct weighting for a length distribution, since rare
types are long.

**TTR** — Type–Token Ratio, distinct tokens over total tokens. Falls as a text grows, so it
is **not** comparable between texts of different lengths.

**Type** — one distinct word. "the cat sat on the mat" is five types.

**Type-weighted** — counting each distinct word once, regardless of frequency. The most
likely silent error in a calibration study.

**Unit** — whether a token stream is `"lemma"` or `"surface"`. Required on
`lexical_diversity`, recorded on every result. See
[The two token streams](../explanation/two-token-streams.md).
