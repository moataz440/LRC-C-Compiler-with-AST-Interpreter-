from __future__ import annotations

from dataclasses import dataclass

from utils.error import CompilerError


class ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


@dataclass
class RunResult:
    return_value: object | None
    globals_after: dict[str, object]
    stdout: str
    all_vars: dict = None  # all scopes merged

    def to_dict(self) -> dict:
        return {
            "return_value": self.return_value,
            "globals_after": dict(self.globals_after),
            "all_vars": dict(self.all_vars) if self.all_vars else {},
            "stdout": self.stdout,
        }


class Environment:
    def __init__(self) -> None:
        self._scopes: list[dict[str, object]] = [{}]

    def push(self) -> None:
        self._scopes.append({})

    def pop(self) -> None:
        self._scopes.pop()

    def declare(self, name: str, value: object) -> None:
        if name in self._scopes[-1]:
            raise CompilerError(f"Runtime error: duplicate variable '{name}' in the same scope.")
        self._scopes[-1][name] = value

    def assign(self, name: str, value: object) -> None:
        for scope in reversed(self._scopes):
            if name in scope:
                scope[name] = value
                return
        raise CompilerError(f"Runtime error: variable '{name}' used before declaration.")

    def get(self, name: str) -> object:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise CompilerError(f"Runtime error: variable '{name}' used before declaration.")

    def snapshot_globals(self) -> dict[str, object]:
        return dict(self._scopes[0])

    def snapshot_all(self) -> dict[str, object]:
        """Merge all scopes (innermost wins) for display purposes."""
        merged: dict[str, object] = {}
        for scope in self._scopes:
            merged.update(scope)
        return merged


