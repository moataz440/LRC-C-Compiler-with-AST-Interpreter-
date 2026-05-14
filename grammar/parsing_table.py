from __future__ import annotations

from grammar.first_follow import compute_first, compute_follow
from grammar.lr_items import canonical_collection
from utils.error import CompilerError


def parse_grammar_file(path: str) -> tuple[dict[str, list[list[str]]], str]:
    grammar: dict[str, list[list[str]]] = {}
    start_symbol = ""
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lhs, rhs = [part.strip() for part in line.split("->")]
            alternatives = []
            for alt in rhs.split("|"):
                symbols = alt.strip().split()
                alternatives.append([] if symbols == ["eps"] else symbols)
            grammar.setdefault(lhs, []).extend(alternatives)
            if not start_symbol:
                start_symbol = lhs
    if not start_symbol:
        raise CompilerError("Grammar file is empty.")
    return grammar, start_symbol


def build_slr_table(grammar: dict[str, list[list[str]]], start_symbol: str) -> dict:
    non_terminals = set(grammar.keys())
    all_rhs_symbols = {sym for prods in grammar.values() for prod in prods for sym in prod if sym != "eps"}
    terminals = all_rhs_symbols - non_terminals
    terminals.add("EOF")

    augmented_start = f"{start_symbol}'"
    grammar_aug = dict(grammar)
    grammar_aug[augmented_start] = [[start_symbol]]

    first = compute_first(grammar_aug, terminals)
    follow = compute_follow(grammar_aug, start_symbol, terminals, first)

    states, transitions = canonical_collection(grammar_aug, start_symbol, terminals)

    productions: list[tuple[str, list[str]]] = []
    for lhs, prods in grammar_aug.items():
        for prod in prods:
            productions.append((lhs, prod))

    action: dict[tuple[int, str], tuple[str, int | tuple[str, list[str]] | None]] = {}
    goto_tbl: dict[tuple[int, str], int] = {}

    for i, state in enumerate(states):
        for lhs, rhs_tuple, dot in state:
            rhs = list(rhs_tuple)
            if dot < len(rhs):
                symbol = rhs[dot]
                if symbol in terminals:
                    j = transitions.get((i, symbol))
                    if j is not None:
                        _set_table(action, (i, symbol), ("shift", j))
                else:
                    j = transitions.get((i, symbol))
                    if j is not None:
                        goto_tbl[(i, symbol)] = j
            else:
                if lhs == augmented_start:
                    _set_table(action, (i, "EOF"), ("accept", None))
                else:
                    prod = (lhs, rhs)
                    for term in follow[lhs]:
                        _set_table(action, (i, term), ("reduce", prod))

    return {
        "action": action,
        "goto": goto_tbl,
        "productions": productions,
        "terminals": terminals,
        "non_terminals": non_terminals,
        "start_symbol": start_symbol,
    }


def _set_table(table: dict, key: tuple, value: tuple) -> None:
    existing = table.get(key)
    if existing is not None and existing != value:
        raise CompilerError(f"Grammar is not SLR(1): conflict at {key} -> {existing} vs {value}")
    table[key] = value
