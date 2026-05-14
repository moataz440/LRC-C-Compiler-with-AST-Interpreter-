"""Render a TreeNode on a tkinter Canvas (scrollable)."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from gui.tree_layout import layout_tree
from gui.tree_model import TreeNode

LINE_COLORS = ("#3B5B8C", "#7B92B4")
TEXT_COLORS = ("#0F172A", "#E2E8F0")
BOX_FILL_LIGHT = "#E8EFFF"
BOX_FILL_DARK = "#1A2332"
BOX_OUTLINE_LIGHT = "#94A3B8"
BOX_OUTLINE_DARK = "#475569"
CANVAS_BG_LIGHT = "#F8FAFF"
CANVAS_BG_DARK = "#0F1117"


def _measure_label(label: str) -> tuple[float, float]:
    lines = (label or "?").split("\n")
    max_w = max(len(ln) for ln in lines) if lines else 1
    w = min(max_w * 6.5 + 16, 520)
    h = max(1, len(lines)) * 15 + 10
    return w, h


def _collect(node: TreeNode) -> list[TreeNode]:
    out: list[TreeNode] = [node]
    for c in node.children:
        out.extend(_collect(c))
    return out


def render_tree(
    parent: tk.Misc,
    root: TreeNode,
    is_dark: Callable[[], bool] | None = None,
) -> tk.Canvas:
    layout_tree(root)

    def dark() -> bool:
        return bool(is_dark and is_dark())

    container = tk.Frame(parent)
    container.pack(fill="both", expand=True)
    container.grid_rowconfigure(0, weight=1)
    container.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(container, highlightthickness=0)
    vsb = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    hsb = tk.Scrollbar(container, orient="horizontal", command=canvas.xview)
    canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    canvas.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    nodes = _collect(root)
    if not nodes:
        canvas.create_text(20, 20, text="(empty tree)", font=("Consolas", 10))
        return canvas

    x_min = min(n.x for n in nodes)
    h_scale = 96.0
    margin = 32
    xpad = 40
    v_gap = 60

    def px_x(x: float) -> float:
        return xpad + (x - x_min) * h_scale

    def py_y(y: int) -> float:
        return margin + y * v_gap

    for n in nodes:
        w, h = _measure_label(n.label)
        cx = px_x(n.x)
        cy = py_y(n.y)
        x0 = cx - w / 2
        y0 = cy - h / 2
        x1 = cx + w / 2
        y1 = cy + h / 2
        n._x0, n._y0, n._x1, n._y1 = x0, y0, x1, y1  # type: ignore[attr-defined]
        n._cx, n._cy = cx, cy  # type: ignore[attr-defined]

    def redraw() -> None:
        canvas.delete("all")
        d = dark()
        cbg = CANVAS_BG_DARK if d else CANVAS_BG_LIGHT
        line_col = LINE_COLORS[1] if d else LINE_COLORS[0]
        text_col = TEXT_COLORS[1] if d else TEXT_COLORS[0]
        fill = BOX_FILL_DARK if d else BOX_FILL_LIGHT
        outline = BOX_OUTLINE_DARK if d else BOX_OUTLINE_LIGHT
        canvas.config(bg=cbg)

        for n in nodes:
            for c in n.children:
                if not hasattr(n, "_x0") or not hasattr(c, "_x0"):
                    continue
                pxc = n._cx  # type: ignore
                pbottom = n._y1  # type: ignore
                cxc = c._cx  # type: ignore
                ctop = c._y0  # type: ignore
                canvas.create_line(pxc, pbottom, cxc, ctop, fill=line_col, width=1)

        for n in nodes:
            x0, y0, x1, y1 = n._x0, n._y0, n._x1, n._y1  # type: ignore
            canvas.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=outline, width=1
            )
            canvas.create_text(
                n._cx, n._cy, text=n.label, fill=text_col, font=("Consolas", 9), justify="center"  # type: ignore
            )

        bb = canvas.bbox("all")
        if bb:
            canvas.config(scrollregion=bb)
            canvas.xview_moveto(0)
            canvas.yview_moveto(0)

    canvas._tree_redraw = redraw  # type: ignore[attr-defined]
    redraw()
    return canvas
