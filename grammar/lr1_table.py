from __future__ import annotations

from grammar.lr1_items import canonical_collection_lr1
from utils.error import CompilerError


def build_lr1_table(grammar: dict[str, list[list[str]]], start_symbol: str) -> dict:
    non_terminals = set(grammar.keys())
    all_rhs_symbols = {sym for prods in grammar.values() for prod in prods for sym in prod if sym != "eps"}
    terminals = all_rhs_symbols - non_terminals
    terminals.add("EOF")

    augmented_start = f"{start_symbol}'"
    grammar_aug = dict(grammar)
    grammar_aug[augmented_start] = [[start_symbol]]

    states, transitions = canonical_collection_lr1(grammar_aug, start_symbol, terminals)

    action: dict[tuple[int, str], tuple[str, int | tuple[str, list[str]] | None]] = {}
    goto_tbl: dict[tuple[int, str], int] = {}

    for i, state in enumerate(states):
        for lhs, rhs_tuple, dot, la in state:
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
                if lhs == augmented_start and la == "EOF":
                    _set_table(action, (i, "EOF"), ("accept", None))
                elif lhs != augmented_start:
                    prod = (lhs, rhs)
                    _set_table(action, (i, la), ("reduce", prod))

    return {
        "action": action,
        "goto": goto_tbl,
        "terminals": terminals,
        "non_terminals": non_terminals,
        "start_symbol": start_symbol,
        "kind": "LR(1)",
    }


def _set_table(table: dict, key: tuple, value: tuple) -> None:
    existing = table.get(key)
    if existing is not None and existing != value:
        # Resolve shift/reduce conflict in favour of shift (standard dangling-else resolution).
        # This is the correct behaviour for C++ where 'else' binds to the nearest 'if'.
        existing_kind = existing[0]
        new_kind = value[0]
        if new_kind == "shift" and existing_kind == "reduce":
            table[key] = value  # prefer shift
            return
        if new_kind == "reduce" and existing_kind == "shift":
            return  # keep existing shift
        raise CompilerError(f"Grammar is not LR(1): unresolvable conflict at {key} -> {existing} vs {value}")
    table[key] = value