class Interpreter:
    def __init__(self) -> None:
        self.env = Environment()
        self.functions: dict[str, dict] = {}
        self._stdout_parts: list[str] = []
        self._stdin_tokens: list[str] = []
        self._last_all_vars: dict = {}  # snapshot taken just before main's scope pops
        self._stdin_callback = None   # callable() -> str, called when cin needs more input
        self._stdout_callback = None  # callable(str) -> None, called for each cout chunk

    def run(self, ast: dict, *, stdin: str = "",
            stdin_callback=None, stdout_callback=None) -> RunResult:
        self._stdout_parts = []
        self._stdin_tokens = stdin.split() if stdin.strip() else []
        self._stdin_callback = stdin_callback
        self._stdout_callback = stdout_callback
        if ast.get("node") != "Program":
            return RunResult(return_value=None, globals_after=self.env.snapshot_globals(), all_vars=self.env.snapshot_all(), stdout="")

        for g in ast.get("globals", []):
            if isinstance(g, dict) and g.get("node") == "Function":
                self.functions[g["name"]] = g

        main_fn = self.functions.get("main")
        if main_fn is None:
            return RunResult(return_value=None, globals_after=self.env.snapshot_globals(), all_vars=self.env.snapshot_all(), stdout="")

        rv = self._call_function(main_fn, args=[])
        return RunResult(return_value=rv, globals_after=self.env.snapshot_globals(), all_vars=self._last_all_vars, stdout="".join(self._stdout_parts))

    def _call_function(self, fn: dict, args: list[object]) -> object | None:
        self.env.push()
        try:
            params = fn.get("params") or []
            if len(args) != len(params):
                raise CompilerError(
                    f"Runtime error: function '{fn.get('name')}' expected {len(params)} args, got {len(args)}."
                )
            for p, v in zip(params, args, strict=False):
                self.env.declare(p["name"], v)
            self._exec_stmt(fn["body"])
            return None
        except ReturnSignal as r:
            return r.value
        finally:
            self.env.pop()

    def _exec_stmt(self, stmt: dict) -> None:
        node = stmt.get("node")
        if node == "Block":
            self.env.push()
            try:
                for s in stmt.get("stmts", []):
                    self._exec_stmt(s)
            finally:
                # Capture all vars before this block's scope disappears
                self._last_all_vars = self.env.snapshot_all()
                self.env.pop()
            return

        if node == "DeclStmt":
            decl = stmt["decl"]
            base_type = decl["var_type"]
            for d in decl.get("declarators", []):
                name = d["name"]
                array_meta = d.get("array")
                value = self._default_value(base_type, array_meta)
                init = d.get("init")
                if init is not None:
                    if init.get("node") == "InitList":
                        value = [self._eval_expr(x) for x in init.get("items", [])]
                    else:
                        raw_val = self._eval_expr(init)
                        # BUG FIX: preserve integer type on assignment
                        value = _coerce_to_type(raw_val, base_type)
                self.env.declare(name, value)
            return

        if node == "ExprStmt":
            self._eval_expr(stmt["expr"])
            return

        if node == "Cout":
            for it in stmt.get("items", []):
                if isinstance(it, dict) and it.get("node") == "Endl":
                    chunk = "\n"
                else:
                    v = self._eval_expr(it)
                    chunk = _to_cpp_string(v)
                self._stdout_parts.append(chunk)
                if self._stdout_callback:
                    self._stdout_callback(chunk)
            return

        if node == "Cin":
            for target in stmt.get("targets", []):
                while not self._stdin_tokens:
                    if self._stdin_callback:
                        line = self._stdin_callback()
                        if line is None:
                            raise CompilerError("Runtime error: cin reached end of input (no more input provided).")
                        self._stdin_tokens.extend(line.split())
                    else:
                        raise CompilerError("Runtime error: cin needs more input. Use the terminal below to provide it.")
                raw = self._stdin_tokens.pop(0)
                # target may be a plain string (old path) or a dict node
                if isinstance(target, str):
                    current = self.env.get(target)
                    self.env.assign(target, _parse_into_type(raw, current))
                elif isinstance(target, dict):
                    if target.get("node") == "CinTargetVar":
                        name = target["name"]
                        current = self.env.get(name)
                        self.env.assign(name, _parse_into_type(raw, current))
                    elif target.get("node") == "CinTargetIndex":
                        name = target["name"]
                        idx = int(self._eval_expr(target["index"]))
                        arr = self.env.get(name)
                        if not isinstance(arr, list):
                            raise CompilerError(f"Runtime error: '{name}' is not an array.")
                        current_elem = arr[idx] if 0 <= idx < len(arr) else 0
                        arr[idx] = _parse_into_type(raw, current_elem)
                        self.env.assign(name, arr)
            return

        if node == "If":
            cond = self._eval_expr(stmt["cond"])
            if bool(cond):
                self._exec_stmt(stmt["then"])
            else:
                if stmt.get("else") is not None:
                    self._exec_stmt(stmt["else"])
            return

        if node == "For":
            self.env.push()
            try:
                init = stmt.get("init")
                if init is not None:
                    if isinstance(init, dict) and init.get("node") == "DeclStmt":
                        self._exec_stmt(init)
                    else:
                        self._eval_expr(init)
                while True:
                    cond_expr = stmt.get("cond")
                    if cond_expr is not None and not bool(self._eval_expr(cond_expr)):
                        break
                    self._exec_stmt(stmt["body"])
                    upd = stmt.get("update")
                    if upd is not None:
                        self._eval_expr(upd)
            finally:
                self.env.pop()
            return

        if node == "Return":
            expr = stmt.get("expr")
            raise ReturnSignal(self._eval_expr(expr) if expr is not None else None)

        raise CompilerError(f"Runtime error: unsupported statement node '{node}'.")

    def _eval_expr(self, expr: dict | None) -> object:
        if expr is None:
            return None
        node = expr.get("node")

        if node == "Number":
            return expr["value"]
        if node == "String":
            return expr["value"]
        if node == "Char":
            return expr["value"]
        if node == "Bool":
            return bool(expr["value"])
        if node == "Identifier":
            return self.env.get(expr["name"])

        if node == "UnaryOp":
            v = self._eval_expr(expr["expr"])
            op = expr["op"]
            if op == "!":
                return not bool(v)
            if op == "-":
                return -_as_number(v)
            raise CompilerError(f"Runtime error: unsupported unary operator '{op}'.")

        if node == "IncDec":
            op = expr["op"]
            kind = expr["kind"]  # "pre" or "post"
            target = expr["target"]
            old = self._read_lvalue(target)
            delta = 1 if op == "++" else -1
            # BUG FIX: preserve int type — if old value is int, keep result as int
            if isinstance(old, int) and not isinstance(old, bool):
                new = old + delta
            else:
                new = _as_number(old) + delta
            self._write_lvalue(target, new)
            # BUG FIX: pre-increment returns new value, post returns old value
            return new if kind == "pre" else old

        if node == "BinOp":
            a = self._eval_expr(expr["left"])
            b = self._eval_expr(expr["right"])
            op = expr["op"]
            return _eval_binop(a, op, b)

        if node == "AssignExpr":
            value = self._eval_expr(expr["value"])
            target = expr["target"]
            if target.get("node") == "Identifier":
                # BUG FIX: preserve the existing variable type on assignment
                var_name = target["name"]
                current = self.env.get(var_name)
                coerced = _coerce_to_existing_type(value, current)
                self.env.assign(var_name, coerced)
                return coerced
            if target.get("node") == "Index":
                base = self._eval_expr(target["base"])
                idx = self._eval_expr(target["index"])
                if not isinstance(base, list):
                    raise CompilerError("Runtime error: indexing non-array value.")
                i = int(_as_number(idx))
                if i < 0 or i >= len(base):
                    raise CompilerError(f"Runtime error: array index {i} out of range (size {len(base)}).")
                base[i] = value
                return value
            raise CompilerError("Runtime error: invalid assignment target.")

        if node == "Index":
            base = self._eval_expr(expr["base"])
            idx = self._eval_expr(expr["index"])
            if not isinstance(base, list):
                raise CompilerError("Runtime error: indexing non-array value.")
            i = int(_as_number(idx))
            if i < 0 or i >= len(base):
                raise CompilerError(f"Runtime error: array index {i} out of range (size {len(base)}).")
            return base[i]

        raise CompilerError(f"Runtime error: unsupported expression node '{node}'.")

    def _read_lvalue(self, expr: dict) -> object:
        node = expr.get("node")
        if node == "Identifier":
            return self.env.get(expr["name"])
        if node == "Index":
            base = self._eval_expr(expr["base"])
            idx = self._eval_expr(expr["index"])
            if not isinstance(base, list):
                raise CompilerError("Runtime error: indexing non-array value.")
            i = int(_as_number(idx))
            if i < 0 or i >= len(base):
                raise CompilerError(f"Runtime error: array index {i} out of range (size {len(base)}).")
            return base[i]
        raise CompilerError("Runtime error: invalid lvalue.")

    def _write_lvalue(self, expr: dict, value: object) -> None:
        node = expr.get("node")
        if node == "Identifier":
            self.env.assign(expr["name"], value)
            return
        if node == "Index":
            base = self._eval_expr(expr["base"])
            idx = self._eval_expr(expr["index"])
            if not isinstance(base, list):
                raise CompilerError("Runtime error: indexing non-array value.")
            i = int(_as_number(idx))
            if i < 0 or i >= len(base):
                raise CompilerError(f"Runtime error: array index {i} out of range (size {len(base)}).")
            base[i] = value
            return
        raise CompilerError("Runtime error: invalid lvalue.")

    def _default_value(self, base_type: str, array_meta: dict | None) -> object:
        if array_meta is not None:
            size = array_meta.get("size") if isinstance(array_meta, dict) else None
            n = int(size) if isinstance(size, (int, float)) and size is not None else 0
            elem = _default_scalar(base_type)
            return [elem for _ in range(n)]
        return _default_scalar(base_type)


