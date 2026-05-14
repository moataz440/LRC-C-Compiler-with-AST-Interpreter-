from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreprocessorDirective:
    kind: str
    raw: str
    line: int
    args: str = ""

    def to_dict(self) -> dict:
        return {"kind": self.kind, "raw": self.raw, "line": self.line, "args": self.args}


@dataclass(frozen=True)
class PreprocessResult:
    directives: list[PreprocessorDirective]
    output_source: str
    macros: dict[str, str | None]
    includes: list[str]           # NEW: list of included headers

    def to_dict(self) -> dict:
        return {
            "directives": [d.to_dict() for d in self.directives],
            "macros": dict(self.macros),
            "includes": list(self.includes),
        }


class Preprocessor:
    """Processes #lines and optionally applies simple conditional compilation."""

    # Known headers that are required for certain identifiers
    _HEADER_PROVIDES: dict[str, set[str]] = {
        "iostream": {"cout", "cin", "endl"},
        "string":   {"string"},
        "cmath":    {"sqrt", "pow", "abs"},
        "cstdlib":  {"exit", "rand", "srand"},
    }

    def __init__(self) -> None:
        self._macros: dict[str, str | None] = {}
        self._directives: list[PreprocessorDirective] = []
        self._includes: list[str] = []

        # Conditional compilation stack.
        self._cond_stack: list[tuple[bool, bool, bool]] = []

    def run(self, source: str) -> PreprocessResult:
        self._macros = {}
        self._directives = []
        self._includes = []
        self._cond_stack = []

        out_lines: list[str] = []
        for idx, raw_line in enumerate(source.splitlines(True), start=1):
            stripped = raw_line.lstrip()
            if stripped.startswith("#"):
                directive = self._parse_directive(stripped, idx)
                self._directives.append(directive)
                self._apply_directive(directive)
                out_lines.append("\n" if raw_line.endswith("\n") else "")
                continue

            if self._is_active():
                out_lines.append(raw_line)
            else:
                out_lines.append("\n" if raw_line.endswith("\n") else "")

        return PreprocessResult(
            directives=list(self._directives),
            output_source="".join(out_lines),
            macros=dict(self._macros),
            includes=list(self._includes),
        )

    def _is_active(self) -> bool:
        if not self._cond_stack:
            return True
        return self._cond_stack[-1][0] and self._cond_stack[-1][1]

    def _parse_directive(self, stripped_hash_line: str, line_no: int) -> PreprocessorDirective:
        raw = stripped_hash_line.rstrip("\r\n")
        content_str = raw[1:].strip()
        if not content_str:
            return PreprocessorDirective(kind="unknown", raw=raw, line=line_no, args="")
        parts = content_str.split(None, 1)
        name = parts[0]
        args = parts[1] if len(parts) > 1 else ""
        # Handle #include<header> with no space (name becomes "include<header>")
        if name.startswith("include") and name != "include":
            args = name[len("include"):].strip()
            name = "include"
        return PreprocessorDirective(kind=name, raw=raw, line=line_no, args=args)

    def _apply_directive(self, d: PreprocessorDirective) -> None:
        kind = d.kind
        args = d.args.strip()

        if kind == "include":
            # Extract header name from <...> or "..." (with or without space after #include)
            raw_args = args.strip()
            if raw_args.startswith("<") and ">" in raw_args:
                header = raw_args[1:raw_args.index(">")]
            elif raw_args.startswith('"') and raw_args.endswith('"'):
                header = raw_args[1:-1]
            else:
                header = raw_args.strip("<>\"' \t")
            # strip .h suffix for lookup
            header_key = header[:-2] if header.endswith(".h") else header
            if header_key not in self._includes:
                self._includes.append(header_key)
            return

        if kind == "define":
            if not args:
                return
            name, value = (args.split(None, 1) + [""])[:2]
            self._macros[name] = value if value != "" else None
            return

        if kind == "undef":
            if args:
                self._macros.pop(args.split(None, 1)[0], None)
            return

        if kind in {"ifdef", "ifndef"}:
            name = args.split(None, 1)[0] if args else ""
            cond = (name in self._macros) if kind == "ifdef" else (name not in self._macros)
            parent_active = self._is_active()
            this_active = parent_active and cond
            any_taken = this_active
            self._cond_stack.append((parent_active, this_active, any_taken))
            return

        if kind == "else":
            if not self._cond_stack:
                return
            parent_active, _this_active, any_taken = self._cond_stack.pop()
            new_this = parent_active and (not any_taken)
            self._cond_stack.append((parent_active, new_this, True))
            return

        if kind == "elif":
            if not self._cond_stack:
                return
            parent_active, _this_active, any_taken = self._cond_stack.pop()
            cond = False
            if args.startswith("defined"):
                inside = args[len("defined"):].strip()
                inside = inside.strip("() \t")
                if inside:
                    cond = inside in self._macros
            else:
                name = args.split(None, 1)[0] if args else ""
                cond = name in self._macros if name else False
            new_this = parent_active and (not any_taken) and cond
            self._cond_stack.append((parent_active, new_this, any_taken or new_this))
            return

        if kind == "endif":
            if self._cond_stack:
                self._cond_stack.pop()
            return

        return

    def get_includes(self) -> list[str]:
        return list(self._includes)
