"""LIX: auditable counts, and what the long-word threshold actually does.

Run with:

    uv run python examples/lix_quickstart.py
"""

from saphes import interpret_lix, lix

ENGLISH = """The committee published its recommendations last week. Local authorities
must now review their existing procedures and report back within ninety days. Several
members expressed reservations about the proposed timetable, arguing that the
consultation period had been unreasonably short. The chairman acknowledged these
concerns but declined to extend the deadline."""

HUNGARIAN = """A bizottság a múlt héten nyilvánosságra hozta ajánlásait. A helyi
önkormányzatoknak felül kell vizsgálniuk a jelenlegi eljárásaikat, és kilencven napon
belül jelentést kell tenniük. Több tag fenntartásait fejezte ki a javasolt ütemtervvel
kapcsolatban, azzal érvelve, hogy a konzultációs időszak indokolatlanul rövid volt. Az
elnök tudomásul vette ezeket az aggályokat, de elutasította a határidő
meghosszabbítását."""


def show_counts() -> None:
    """A score is not enough: print the counts that produced it."""
    print("=== The counts travel with the score ===")
    result = lix(ENGLISH)
    print(f"  A (words)     = {result.words}")
    print(f"  B (sentences) = {result.sentences}   [{result.sentence_source}]")
    print(f"  C (long words)= {result.long_words}   [threshold {result.long_word_threshold}]")
    print(f"  LIX = A/B + 100*C/A = {result.avg_sentence_length:.2f}", end="")
    print(f" + {100 * result.long_word_share:.2f} = {result.score:.2f}")
    print(f"  band: {result.band}")
    print(f"  length policy: {result.length_policy}")
    print()


def show_sweep() -> None:
    """What the parameter does: it moves which words count as long."""
    print("=== Sweeping the threshold ===")
    print(f"  {'threshold':>9}  {'EN share':>9}  {'EN LIX':>7}  {'HU share':>9}  {'HU LIX':>7}")
    for threshold in (5, 6, 7, 8, 9, 10, 12):
        en = lix(ENGLISH, long_word_threshold=threshold)
        hu = lix(HUNGARIAN, long_word_threshold=threshold)
        print(
            f"  {threshold:>9}  {en.long_word_share:>8.1%}  {en.score:>7.2f}"
            f"  {hu.long_word_share:>8.1%}  {hu.score:>7.2f}"
        )
    print()
    print("  Two paragraphs cannot settle what threshold a language needs — that is")
    print("  a distributional question. Measured over the Hungarian Webcorpus (493M")
    print("  running tokens, 4% stratum), 38.9% of tokens are longer than 6, against")
    print("  a Germanic norm nearer 20-25%. Picking the threshold properly means")
    print("  matching those shares across languages, not eyeballing a sample.")
    print()


def show_bands() -> None:
    """Björnsson's bands are calibrated at threshold 6 and nowhere else."""
    print("=== Bands only mean anything at threshold 6 ===")
    tuned = lix(HUNGARIAN, long_word_threshold=9)
    print(f"  score at threshold 9: {tuned.score:.2f}")
    print(f"  band:                 {tuned.band}")
    print(f"  interpret_lix anyway: {interpret_lix(tuned.score)!r}")
    print("  Raising the threshold rescales the 100*C/A term by construction, so")
    print("  the score is no longer on the Swedish scale the labels were fitted to.")
    print()


def show_sentence_sources() -> None:
    """B has three sources, because real pipelines cannot always supply sentences."""
    print("=== Three ways to supply B ===")
    segmented = lix(ENGLISH)
    presegmented = lix(ENGLISH, sentences=["One sentence.", "And another."])
    explicit = lix(ENGLISH.split(), sentences=4)
    for label, result in (
        ("segmented", segmented),
        ("presegmented", presegmented),
        ("explicit", explicit),
    ):
        print(
            f"  {label:>13}: B={result.sentences}  LIX={result.score:6.2f}"
            f"  recorded as {result.sentence_source!r}"
        )
    print()
    print("  The explicit path is not a corner case. A treebank that drops")
    print("  punctuation, or a spaCy pipeline with the parser disabled, cannot give")
    print("  you sentences at all — and the result records which route was taken.")


def main() -> None:
    show_counts()
    show_sweep()
    show_bands()
    show_sentence_sources()


if __name__ == "__main__":
    main()