def _default_scalar(base_type: str) -> object:
    if base_type in {"int", "long"}:
        return 0
    if base_type in {"float", "double"}:
        return 0.0
    if base_type == "bool":
        return False
    if base_type == "char":
        return "\0"
    if base_type == "string":
        return ""
    return None


def _coerce_to_type(value: object, base_type: str) -> object:
    """Coerce a computed value to match the declared type (e.g. keep int as int)."""
    if base_type in {"int", "long"}:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return int(value)
    if base_type in {"float", "double"}:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return value


def _coerce_to_existing_type(new_value: object, existing: object) -> object:
    """Preserve the runtime type of a variable on assignment."""
    if isinstance(existing, int) and not isinstance(existing, bool):
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            return int(new_value)
    if isinstance(existing, float):
        if isinstance(new_value, (int, float)) and not isinstance(new_value, bool):
            return float(new_value)
    return new_value


def _as_number(v: object) -> float:
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, (int, float)):
        return float(v)
    raise CompilerError("Runtime error: expected numeric value.")


def _eval_binop(a: object, op: str, b: object) -> object:
    if op in {"+", "-", "*", "/", "%"}:
        ax = _as_number(a)
        bx = _as_number(b)
        if op == "+":
            result = ax + bx
        elif op == "-":
            result = ax - bx
        elif op == "*":
            result = ax * bx
        elif op == "/":
            if bx == 0:
                raise CompilerError("Runtime error: division by zero.")
            result = ax / bx
        else:  # %
            if int(bx) == 0:
                raise CompilerError("Runtime error: modulo by zero.")
            result = int(ax) % int(bx)
        # Preserve int if both operands were int
        if isinstance(a, int) and not isinstance(a, bool) and isinstance(b, int) and not isinstance(b, bool):
            if op != "/":
                return int(result)
        return result

    if op in {"<", ">", "<=", ">=", "==", "!="}:
        if op == "<":   return a < b
        if op == ">":   return a > b
        if op == "<=":  return a <= b
        if op == ">=":  return a >= b
        if op == "==":  return a == b
        if op == "!=":  return a != b

    if op == "&&":
        return bool(a) and bool(b)
    if op == "||":
        return bool(a) or bool(b)

    raise CompilerError(f"Runtime error: unsupported operator '{op}'.")


def _to_cpp_string(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        s = f"{v:.10g}"
        return s
    return str(v)


def _parse_into_type(raw: str, current_value: object) -> object:
    if isinstance(current_value, bool):
        if raw.lower() in {"true", "1"}:
            return True
        if raw.lower() in {"false", "0"}:
            return False
        raise CompilerError("Runtime error: cannot parse bool from input.")
    if isinstance(current_value, int):
        try:
            return int(float(raw))
        except ValueError as exc:
            raise CompilerError("Runtime error: cannot parse int from input.") from exc
    if isinstance(current_value, float):
        try:
            return float(raw)
        except ValueError as exc:
            raise CompilerError("Runtime error: cannot parse float from input.") from exc
    if isinstance(current_value, str):
        return raw
    return raw
