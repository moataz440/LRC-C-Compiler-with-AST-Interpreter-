from __future__ import annotations


def tac_to_asm(tac_lines: list[str]) -> list[str]:
    out: list[str] = []
    for raw in tac_lines:
        line = raw.strip()
        if not line:
            continue

        if line.startswith("func ") and line.endswith(":"):
            name = line[len("func ") : -1].strip()
            out.append(f"FUNC {name}")
            continue
        if line == "endfunc":
            out.append("ENDFUNC")
            continue

        if line.endswith(":"):
            out.append(f"LABEL {line[:-1]}")
            continue

        if line.startswith("goto "):
            out.append(f"GOTO {line.split(None, 1)[1]}")
            continue

        if line.startswith("ifFalse "):
            # ifFalse <cond> goto <label>
            parts = line.split()
            # ["ifFalse", cond, "goto", label]
            if len(parts) >= 4 and parts[2] == "goto":
                out.append(f"IF_FALSE {parts[1]}, GOTO {parts[3]}")
                continue

        if line.startswith("return"):
            parts = line.split(None, 1)
            if len(parts) == 1:
                out.append("RET")
            else:
                out.append(f"RET {parts[1].strip()}")
            continue

        if " = " in line:
            left, right = [p.strip() for p in line.split("=", 1)]
            rparts = right.split()

            if len(rparts) == 1:
                out.append(f"MOV {left}, {rparts[0]}")
                continue
            if len(rparts) == 2:
                # unary
                op, a = rparts
                if op == "-":
                    out.append(f"NEG {left}, {a}")
                elif op == "!":
                    out.append(f"NOT {left}, {a}")
                else:
                    out.append(f"UNOP {left}, {op}, {a}")
                continue
            if len(rparts) == 3:
                a, op, b = rparts
                op_map = {
                    "+": "ADD",
                    "-": "SUB",
                    "*": "MUL",
                    "/": "DIV",
                    "%": "MOD",
                    "<": "LT",
                    ">": "GT",
                    "<=": "LE",
                    ">=": "GE",
                    "==": "EQ",
                    "!=": "NE",
                    "&&": "AND",
                    "||": "OR",
                }
                out.append(f"{op_map.get(op, 'BINOP')} {left}, {a}, {b}")
                continue

        # Fallback: keep as comment-ish
        out.append(f"; {line}")
    return out

