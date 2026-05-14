"""Project-wide configuration constants."""

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
TESTS_DIR = BASE_DIR / "tests"

# Input source used by default when `main.py` is run without arguments.
DEFAULT_INPUT_FILE = TESTS_DIR / "test_for_loop.txt"
