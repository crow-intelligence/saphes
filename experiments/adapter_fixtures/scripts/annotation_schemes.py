"""Reproduce the worked examples in `../annotation-schemes.txt`.

Two sentences, each annotated twice by two accepted conventions, showing that
mean dependency distance depends on the annotation scheme and not only on the
text. Nothing here is asserted by hand; run it and the numbers in the explainer
come out.

Usage:
    uv run python experiments/adapter_fixtures/scripts/annotation_schemes.py
"""

from saphes import DepToken, dependency_distances, mean_dependency_distance


def show(title: str, note: str, tokens: list[DepToken], words: list[str]) -> float:
    """Print one annotation of one sentence, and return its MDD."""
    print(f"  {title}")
    print(f"    {note}")
    for token, word in zip(tokens, words, strict=True):
        head = words[token.head - 1] if token.head else "ROOT"
        gap = "" if token.head == 0 else f"  distance {abs(token.index - token.head)}"
        print(f"      {token.index}. {word:<10} -> {head}{gap}")
    distances = dependency_distances(tokens)
    result = mean_dependency_distance([tokens])
    print(f"    distances {distances}  sum {sum(distances)}  pairs {len(distances)}")
    print(f"    MDD = {sum(distances)}/{len(distances)} = {result.mdd:.3f}\n")
    return result.mdd


def main() -> None:
    """Print both worked examples."""
    print("=" * 78)
    print("EXAMPLE 1 — coordination: 'János és Mária tegnap moziba ment'")
    print("=" * 78)
    words = ["János", "és", "Mária", "tegnap", "moziba", "ment"]
    first = show(
        "Scheme A — Stanford/UD style: the FIRST CONJUNCT heads the phrase",
        "'és' and 'Mária' hang off 'János'; 'János' is the subject of 'ment'.",
        [
            DepToken(1, 6, False, "PROPN"),
            DepToken(2, 3, False, "CCONJ"),
            DepToken(3, 1, False, "PROPN"),
            DepToken(4, 6, False, "ADV"),
            DepToken(5, 6, False, "NOUN"),
            DepToken(6, 0, False, "VERB"),
        ],
        words,
    )
    second = show(
        "Scheme B — Prague style: the CONJUNCTION heads the phrase",
        "both names hang off 'és'; 'és' is the subject of 'ment'.",
        [
            DepToken(1, 2, False, "PROPN"),
            DepToken(2, 6, False, "CCONJ"),
            DepToken(3, 2, False, "PROPN"),
            DepToken(4, 6, False, "ADV"),
            DepToken(5, 6, False, "NOUN"),
            DepToken(6, 0, False, "VERB"),
        ],
        words,
    )
    gap = abs(first - second) / min(first, second) * 100
    print(f"  >>> {first:.3f} against {second:.3f} — {gap:.0f}% apart\n")

    print("=" * 78)
    print("EXAMPLE 2 — postpositions: 'a fiú az asztal alatt aludt'")
    print("=" * 78)
    words = ["a", "fiú", "az", "asztal", "alatt", "aludt"]
    first = show(
        "Scheme A — UD: the NOUN heads, the postposition is a 'case' marker",
        "'alatt' attaches down to 'asztal'; 'asztal' attaches to the verb.",
        [
            DepToken(1, 2, False, "DET"),
            DepToken(2, 6, False, "NOUN"),
            DepToken(3, 4, False, "DET"),
            DepToken(4, 6, False, "NOUN"),
            DepToken(5, 4, False, "ADP"),
            DepToken(6, 0, False, "VERB"),
        ],
        words,
    )
    second = show(
        "Scheme B — older style: the POSTPOSITION heads its phrase",
        "'asztal' attaches up to 'alatt'; 'alatt' attaches to the verb.",
        [
            DepToken(1, 2, False, "DET"),
            DepToken(2, 6, False, "NOUN"),
            DepToken(3, 4, False, "DET"),
            DepToken(4, 5, False, "NOUN"),
            DepToken(5, 6, False, "ADP"),
            DepToken(6, 0, False, "VERB"),
        ],
        words,
    )
    gap = abs(first - second) / min(first, second) * 100
    print(f"  >>> {first:.3f} against {second:.3f} — {gap:.0f}% apart")


if __name__ == "__main__":
    main()
