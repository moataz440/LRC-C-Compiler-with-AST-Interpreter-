from __future__ import annotations

from collections import deque

from grammar.first_follow import EPS, compute_first


LR1Item = tuple[str, tuple[str, ...], int, str]  # (lhs, rhs, dot, lookahead)


def _first_of_sequence(
    sequence: list[str],
    first: dict[str, set[str]],
    terminals: set[str],
) -> set[str]:
    if not sequence:
        return {EPS}
    result: set[str] = set()
    add_eps = True
    for sym in sequence:
        if sym in terminals:
            result.add(sym)
            add_eps = False
            break
        result.update(first[sym] - {EPS})
        if EPS not in first[sym]:
            add_eps = False
            break
    if add_eps:
        result.add(EPS)
    return result


def closure(
    items: set[LR1Item],
    grammar: dict[str, list[list[str]]],
    terminals: set[str],
    first: dict[str, set[str]],
) -> frozenset[LR1Item]:
    result: set[LR1Item] = set(items)
    changed = True
    while changed:
        changed = False
        for lhs, rhs, dot, la in list(result):
            if dot >= len(rhs):
                continue
            sym = rhs[dot]
            if sym in terminals or sym not in grammar:
                continue

            beta = list(rhs[dot + 1 :]) + [la]
            lookaheads = _first_of_sequence(beta, first, terminals) - {EPS}
            for prod in grammar[sym]:
                for b in lookaheads:
                    candidate = (sym, tuple(prod), 0, b)
                    if candidate not in result:
                        result.add(candidate)
                        changed = True
    return frozenset(result)


def goto(
    state: frozenset[LR1Item],
    symbol: str,
    grammar: dict[str, list[list[str]]],
    terminals: set[str],
    first: dict[str, set[str]],
) -> frozenset[LR1Item]:
    shifted: set[LR1Item] = set()
    for lhs, rhs, dot, la in state:
        if dot < len(rhs) and rhs[dot] == symbol:
            shifted.add((lhs, rhs, dot + 1, la))
    if not shifted:
        return frozenset()
    return closure(shifted, grammar, terminals, first)


def canonical_collection_lr1(
    grammar: dict[str, list[list[str]]],
    start_symbol: str,
    terminals: set[str],
) -> tuple[list[frozenset[LR1Item]], dict[tuple[int, str], int]]:
    augmented_start = f"{start_symbol}'"

    first = compute_first(grammar, terminals)
    initial = closure({(augmented_start, (start_symbol,), 0, "EOF")}, grammar, terminals, first)
    states: list[frozenset[LR1Item]] = [initial]
    transitions: dict[tuple[int, str], int] = {}
    queue = deque([0])

    while queue:
        i = queue.popleft()
        state = states[i]
        symbols = {rhs[dot] for _lhs, rhs, dot, _la in state if dot < len(rhs)}
        for sym in symbols:
            target = goto(state, sym, grammar, terminals, first)
            if not target:
                continue
            if target not in states:
                states.append(target)
                queue.append(len(states) - 1)
            transitions[(i, sym)] = states.index(target)

    return states, transitions

