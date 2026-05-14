from __future__ import annotations

from semantic.symbol_table import SymbolTable
from utils.error import CompilerError


def infer_expr_type(expr: dict, symbols: SymbolTable) -> str:
    node = expr["node"]
    if node == "Number":
        return "float" if isinstance(expr["value"], float) else "int"
    if node == "Identifier":
        name = expr["name"]
        if not symbols.exists(name):
            raise CompilerError(f"Semantic error: variable '{name}' used before declaration.")
        return symbols.get(name)
    if node == "String":
        return "string"
    if node == "Char":
        return "char"
    if node == "Bool":
        return "bool"
    if node == "Index":
        base_t = infer_expr_type(expr["base"], symbols)
        _idx_t = infer_expr_type(expr["index"], symbols)
        # Represent arrays as "T[]" strings.
        if base_t.endswith("[]"):
            return base_t[: -2]
        # If someone indexes a non-array, keep it as-is but still allow parsing.
        return base_t
    if node == "UnaryOp":
        inner = infer_expr_type(expr["expr"], symbols)
        if expr["op"] == "!":
            return "bool"
        if expr["op"] == "-":
            if inner not in {"int", "float", "double", "long"}:
                raise CompilerError("Semantic error: unary '-' requires numeric operand.")
            return inner
        return inner
    if node == "IncDec":
        # ++x, x++, --x, x--
        target = expr["target"]
        tnode = target.get("node")
        if tnode == "Identifier":
            inner = infer_expr_type(target, symbols)
        elif tnode == "Index":
            inner = infer_expr_type(target, symbols)
        else:
            raise CompilerError("Semantic error: ++/-- target must be a variable (identifier or array element).")
        if inner not in {"int", "float", "double", "long"}:
            raise CompilerError("Semantic error: ++/-- requires a numeric operand.")
        return inner
    if node == "BinOp":
        left = infer_expr_type(expr["left"], symbols)
        right = infer_expr_type(expr["right"], symbols)
        if expr["op"] in {"<", ">", "<=", ">=", "==", "!="}:
            if left in {"string", "char"} or right in {"string", "char"}:
                # Allow equality for same-type, forbid ordering for now.
                if expr["op"] in {"<", ">", "<=", ">="}:
                    raise CompilerError("Semantic error: ordering comparisons require numeric operands.")
                if left != right:
                    raise CompilerError("Semantic error: equality comparison requires matching operand types.")
                return "bool"
            if left not in {"int", "float", "double", "long"} or right not in {"int", "float", "double", "long"}:
                raise CompilerError("Semantic error: relational operators require numeric operands.")
            return "bool"
        if expr["op"] in {"&&", "||"}:
            return "bool"
        if left in {"double", "float"} or right in {"double", "float"}:
            return "double" if "double" in {left, right} else "float"
        if left == "long" or right == "long":
            return "long"
        return "int"
    if node == "AssignExpr":
        # Assignment expression has the type of the RHS.
        return infer_expr_type(expr["value"], symbols)
    raise CompilerError(f"Semantic error: unknown expression node '{node}'.")
