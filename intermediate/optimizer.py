from __future__ import annotations


def optimize_tac(code: list[str]) -> list[str]:

    passes = 0
    max_passes = 10
    while passes < max_passes:
        passes += 1
        updated = _run_all_passes(code)
        if updated == code:
            break
        code = updated
    return code


def _run_all_passes(code: list[str]) -> list[str]:
    code = _fold_and_simplify(code)
    code = _propagate_copies(code)
    code = _eliminate_common_subexpressions(code)
    code = _remove_dead_assignments(code)
    return code


def _is_structural_line(line: str) -> bool:
    s = line.strip()
    return (
        not s
        or s.endswith(":")
        or s.startswith("goto ")
        or s.startswith("ifFalse ")
        or s.startswith("func ")
        or s == "endfunc"
        or s.startswith("print ")
        or s.startswith("read ")
        or s.startswith("return")
    )


def _try_parse_assignment(line: str):
    """Split  lhs = rhs  into (lhs, rhs_string, rhs_tokens) or return None."""
    s = line.strip()
    if " = " not in s:
        return None
    lhs, rhs = s.split("=", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    return lhs, rhs, rhs.split()


def _numeric_value(token: str):
    """Return the Python number for a numeric literal string, or None."""
    s = token
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]
    if s.replace(".", "", 1).isdigit():
        value = float(s) if "." in s else int(s)
        return -value if negative else value
    return None


def _format_number(value) -> str:
    if isinstance(value, float) and value == int(value):
        return str(int(value))
    return str(value)


def _eval_binary_op(left_val, op: str, right_val):
    if op == "+":  return left_val + right_val
    if op == "-":  return left_val - right_val
    if op == "*":  return left_val * right_val
    if op == "/" and right_val != 0:
        result = left_val / right_val
        return int(result) if result == int(result) else result
    if op == "%":  return int(left_val) % int(right_val)
    return None


def _try_algebraic_identity(left: str, op: str, right: str, left_val, right_val):
    """Return simplified operand string if an algebraic identity fires, else None."""
    if op == "+":
        if right_val == 0: return left
        if left_val == 0:  return right
    if op == "-":
        if right_val == 0: return left
        if left == right:  return "0"
    if op == "*":
        if right_val == 1:            return left
        if left_val == 1:             return right
        if left_val == 0 or right_val == 0: return "0"
    if op == "/":
        if right_val == 1: return left
        if left_val == 0:  return "0"
    if op == "%":
        if right_val == 1: return "0"
    return None


def _fold_and_simplify(code: list[str]) -> list[str]:
    """Pass 1+2: constant folding and algebraic simplification."""
    result: list[str] = []
    for line in code:
        if _is_structural_line(line):
            result.append(line)
            continue

        parsed = _try_parse_assignment(line)
        if parsed is None:
            result.append(line)
            continue

        lhs, rhs, parts = parsed

        if len(parts) == 1:
            if lhs == parts[0]:
                continue  # x = x -- drop it
            result.append(line)

        elif len(parts) == 2:
            op, operand = parts
            val = _numeric_value(operand)
            if op == "-" and val is not None:
                result.append(f"{lhs} = {_format_number(-val)}")
            else:
                result.append(line)

        elif len(parts) == 3:
            left, op, right = parts
            left_val  = _numeric_value(left)
            right_val = _numeric_value(right)

            if left_val is not None and right_val is not None:
                folded = _eval_binary_op(left_val, op, right_val)
                if folded is not None:
                    result.append(f"{lhs} = {_format_number(folded)}")
                    continue

            simplified = _try_algebraic_identity(left, op, right, left_val, right_val)
            if simplified is not None:
                if simplified == lhs:
                    continue
                result.append(f"{lhs} = {simplified}")
                continue

            result.append(line)

        else:
            result.append(line)

    return result


