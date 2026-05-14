"""Input path helpers: accepted extensions and safe reads."""

from __future__ import annotations

from pathlib import Path

from utils.error import CompilerError

# CLI and GUI accept plain text sources and C++ sources interchangeably.
SUPPORTED_SOURCE_SUFFIXES: frozenset[str] = frozenset({".txt", ".cpp"})


def validate_source_path(path: Path) -> None:
    suf = path.suffix.lower()
    if suf not in SUPPORTED_SOURCE_SUFFIXES:
        allowed = ", ".join(sorted(SUPPORTED_SOURCE_SUFFIXES))
        raise CompilerError(
            f"Unsupported input file type {path.suffix!r}. "
            f"Use one of: {allowed} (got: {path})."
        )


def read_source_file(path: Path, *, encoding: str = "utf-8") -> str:
    validate_source_path(path)
    return path.read_text(encoding=encoding)
