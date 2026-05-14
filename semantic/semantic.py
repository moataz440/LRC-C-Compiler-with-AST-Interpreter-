from __future__ import annotations

from semantic.symbol_table import SymbolTable
from semantic.type_checker import infer_expr_type
from utils.error import CompilerError

_REQUIRES_HEADER: dict[str, str] = {
    "cout": "iostream",
    "cin":  "iostream",
    "endl": "iostream",
}
_STD_IDENTIFIERS: set[str] = {"cout", "cin", "endl", "string"}


def _init_repr(init_node: dict | None) -> str | None:
    """Return a short human-readable string for an initializer node."""
    if init_node is None:
        return None
    node = init_node.get("node")
    if node == "Number":
        return str(init_node["value"])
    if node == "String":
        return f'"{init_node["value"]}"'
    if node == "Char":
        return f"'{init_node['value']}'"
    if node == "Bool":
        return "true" if init_node["value"] else "false"
    if node == "Identifier":
        return init_node["name"]
    if node == "InitList":
        items = [_init_repr(i) or "?" for i in init_node.get("items", [])]
        return "{" + ", ".join(items) + "}"
    if node == "BinOp":
        l = _init_repr(init_node.get("left")) or "?"
        r = _init_repr(init_node.get("right")) or "?"
        return f"{l} {init_node.get('op','')} {r}"
    return None


