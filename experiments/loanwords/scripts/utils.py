"""Shared paths and logging for the loan-word study."""

import sys
import time
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = EXPERIMENT_DIR / "data"
RESULTS_DIR = EXPERIMENT_DIR / "results"


def log(step: str, message: str) -> None:
    """Print a timestamped progress line."""
    stamp = time.strftime("%H:%M:%S")
    print(f"[{stamp}] {step}: {message}", flush=True)


def require_file(path: Path, hint: str) -> None:
    """Exit with a usable instruction if a prerequisite file is missing."""
    if not path.exists():
        log("input", f"Missing {path}")
        log("input", f"Run first: uv run python experiments/loanwords/scripts/{hint}")
        sys.exit(1)
