"""Map AST JSON dicts to TreeNode for visualization."""

from __future__ import annotations

from typing import Any

from gui.tree_model import TreeNode


def _safe_label(s: str, max_len: int = 40) -> str:
    s = s.replace("\n", " ")
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def ast_to_tree(n: Any) -> TreeNode | None:
    if n is None or not isinstance(n, dict):
        return None

    node_type = n.get("node", "?")

    if node_type == "Program":
        ch: list[TreeNode] = []
        for item in n.get("globals", []):
            t = ast_to_tree(item)
            if t is not None:
                ch.append(t)
        return TreeNode("Program", ch)

    if node_type == "GlobalDecl":
        inner = ast_to_tree(n.get("decl"))
        return TreeNode("GlobalDecl", [inner] if inner else [])

    if node_type == "UsingNamespace":
        return TreeNode(_safe_label(f"using namespace {n.get('name', '')}"), [])

    if node_type == "Function":
        kids: list[TreeNode] = []
        for p in n.get("params", []):
            pt = ast_to_tree(p)
            if pt:
                kids.append(pt)
        body = ast_to_tree(n.get("body"))
        if body:
            kids.append(body)
        return TreeNode(
            _safe_label(f"Function  {n.get('return_type', '')}  {n.get('name', '')}(…)"),
            kids,
        )

    if node_type == "Param":
        return TreeNode(_safe_label(f"Param  {n.get('var_type', '')}  {n.get('name', '')}"), [])

    if node_type == "DeclStmt":
        inner = ast_to_tree(n.get("decl"))
        return TreeNode("DeclStmt", [inner] if inner else [])

    if node_type == "Decl":
        chd: list[TreeNode] = []
        for d in n.get("declarators", []):
            t = ast_to_tree(d)
            if t:
                chd.append(t)
        return TreeNode(_safe_label(f"Decl  {n.get('var_type', '')}"), chd)

    if node_type == "Declarator":
        label = n.get("name", "")
        arr = n.get("array")
        if arr and isinstance(arr, dict) and arr.get("size") is not None:
            label = f"{label}[{arr.get('size')}]"
        elif arr:
            label = f"{label}[]"
        init = ast_to_tree(n.get("init"))
        kids2 = [init] if init else []
        return TreeNode(_safe_label(f"Declarator  {label}"), kids2)

    if node_type == "InitList":
        ch3: list[TreeNode] = []
        for it in n.get("items", []):
            t = ast_to_tree(it)
            if t:
                ch3.append(t)
        return TreeNode("InitList", ch3)

    if node_type == "For":
        parts = [
            ast_to_tree(n.get("init")),
            ast_to_tree(n.get("cond")),
            ast_to_tree(n.get("update")),
            ast_to_tree(n.get("body")),
        ]
        chf = [p for p in parts if p is not None]
        return TreeNode("For", chf)

    if node_type == "If":
        parts_if = [ast_to_tree(n.get("cond")), ast_to_tree(n.get("then")), ast_to_tree(n.get("else"))]
        chi = [p for p in parts_if if p is not None]
        return TreeNode("If", chi)

    if node_type == "Return":
        ex = ast_to_tree(n.get("expr"))
        return TreeNode("Return", [ex] if ex else [])

    if node_type == "ExprStmt":
        ex = ast_to_tree(n.get("expr"))
        return TreeNode("ExprStmt", [ex] if ex else [])

    if node_type == "Block":
        chb: list[TreeNode] = []
        for s in n.get("stmts", []):
            t = ast_to_tree(s)
            if t is not None:
                chb.append(t)
        return TreeNode("Block", chb)

    # Legacy nodes (older grammars / partial trees)
    if node_type == "DeclAssign":
        expr = ast_to_tree(n.get("expr"))
        ch2 = [expr] if expr is not None else []
        return TreeNode(_safe_label(f"DeclAssign  {n.get('name', '')}"), ch2)

    if node_type == "Assign":
        ex = ast_to_tree(n.get("expr"))
        kids = [ex] if ex is not None else []
        return TreeNode(_safe_label(f"Assign  {n.get('target', '')}  ="), kids)

    if node_type == "AssignExpr":
        tgt = ast_to_tree(n.get("target"))
        val = ast_to_tree(n.get("value"))
        return TreeNode("AssignExpr", [x for x in (tgt, val) if x])

    if node_type == "UnaryOp":
        ex = ast_to_tree(n.get("expr"))
        return TreeNode(_safe_label(f"Unary  {n.get('op', '')}"), [ex] if ex else [])

    if node_type == "Index":
        base = ast_to_tree(n.get("base"))
        idx = ast_to_tree(n.get("index"))
        return TreeNode("Index", [x for x in (base, idx) if x])

    if node_type == "BinOp":
        left = ast_to_tree(n.get("left"))
        right = ast_to_tree(n.get("right"))
        kids2: list[TreeNode] = [x for x in (left, right) if x is not None]
        return TreeNode(_safe_label(f"BinOp  {n.get('op', '')}"), kids2)

    if node_type == "Identifier":
        return TreeNode(_safe_label(f"Id  {n.get('name', '')}"), [])

    if node_type == "Number":
        v = n.get("value", "")
        return TreeNode(_safe_label(f"Num  {v}"), [])

    if node_type == "String":
        return TreeNode(_safe_label(f"String  {n.get('value', '')!r}"), [])

    if node_type == "Char":
        return TreeNode(_safe_label(f"Char  {n.get('value', '')!r}"), [])

    if node_type == "Bool":
        return TreeNode(_safe_label(f"Bool  {n.get('value')}"), [])

    if node_type == "Endl":
        return TreeNode("endl", [])

    if node_type == "IncDec":
        target = ast_to_tree(n.get("target"))
        kind = n.get("kind", "")
        op = n.get("op", "")
        label = f"{op}({kind})"
        return TreeNode(_safe_label(label), [target] if target else [])

    if node_type == "Cout":
        ch_cout: list[TreeNode] = []
        for it in n.get("items", []):
            t = ast_to_tree(it)
            if t is not None:
                ch_cout.append(t)
        return TreeNode("cout <<", ch_cout)

    if node_type == "Cin":
        ch_cin: list[TreeNode] = [
            TreeNode(_safe_label(f"Id  {name}"), []) for name in n.get("targets", [])
        ]
        return TreeNode("cin >>", ch_cin)

    if "children" in n:
        chx = [ast_to_tree(c) for c in n.get("children", [])]
        chx = [c for c in chx if c]
        return TreeNode(_safe_label(str(node_type)), chx)

    return TreeNode(_safe_label(str(node_type)), [])
