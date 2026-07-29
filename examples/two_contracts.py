"""The two metrics need opposite token streams — and what happens if you confuse them.

Run with:

    uv run python examples/two_contracts.py
"""

from saphes import lexical_diversity, lix, word_length
from saphes.datasets import Sample, load_english, load_greek, load_hungarian


def mean_length(words: list[str]) -> float:
    """Mean word length under the default NFC policy."""
    return sum(word_length(w) for w in words) / len(words)


def report(sample: Sample) -> None:
    """Print both metrics computed the right way and the wrong way."""
    surface = lexical_diversity(sample.forms, unit="surface", case_fold=True)
    lemma = lexical_diversity(sample.lemmas, unit="lemma", case_fold=True)

    correct_lix = lix(sample.forms, sentences=3)
    wrong_lix = lix(sample.lemmas, sentences=3)

    print(f"--- {sample.language} ({len(sample.pairs)} tokens) ---")
    print("  diversity   (wants LEMMAS)")
    print(f"    on lemmas   TTR = {lemma.ttr:.4f}   <- correct")
    print(f"    on surface  TTR = {surface.ttr:.4f}   <- inflated by morphology")
    print(f"    gap         {surface.ttr - lemma.ttr:+.4f}")
    print("  readability (wants SURFACE FORMS)")
    print(f"    on surface  LIX = {correct_lix.score:6.2f}  <- correct")
    print(f"    on lemmas   LIX = {wrong_lix.score:6.2f}  <- word length erased")
    print(f"    gap         {correct_lix.score - wrong_lix.score:+.2f}")
    print(
        f"    mean word length: {mean_length(sample.forms):.2f} surface"
        f" vs {mean_length(sample.lemmas):.2f} lemma"
    )
    print()


def main() -> None:
    print("Both mistakes are silent. No error, no NaN — just a plausible number.")
    print("The gap grows with the morphology of the language.")
    print()
    for sample in (load_english(), load_hungarian(), load_greek()):
        report(sample)

    print("What stops you making the mistake:")
    try:
        lexical_diversity(["a", "b"])  # type: ignore[call-arg]
    except TypeError as exc:
        print(f"  no unit           -> TypeError: {exc}")
    try:
        lexical_diversity("ház házak házban", unit="lemma")
    except TypeError as exc:
        print(f"  string as lemmas  -> TypeError: {str(exc)[:60]}...")
    try:
        lix(["some", "tokens"])
    except TypeError as exc:
        print(f"  tokens, no B      -> TypeError: {str(exc)[:60]}...")


if __name__ == "__main__":
    main()
