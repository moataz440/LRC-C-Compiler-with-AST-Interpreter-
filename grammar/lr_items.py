from __future__ import annotations

from collections import deque


Item = tuple[str, tuple[str, ...], int]


def closure(items: set[Item], grammar: dict[str, list[list[str]]], terminals: set[str]) -> frozenset[Item]:
    result = set(items)
    changed = True
    while changed:
        changed = False
        for lhs, rhs, dot in list(result):
            if dot >= len(rhs):
                continue
            sym = rhs[dot]
            if sym in terminals or sym not in grammar:
                continue
            for prod in grammar[sym]:
                candidate = (sym, tuple(prod), 0)
                if candidate not in result:
                    result.add(candidate)
                    changed = True
    return frozenset(result)


def goto(
    state: frozenset[Item], symbol: str, grammar: dict[str, list[list[str]]], terminals: set[str]
) -> frozenset[Item]:
    shifted: set[Item] = set()
    for lhs, rhs, dot in state:
        if dot < len(rhs) and rhs[dot] == symbol:
            shifted.add((lhs, rhs, dot + 1))
    if not shifted:
        return frozenset()
    return closure(shifted, grammar, terminals)


def canonical_collection(
    grammar: dict[str, list[list[str]]], start_symbol: str, terminals: set[str]
) -> tuple[list[frozenset[Item]], dict[tuple[int, str], int]]:
    augmented_start = f"{start_symbol}'"
    initial = closure({(augmented_start, (start_symbol,), 0)}, grammar, terminals)
    states: list[frozenset[Item]] = [initial]
    transitions: dict[tuple[int, str], int] = {}
    queue = deque([0])

    while queue:
        i = queue.popleft()
        state = states[i]
        symbols = {rhs[dot] for lhs, rhs, dot in state if dot < len(rhs)}
        for sym in symbols:
            target = goto(state, sym, grammar, terminals)
            if not target:
                continue
            if target not in states:
                states.append(target)
                queue.append(len(states) - 1)
            transitions[(i, sym)] = states.index(target)
    return states, transitions