def _propagate_copies(code: list[str]) -> list[str]:
    """
    Pass 3: copy propagation.
    Tracks  variable -> literal  mappings within straight-line blocks and
    substitutes the literal wherever the variable is later used as an operand.
    The map is cleared at labels and branches.
    """
    literal_for: dict[str, str] = {}
    result: list[str] = []

    for line in code:
        s = line.strip()

        if _is_structural_line(s):
            if s.endswith(":") or s.startswith("goto") or s.startswith("ifFalse"):
                literal_for.clear()
            result.append(line)
            continue

        parsed = _try_parse_assignment(s)
        if parsed is None:
            result.append(line)
            continue

        lhs, rhs, parts = parsed

        if len(parts) == 1:
            substituted = literal_for.get(parts[0], parts[0])
            if lhs == substituted:
                continue
            literal_for.pop(lhs, None)
            if _numeric_value(substituted) is not None:
                literal_for[lhs] = substituted
            result.append(f"{lhs} = {substituted}")

        elif len(parts) == 3:
            left, op, right = parts
            left_sub  = literal_for.get(left,  left)
            right_sub = literal_for.get(right, right)
            literal_for.pop(lhs, None)
            if left_sub != left or right_sub != right:
                result.append(f"{lhs} = {left_sub} {op} {right_sub}")
            else:
                result.append(line)

        else:
            literal_for.pop(lhs, None)
            result.append(line)

    return result


def _eliminate_common_subexpressions(code: list[str]) -> list[str]:
    """
    Pass 4: local common subexpression elimination.
    Within a straight-line block, when  t2 = a op b  is seen and we already
    computed  t1 = a op b  (with a and b unchanged), emit  t2 = t1  instead.
    """
    rhs_first_temp: dict[str, str] = {}
    result: list[str] = []

    def _invalidate(var: str) -> None:
        stale = [rhs for rhs, temp in list(rhs_first_temp.items())
                 if var in rhs.split()]
        for rhs in stale:
            del rhs_first_temp[rhs]

    for line in code:
        s = line.strip()

        if _is_structural_line(s):
            if s.endswith(":") or s.startswith("goto") or s.startswith("ifFalse"):
                rhs_first_temp.clear()
            result.append(line)
            continue

        parsed = _try_parse_assignment(s)
        if parsed is None:
            result.append(line)
            continue

        lhs, rhs, parts = parsed

        if len(parts) == 3:
            canonical = rhs
            existing_temp = rhs_first_temp.get(canonical)
            if existing_temp is not None and existing_temp != lhs:
                result.append(f"{lhs} = {existing_temp}")
                _invalidate(lhs)
                continue

        _invalidate(lhs)
        if len(parts) == 3:
            rhs_first_temp[rhs] = lhs

        result.append(line)
    return result


def _all_read_variables(code: list[str]) -> set[str]:
    """
    Collect every variable that appears as an *operand* anywhere in the code.
    These must be kept alive.
    """
    live: set[str] = set()

    def _is_name(token: str) -> bool:
        return token.isidentifier() and _numeric_value(token) is None

    for line in code:
        s = line.strip()

        if s.startswith("print "):
            tok = s[6:].strip()
            if _is_name(tok): live.add(tok)
            continue
        if s.startswith("ifFalse "):
            parts = s.split()
            if len(parts) >= 2 and _is_name(parts[1]): live.add(parts[1])
            continue
        if s.startswith("return "):
            tok = s[7:].strip()
            if _is_name(tok): live.add(tok)
            continue

        parsed = _try_parse_assignment(s)
        if parsed is None:
            continue

        _lhs, _rhs, parts = parsed
        for i, tok in enumerate(parts):
            if i == 1 and len(parts) == 3:
                continue  # middle token is the operator
            if _is_name(tok):
                live.add(tok)

    return live


def _is_compiler_temp(name: str) -> bool:
    """True for temporaries generated by TACGenerator: t1, t2, t10, ..."""
    return name.startswith("_t") and name[2:].isdigit()


def _remove_dead_assignments(code: list[str]) -> list[str]:
    """
    Pass 5: drop assignments to compiler temporaries that are never read.
    User-declared variables are never removed — only generated t1/t2/... names.
    """
    live_vars = _all_read_variables(code)
    result: list[str] = []
    for line in code:
        parsed = _try_parse_assignment(line.strip())
        if parsed is not None:
            lhs = parsed[0]
            if _is_compiler_temp(lhs) and lhs not in live_vars:
                continue
        result.append(line)
    return result
