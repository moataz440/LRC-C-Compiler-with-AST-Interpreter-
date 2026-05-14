from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    var_type: str
    scope_name: str        # e.g. "global", "main", "for_loop"
    scope_level: int       # 0 = global, 1 = function, 2+ = nested
    line: int | None = None
    is_array: bool = False
    array_size: int | None = None
    init_value: str | None = None   # string representation of initializer if present
    is_param: bool = False
    final_value: str | None = None  # runtime final value (set after execution)

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "type":        self.var_type,
            "scope_name":  self.scope_name,
            "scope_level": self.scope_level,
            "line":        self.line,
            "is_array":    self.is_array,
            "array_size":  self.array_size,
            "init_value":  self.init_value,
            "is_param":    self.is_param,
            "final_value": self.final_value,
        }


class SymbolTable:
    def __init__(self) -> None:
        # Active scopes for semantic checking (name → type string)
        self._scopes: list[dict[str, str]] = [{}]
        self._scope_names: list[str] = ["global"]

        # Permanent record of all symbols ever declared (for display)
        self._all_symbols: list[Symbol] = []

    # ── Scope management ───────────────────────────────────────────────

    def push_scope(self, name: str = "block") -> None:
        self._scopes.append({})
        self._scope_names.append(name)

    def pop_scope(self) -> None:
        if len(self._scopes) <= 1:
            return
        self._scopes.pop()
        self._scope_names.pop()

    def current_scope_level(self) -> int:
        return len(self._scopes) - 1

    def current_scope_name(self) -> str:
        return self._scope_names[-1]

    # ── Declaration ────────────────────────────────────────────────────

    def declare(
        self,
        name: str,
        var_type: str,
        *,
        line: int | None = None,
        is_array: bool = False,
        array_size: int | None = None,
        init_value: str | None = None,
        is_param: bool = False,
    ) -> None:
        self._scopes[-1][name] = var_type
        sym = Symbol(
            name=name,
            var_type=var_type,
            scope_name=self._scope_names[-1],
            scope_level=self.current_scope_level(),
            line=line,
            is_array=is_array,
            array_size=array_size,
            init_value=init_value,
            is_param=is_param,
        )
        self._all_symbols.append(sym)

    # ── Lookup ─────────────────────────────────────────────────────────

    def exists(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self._scopes))

    def exists_in_current_scope(self, name: str) -> bool:
        return name in self._scopes[-1]

    def get(self, name: str) -> str:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise KeyError(name)

    # ── Final value update ─────────────────────────────────────────────

    def update_final_values(self, all_vars: dict) -> None:
        """After the interpreter runs, populate final_value on each symbol."""
        for sym in self._all_symbols:
            if sym.name in all_vars:
                v = all_vars[sym.name]
                if isinstance(v, list):
                    sym.final_value = "{" + ", ".join(str(x) for x in v) + "}"
                elif v is None:
                    sym.final_value = None
                else:
                    sym.final_value = str(v)

    # ── Export ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, str]:
        """Merged flat dict (for backward compat)."""
        merged: dict[str, str] = {}
        for scope in self._scopes:
            merged.update(scope)
        return merged

    def scopes(self) -> list[dict[str, str]]:
        return [dict(s) for s in self._scopes]

    def all_symbols(self) -> list[dict]:
        """All symbols ever declared, in declaration order."""
        return [s.to_dict() for s in self._all_symbols]
