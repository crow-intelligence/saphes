"""Step 1: Download the frequency lists (and optionally one corpus part).

All downloads are cached to data/ — safe to re-run. Files are streamed in chunks
rather than read whole, because the full Hungarian frequency list is 115 MB and
the corpus part is ~370 MB.

Usage:
    uv run python experiments/lix_calibration/scripts/download_data.py --smoke-test
    uv run python experiments/lix_calibration/scripts/download_data.py
    uv run python experiments/lix_calibration/scripts/download_data.py --with-corpus-part
"""

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utils import DATA_DIR, log  # noqa: E402

MOKK_FREQ = "ftp://ftp.mokk.bme.hu/Language/Hungarian/Freq/Web2.2/"
MOKK_TOP100K = MOKK_FREQ + "web2.2-freq-sorted.top100k.txt"
MOKK_FULL = MOKK_FREQ + "web2.2-freq-sorted.txt.gz"
MOKK_CORPUS_PART = (
    "ftp://ftp.mokk.bme.hu/Language/Hungarian/Crawl/Web2/web2-4p-0.tar.gz"
)
LEIPZIG = "https://downloads.wortschatz-leipzig.de/corpora/{code}_news_2022_1M.tar.gz"

# Sizes verified against the servers. The smoke file is asserted exactly; a
# mismatch means the resource moved and the whole study is reading something
# other than what it claims to.
EXPECTED_SIZES = {
    "web2.2-freq-sorted.top100k.txt": 2_814_390,
    "web2.2-freq-sorted.txt.gz": 120_512_445,
}

CHUNK = 1 << 20  # 1 MiB
MANIFEST = "manifest.json"


def download(url: str, dest: Path, *, expected_size: int | None = None) -> None:
    """Stream ``url`` to ``dest``, skipping if already present."""
    if dest.exists():
        log("download", f"Already cached ({dest.stat().st_size:,} bytes) → {dest}")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    log("download", f"Fetching {url}")

    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(url, timeout=120) as resp, open(  # noqa: S310
            tmp, "wb"
        ) as out:
            while chunk := resp.read(CHUNK):
                out.write(chunk)
                digest.update(chunk)
                total += len(chunk)
                if total % (16 * CHUNK) == 0:
                    log("download", f"  {total:,} bytes...")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        tmp.unlink(missing_ok=True)
        log("download", f"FAILED: {exc}")
        log("download", f"Place the file manually at {dest} and re-run.")
        sys.exit(1)

    if expected_size is not None and total != expected_size:
        tmp.unlink(missing_ok=True)
        log(
            "download",
            f"FAILED: expected {expected_size:,} bytes, got {total:,}. "
            "The resource has changed; do not proceed without checking why.",
        )
        sys.exit(1)

    tmp.rename(dest)
    log("download", f"{total:,} bytes, sha256={digest.hexdigest()[:16]}… → {dest}")
    _record(dest, total, digest.hexdigest(), url)


def _record(dest: Path, size: int, sha256: str, url: str) -> None:
    """Append provenance for a downloaded file to the manifest."""
    path = DATA_DIR / MANIFEST
    manifest = json.loads(path.read_text()) if path.exists() else {}
    manifest[dest.name] = {"url": url, "bytes": size, "sha256": sha256}
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


def main() -> None:
    """Download whatever the requested run needs."""
    parser = argparse.ArgumentParser(description="Download calibration corpora")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Fetch only the 2.8 MB top100k list and the Leipzig pair",
    )
    parser.add_argument(
        "--with-corpus-part",
        action="store_true",
        help="Also fetch one ~370 MB Webcorpus part, for sentence-count validation",
    )
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    name = Path(MOKK_TOP100K).name
    download(MOKK_TOP100K, DATA_DIR / name, expected_size=EXPECTED_SIZES[name])

    for code in ("swe", "hun"):
        url = LEIPZIG.format(code=code)
        download(url, DATA_DIR / Path(url).name)

    if not args.smoke_test:
        name = Path(MOKK_FULL).name
        download(MOKK_FULL, DATA_DIR / name, expected_size=EXPECTED_SIZES[name])

    if args.with_corpus_part:
        download(MOKK_CORPUS_PART, DATA_DIR / Path(MOKK_CORPUS_PART).name)

    log("download", f"Done. Manifest → {DATA_DIR / MANIFEST}")


if __name__ == "__main__":
    main()
