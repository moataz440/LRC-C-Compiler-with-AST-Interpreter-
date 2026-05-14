"""Simple n-ary tree for on-screen tree visualization."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TreeNode:
    label: str
    children: list[TreeNode] = field(default_factory=list)
    # Filled by layout
    x: float = 0.0
    y: int = 0
