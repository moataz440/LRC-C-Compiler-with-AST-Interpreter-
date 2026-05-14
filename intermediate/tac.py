from __future__ import annotations

from intermediate.temp_vars import TempFactory


class TACGenerator:
    """
    Walks the AST and emits three-address code (TAC).

    Each function in the program becomes a  func <name>: ... endfunc  block.
    Expressions produce a result operand (a temporary name or a literal string).
    Statements produce one or more TAC lines with no result.
    """

    def __init__(self) -> None:
        self._temps = TempFactory()
        self.lines: list[str] = []

    def generate(self, ast: dict) -> list[str]:
        self.lines.clear()
        if ast.get("node") != "Program":
            return self.lines

        for global_item in ast.get("globals", []):
            if global_item.get("node") == "Function":
                self._emit_function(global_item)

        return self.lines

    def _emit_function(self, func: dict) -> None:
        self.lines.append(f"func {func['name']}:")
        self._emit_stmt(func["body"])
        self.lines.append("endfunc")

    def _emit_stmt(self, stmt: dict) -> None:
        node = stmt["node"]

        if node == "Block":
            for child_stmt in stmt.get("stmts", []):
                self._emit_stmt(child_stmt)
            return

        if node == "DeclStmt":
            self._emit_decl_stmt(stmt)
            return

        if node == "ExprStmt":
            self._emit_expr(stmt["expr"])
            return

        if node == "Cout":
            self._emit_cout(stmt)
            return

        if node == "Cin":
            for target in stmt.get("targets", []):
                if isinstance(target, str):
                    self.lines.append(f"read {target}")
                elif isinstance(target, dict):
                    name = target.get("name", "?")
                    if target.get("node") == "CinTargetIndex":
                        self.lines.append(f"read {name}[index]")
                    else:
                        self.lines.append(f"read {name}")
            return

        if node == "If":
            self._emit_if(stmt)
            return

        if node == "For":
            self._emit_for(stmt)
            return

        if node == "Return":
            if stmt.get("expr") is None:
                self.lines.append("return")
            else:
                return_val = self._emit_expr(stmt["expr"])
                self.lines.append(f"return {return_val}")
            return

    def _emit_decl_stmt(self, stmt: dict) -> None:
        decl = stmt["decl"]
        base_type = decl["var_type"]
        for declarator in decl.get("declarators", []):
            init = declarator.get("init")
            if init is None:
                continue
            var_name = declarator["name"]
            if init.get("node") == "InitList":
                item_count = len(init.get("items", []))
                self.lines.append(f"{var_name} = {{{item_count} items}}  ; {base_type}[]")
            else:
                value_operand = self._emit_expr(init)
                self.lines.append(f"{var_name} = {value_operand}")

    def _emit_cout(self, stmt: dict) -> None:
        for item in stmt.get("items", []):
            if isinstance(item, dict) and item.get("node") == "Endl":
                self.lines.append('print "\\n"')
            else:
                operand = self._emit_expr(item)
                self.lines.append(f"print {operand}")

    def _emit_if(self, stmt: dict) -> None:
        condition = self._emit_expr(stmt["cond"])
        else_label = self._temps.new_label("IF_ELSE_")
        end_label  = self._temps.new_label("IF_END_")
        self.lines.append(f"ifFalse {condition} goto {else_label}")
        self._emit_stmt(stmt["then"])
        self.lines.append(f"goto {end_label}")
        self.lines.append(f"{else_label}:")
        if stmt.get("else") is not None:
            self._emit_stmt(stmt["else"])
        self.lines.append(f"{end_label}:")

    def _emit_for(self, stmt: dict) -> None:
        loop_start = self._temps.new_label("FOR_START_")
        loop_end   = self._temps.new_label("FOR_END_")

        init = stmt.get("init")
        if init is not None:
            if init.get("node") == "DeclStmt":
                self._emit_stmt(init)
            else:
                self._emit_expr(init)

        self.lines.append(f"{loop_start}:")

        if stmt.get("cond") is not None:
            cond_operand = self._emit_expr(stmt["cond"])
            self.lines.append(f"ifFalse {cond_operand} goto {loop_end}")

        self._emit_stmt(stmt["body"])

        if stmt.get("update") is not None:
            self._emit_expr(stmt["update"])

        self.lines.append(f"goto {loop_start}")
        self.lines.append(f"{loop_end}:")

    def _emit_expr(self, expr: dict) -> str:
        node = expr["node"]

        if node == "Number":
            return str(expr["value"])

        if node == "Identifier":
            return expr["name"]

        if node == "String":
            return f'"{expr["value"]}"'

        if node == "Char":
            return f"'{expr['value']}'"

        if node == "Bool":
            return "true" if expr["value"] else "false"

        if node == "UnaryOp":
            operand = self._emit_expr(expr["expr"])
            result_temp = self._temps.new_temp()
            self.lines.append(f"{result_temp} = {expr['op']}{operand}")
            return result_temp

        if node == "IncDec":
            return self._emit_incdec(expr)

        if node == "BinOp":
            left_operand  = self._emit_expr(expr["left"])
            right_operand = self._emit_expr(expr["right"])
            result_temp = self._temps.new_temp()
            self.lines.append(f"{result_temp} = {left_operand} {expr['op']} {right_operand}")
            return result_temp

        if node == "AssignExpr":
            value_operand = self._emit_expr(expr["value"])
            lvalue = self._lvalue_of(expr["target"])
            self.lines.append(f"{lvalue} = {value_operand}")
            return lvalue

        if node == "Index":
            base_operand  = self._emit_expr(expr["base"])
            index_operand = self._emit_expr(expr["index"])
            result_temp = self._temps.new_temp()
            self.lines.append(f"{result_temp} = {base_operand}[{index_operand}]")
            return result_temp

        raise ValueError(f"TAC generator: unsupported expression node '{node}'")

    def _emit_incdec(self, expr: dict) -> str:
        """
        Handles both prefix (++x, --x) and postfix (x++, x--) increment/decrement.
        Prefix returns the new value; postfix returns the old value.
        """
        op      = expr["op"]    # "++" or "--"
        kind    = expr["kind"]  # "pre" or "post"
        target  = expr["target"]
        lvalue  = self._lvalue_of(target)
        sign    = "+" if op == "++" else "-"

        if kind == "post":
            old_value = self._temps.new_temp()
            new_value = self._temps.new_temp()
            self.lines.append(f"{old_value} = {lvalue}")
            self.lines.append(f"{new_value} = {lvalue} {sign} 1")
            self.lines.append(f"{lvalue} = {new_value}")
            return old_value
        else:
            new_value = self._temps.new_temp()
            self.lines.append(f"{new_value} = {lvalue} {sign} 1")
            self.lines.append(f"{lvalue} = {new_value}")
            return lvalue

    def _lvalue_of(self, expr: dict) -> str:
        """Return the writable location string for an assignable expression."""
        node = expr["node"]
        if node == "Identifier":
            return expr["name"]
        if node == "Index":
            base_operand  = self._emit_expr(expr["base"])
            index_operand = self._emit_expr(expr["index"])
            return f"{base_operand}[{index_operand}]"
        return self._emit_expr(expr)