class SemanticAnalyzer:
    def __init__(self) -> None:
        self.symbols = SymbolTable()
        self._includes: list[str] = []
        self._has_using_namespace_std: bool = False

    def analyze(self, ast: dict, includes: list[str] | None = None) -> dict:
        self._includes = includes or []
        self._has_using_namespace_std = False

        if ast.get("node") != "Program":
            return {
                "merged": self.symbols.to_dict(),
                "scopes": self.symbols.scopes(),
                "all_symbols": self.symbols.all_symbols(),
            }

        # First pass: detect 'using namespace std'
        for item in ast.get("globals", []):
            if item.get("node") == "UsingNamespace" and item.get("name") == "std":
                self._has_using_namespace_std = True

        for item in ast.get("globals", []):
            self._handle_global(item)

        return {
            "merged": self.symbols.to_dict(),
            "scopes": self.symbols.scopes(),
            "all_symbols": self.symbols.all_symbols(),
        }

    def _check_std_identifier(self, name: str, qualified: bool = False) -> None:
        # Always enforce #include <iostream> for cin/cout/endl
        required_header = _REQUIRES_HEADER.get(name)
        if required_header and required_header not in self._includes:
            raise CompilerError(
                f"Semantic error: '{name}' requires '#include <{required_header}>' "
                f"but it was not found in the source."
            )
        # Enforce namespace: must have using namespace std OR use std::name qualifier
        if name in _STD_IDENTIFIERS and not self._has_using_namespace_std and not qualified:
            raise CompilerError(
                f"Semantic error: '{name}' is in namespace 'std'. "
                f"Add 'using namespace std;' or use 'std::{name}'."
            )

    def _handle_global(self, item: dict) -> None:
        node = item.get("node")
        if node == "GlobalDecl":
            self._handle_decl(item["decl"])
            return
        if node == "UsingNamespace":
            return
        if node == "Function":
            self._handle_function(item)
            return
        raise CompilerError(f"Semantic error: unsupported global node '{node}'.")

    def _handle_function(self, func: dict) -> None:
        fn_name = func.get("name", "?")
        # Register the function itself as a symbol in the global scope (level 0)
        ret_type = func.get("return_type", "int")
        param_types = ", ".join(p["var_type"] for p in func.get("params", []))
        self.symbols.declare(
            fn_name, f"{ret_type}({param_types})",
            is_param=False, is_array=False,
        )
        self.symbols.push_scope(name=fn_name)
        for p in func.get("params", []):
            if self.symbols.exists(p["name"]):
                raise CompilerError(f"Semantic error: duplicate parameter '{p['name']}'.")
            self.symbols.declare(
                p["name"], p["var_type"],
                is_param=True,
            )
        self._handle_stmt(func["body"])
        self.symbols.pop_scope()

    def _handle_stmt(self, stmt: dict) -> None:
        node = stmt.get("node")
        if node == "Block":
            self.symbols.push_scope(name=self.symbols.current_scope_name())
            for s in stmt.get("stmts", []):
                self._handle_stmt(s)
            self.symbols.pop_scope()
            return
        if node == "DeclStmt":
            self._handle_decl(stmt["decl"])
            return
        if node == "ExprStmt":
            infer_expr_type(stmt["expr"], self.symbols)
            return
        if node == "Cout":
            qualified = bool(stmt.get("qualified"))
            self._check_std_identifier("cout", qualified=qualified)
            for it in stmt.get("items", []):
                if isinstance(it, dict) and it.get("node") == "Endl":
                    self._check_std_identifier("endl", qualified=qualified)
                    continue
                infer_expr_type(it, self.symbols)
            return
        if node == "Cin":
            qualified = bool(stmt.get("qualified"))
            self._check_std_identifier("cin", qualified=qualified)
            for target in stmt.get("targets", []):
                if isinstance(target, str):
                    name = target
                elif isinstance(target, dict):
                    name = target.get("name", "")
                else:
                    name = ""
                if name and not self.symbols.exists(name):
                    raise CompilerError(f"Semantic error: variable '{name}' used before declaration.")
            return
        if node == "If":
            cond_type = infer_expr_type(stmt["cond"], self.symbols)
            if cond_type not in {"bool", "int", "long", "float", "double"}:
                raise CompilerError("Semantic error: if condition must be a boolean or numeric expression.")
            self._handle_stmt(stmt["then"])
            if stmt.get("else") is not None:
                self._handle_stmt(stmt["else"])
            return
        if node == "For":
            self.symbols.push_scope(name="for_loop")
            init = stmt.get("init")
            if init is None:
                pass
            elif isinstance(init, dict) and init.get("node") == "DeclStmt":
                self._handle_decl(init["decl"])
            else:
                infer_expr_type(init, self.symbols)
            if stmt.get("cond") is not None:
                cond_type = infer_expr_type(stmt["cond"], self.symbols)
                if cond_type not in {"bool", "int", "long", "float", "double"}:
                    raise CompilerError("Semantic error: for condition must be a boolean or numeric expression.")
            if stmt.get("update") is not None:
                infer_expr_type(stmt["update"], self.symbols)
            self._handle_stmt(stmt["body"])
            self.symbols.pop_scope()
            return
        if node == "Return":
            if stmt.get("expr") is not None:
                infer_expr_type(stmt["expr"], self.symbols)
            return

        raise CompilerError(f"Semantic error: unsupported statement node '{node}'.")

    def _handle_decl(self, decl: dict) -> None:
        if decl.get("node") != "Decl":
            raise CompilerError(f"Semantic error: unsupported declaration node '{decl.get('node')}'.")

        base_type = decl["var_type"]
        for d in decl.get("declarators", []):
            name = d["name"]
            if self.symbols.exists_in_current_scope(name):
                raise CompilerError(f"Semantic error: duplicate declaration for variable '{name}'.")

            array_meta = d.get("array")
            init_node  = d.get("init")
            is_array   = array_meta is not None
            array_size: int | None = None
            var_type   = base_type

            if is_array:
                array_size = array_meta.get("size") if isinstance(array_meta, dict) else None
                has_init_list = isinstance(init_node, dict) and init_node.get("node") == "InitList"
                if array_size is None and not has_init_list:
                    raise CompilerError(
                        f"Semantic error: array '{name}' declared without a size or initializer list. "
                        f"Use 'int {name}[N]' or 'int {name}[] = {{...}}'."
                    )
                if array_size is None and has_init_list:
                    array_size = len(init_node.get("items", []))
                var_type = f"{base_type}[]"

            init_repr = _init_repr(init_node)

            self.symbols.declare(
                name, var_type,
                is_array=is_array,
                array_size=array_size,
                init_value=init_repr,
            )

            if init_node is None:
                continue
            if init_node.get("node") == "InitList":
                for elem in init_node.get("items", []):
                    infer_expr_type(elem, self.symbols)
                continue

            init_type = infer_expr_type(init_node, self.symbols)
            if base_type in {"int", "long"} and init_type in {"float", "double"}:
                raise CompilerError(
                    f"Semantic error: cannot assign floating-point expression to "
                    f"{base_type} variable '{name}' without a cast."
                )
            if base_type in {"int", "long", "float", "double"} and init_type == "string":
                raise CompilerError(
                    f"Semantic error: cannot assign string to numeric variable '{name}'."
                )
