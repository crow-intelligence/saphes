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

**Stem** — what an algorithmic suffix-stripper leaves behind. Not a lemma and usually not a
word: Snowball Hungarian turns `fánál` into `fá` and `adtam` into `adt`. Available as
`unit="stem"`, and comparable only to another stem count from the same stemmer. See
[Stemming is not lemmatisation](../explanation/stemming-is-not-lemmatisation.md).

**Length policy** — how a word's letters are counted. Defaults to `"nfc"`: normalise to NFC,
then count code points. Any callable works, and `hungarian_letter_count` is the one that
ships. See `word_length` in the [readability reference](readability.md).

**Digraph** — a letter written with two characters. Hungarian has `cs dz gy ly ny sz ty zs`,
plus the trigraph `dzs`. A character count is therefore not a letter count.

**Geminate** — a doubled letter, written short: long `sz` is spelled `ssz`, not `szsz`. Two
letters, three characters.

**Morpheme boundary** — the seam in a compound or derived word. It matters here because a
seam can put `z` next to `s` without them being the letter `zs`: `község` is `köz` + `ség`.
See [Count letters rather than characters](../how-to/count-letters-not-characters.md).

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

**Unit** — whether a token stream is `"lemma"`, `"surface"` or `"stem"`. Required on
`lexical_diversity`, recorded on every result. See
[The two token streams](../explanation/two-token-streams.md).
