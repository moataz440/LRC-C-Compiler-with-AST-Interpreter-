from __future__ import annotations


EPS = "eps"


def compute_first(grammar: dict[str, list[list[str]]], terminals: set[str]) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {nt: set() for nt in grammar}
    changed = True
    while changed:
        changed = False
        for nt, productions in grammar.items():
            for prod in productions:
                if not prod:
                    if EPS not in first[nt]:
                        first[nt].add(EPS)
                        changed = True
                    continue
                add_eps = True
                for sym in prod:
                    if sym in terminals:
                        if sym not in first[nt]:
                            first[nt].add(sym)
                            changed = True
                        add_eps = False
                        break
                    before = len(first[nt])
                    first[nt].update(first[sym] - {EPS})
                    if len(first[nt]) != before:
                        changed = True
                    if EPS not in first[sym]:
                        add_eps = False
                        break
                if add_eps and EPS not in first[nt]:
                    first[nt].add(EPS)
                    changed = True
    return first


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


def compute_follow(
    grammar: dict[str, list[list[str]]],
    start_symbol: str,
    terminals: set[str],
    first: dict[str, set[str]],
) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {nt: set() for nt in grammar}
    follow[start_symbol].add("EOF")
    changed = True
    while changed:
        changed = False
        for lhs, productions in grammar.items():
            for prod in productions:
                for i, sym in enumerate(prod):
                    if sym in terminals or sym == EPS:
                        continue
                    beta = prod[i + 1 :]
                    first_beta = _first_of_sequence(beta, first, terminals)
                    before = len(follow[sym])
                    follow[sym].update(first_beta - {EPS})
                    if EPS in first_beta or not beta:
                        follow[sym].update(follow[lhs])
                    if len(follow[sym]) != before:
                        changed = True
    return follow
