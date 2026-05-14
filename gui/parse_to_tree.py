"""Map concrete parse tree JSON to TreeNode."""

from __future__ import annotations

from typing import Any

from gui.tree_model import TreeNode


def _short(s: str, max_len: int = 44) -> str:
    s = s.replace("\n", " ")
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s


def parse_to_tree(n: Any) -> TreeNode | None:
    if n is None or not isinstance(n, dict):
        return None
    if n.get("kind") == "terminal":
        sym = n.get("symbol", "")
        lex = n.get("lexeme", "")
        return TreeNode(_short(f"{sym}  {lex!r}"), [])
    if n.get("kind") == "nonterminal":
        label = n.get("production") or n.get("lhs", "")
        ch = n.get("children") or []
        children = [parse_to_tree(c) for c in ch]
        children = [c for c in children if c is not None]
        return TreeNode(_short(str(label)), children)
    return TreeNode("?", [])
