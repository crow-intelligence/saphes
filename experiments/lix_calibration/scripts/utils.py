"""Shared utilities for the LIX calibration scripts."""

import sys
from datetime import UTC, datetime
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = EXPERIMENT_DIR / "data"
RESULTS_DIR = EXPERIMENT_DIR / "results"


def log(step: str, message: str) -> None:
    """Print a timestamped log line: [step] message.

    Flushed, because these scripts run for minutes and are usually watched
    through a redirect, where a buffered stdout shows nothing at all until the
    process exits.
    """
    ts = datetime.now(tz=UTC).strftime("%H:%M:%S")
    print(f"{ts} [{step}] {message}", flush=True)


def require_file(path: Path, hint: str) -> None:
    """Raise SystemExit with a helpful message if path does not exist.

    Args:
        path: File path to check.
        hint: Name of the script that should have created this file.
    """
    if not path.exists():
        log("error", f"Missing required file: {path}")
        log(
            "error",
            f"Run first: uv run python experiments/lix_calibration/scripts/{hint}",
        )
        sys.exit(1)


def fmt_share(share: float) -> str:
    """Format a proportion as a percentage string."""
    return f"{100 * share:.2f}%"
