"""Layered x placement for n-ary trees (post-order, center internal nodes)."""

from __future__ import annotations

from gui.tree_model import TreeNode


def layout_tree(root: TreeNode) -> None:
    class Counter:
        def __init__(self) -> None:
            self.n = 0.0

        def next(self) -> float:
            v = self.n
            self.n += 1.0
            return v

    def walk(node: TreeNode, depth: int, counter: Counter) -> None:
        if not node.children:
            node.x = counter.next()
        else:
            for c in node.children:
                walk(c, depth + 1, counter)
            xs = [c.x for c in node.children]
            node.x = (min(xs) + max(xs)) / 2.0
        node.y = depth

    walk(root, 0, Counter())
